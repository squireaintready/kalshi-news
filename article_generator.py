"""
Article Generator - Creates news articles from Kalshi market data using LLMs
"""
import logging
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional
import json

import config

logger = logging.getLogger(__name__)

# Article generation prompt - engaging market analysis style
ARTICLE_SYSTEM_PROMPT = """You are a sharp financial writer creating engaging articles about prediction markets. Your writing style is:

- Fact-forward and informative, like a Bloomberg or Axios article but with personality
- Lead with the numbers and data, then layer in analysis and occasional opinion
- Opinions should feel earned—back them up with reasoning, don't just assert
- Skeptical and analytical. Question whether the market has it right. Poke holes.
- Varied sentence structure. Mix punchy short sentences with longer explanatory ones.
- Use phrases like "The market may be underpricing...", "What's interesting here...", "The risk that isn't priced in..."
- Sprinkle in first-person sparingly: "I'd argue...", "My read on this...", "Hard to ignore..."
- NO podcast energy. No "dude", "man", "wild", "think about it". This is written, not spoken.
- Absolutely NO AI-sounding phrases like "it's important to note", "in conclusion", "furthermore", "delve into", "navigating"
- Never use bullet points or numbered lists in the article body
- Write like a smart analyst who writes well, not a robot or a podcaster

The article should feel like something you'd read on a quality finance blog—informed, opinionated, readable."""

# Results article prompt - for when markets resolve
RESULTS_SYSTEM_PROMPT = """You are a sharp financial writer creating post-mortem articles about prediction markets that have just resolved. Your writing style is:

- Lead with the outcome: what happened, who won, who lost
- Analyze whether the market got it right or wrong—and why
- Examine what signals people missed or correctly identified
- Be honest about uncertainty and hindsight bias
- Use phrases like "The market had this at X%—turns out that was...", "What the crowd missed...", "In hindsight..."
- Sprinkle in first-person sparingly: "I'd have been wrong too...", "Looking back..."
- NO podcast energy. This is written analysis, not spoken commentary.
- Absolutely NO AI-sounding phrases like "it's important to note", "in conclusion", "furthermore", "delve into"
- Never use bullet points or numbered lists

The article should feel like a satisfying wrap-up—readers want to know what happened and what to learn from it."""

RESULTS_USER_PROMPT_TEMPLATE = """Write a results article about this prediction market that just resolved. The article should be 350-500 words.

Market Details:
- Title: {title}
- Final Outcome: {outcome} (the market resolved to {outcome})
- Final Probability Before Resolution: {final_probability}%
- Original Analysis Probability (when we first covered it): {original_probability}%
- Total Volume: {volume} contracts traded
- Market Closed: {close_time}
- Subtitle/Description: {subtitle}

Requirements for the article:
1. Create a compelling title that signals the outcome (e.g., "The Fed Held Rates—And the Market Saw It Coming" or "Bitcoin Missed $100K: Where the Bulls Went Wrong")
2. Cover these topics naturally:
   - The outcome and what it means
   - Whether the market pricing was accurate or off
   - What factors drove the result
   - What signals people got right or wrong
   - Lessons for similar future markets
3. Length: 350-500 words
4. Tone: analytical wrap-up, honest about what was predictable vs. surprising

Return your response in this exact JSON format:
{{
    "title": "Your results headline here",
    "teaser": "A 1-2 sentence summary of the outcome and key takeaway",
    "content": "The full article body here (350-500 words)"
}}

Only return valid JSON, nothing else."""

ARTICLE_USER_PROMPT_TEMPLATE = """Write an article about this prediction market. The article should be 400-650 words.

Market Details:
- Title: {title}
- Current Probability: {probability}% chance of YES
- Recent Price Movement: {price_movement}
- Volume: {volume} contracts traded
- 24h Volume: {volume_24h} contracts
- Open Interest: {open_interest}
- Market Closes: {close_time}
- Days Until Close: {days_until_close}
- Subtitle/Description: {subtitle}

Requirements for the article:
1. Create a catchy, compelling title (intriguing but credible—not trashy clickbait)
2. Cover these topics woven naturally into the narrative (NOT as a checklist):
   - Current odds/probability and what they signal
   - Whether the market pricing seems right, too high, or too low—and why
   - Key upcoming events or catalysts that could move the market
   - Risks or factors the market might be underweighting
   - Relevant recent news, data, or trends
   - Your analytical take on the situation
3. Length: 400-650 words
4. Tone: informed, analytical, readable. Lead with facts, sprinkle opinions. Written for readers, not listeners.
5. Sound like a human analyst who writes well—not robotic, not a podcaster

Return your response in this exact JSON format:
{{
    "title": "Your catchy clickbait title here",
    "teaser": "A 1-2 sentence hook that makes people want to read more",
    "content": "The full article body here (400-650 words)"
}}

Only return valid JSON, nothing else."""


class ArticleGenerator:
    """Generates news articles from market data using LLM APIs"""

    def __init__(self):
        self.provider = config.LLM_PROVIDER.lower()
        self._setup_client()

    def _setup_client(self):
        """Initialize the appropriate LLM client"""
        if self.provider == "anthropic":
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
                logger.info("Initialized Anthropic client")
            except ImportError:
                raise ImportError("anthropic package not installed. Run: pip install anthropic")
        elif self.provider == "openai":
            try:
                import openai
                self.client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
                logger.info("Initialized OpenAI client")
            except ImportError:
                raise ImportError("openai package not installed. Run: pip install openai")
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

    def _call_anthropic(self, system_prompt: str, user_prompt: str) -> str:
        """Make API call to Anthropic Claude"""
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )
        return response.content[0].text

    def _call_openai(self, system_prompt: str, user_prompt: str) -> str:
        """Make API call to OpenAI"""
        response = self.client.chat.completions.create(
            model="gpt-4-turbo-preview",
            max_tokens=2000,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"}
        )
        return response.choices[0].message.content

    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """Route to appropriate LLM provider"""
        if self.provider == "anthropic":
            return self._call_anthropic(system_prompt, user_prompt)
        elif self.provider == "openai":
            return self._call_openai(system_prompt, user_prompt)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def generate_article(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Generate an article for a given market

        Args:
            market_data: Enriched market data from KalshiClient

        Returns:
            Article dict with title, teaser, content, and metadata
        """
        try:
            # Prepare the prompt with market data
            user_prompt = ARTICLE_USER_PROMPT_TEMPLATE.format(
                title=market_data.get("title", "Unknown Market"),
                probability=market_data.get("probability_pct", 50),
                price_movement=self._format_price_movement(market_data),
                volume=market_data.get("volume", 0),
                volume_24h=market_data.get("volume_24h", 0),
                open_interest=market_data.get("open_interest", 0),
                close_time=market_data.get("close_time_readable", "Unknown"),
                days_until_close=market_data.get("days_until_close", "Unknown"),
                subtitle=market_data.get("subtitle", market_data.get("title", ""))
            )

            # Call LLM
            logger.info(f"Generating article for market: {market_data.get('ticker', 'unknown')}")
            response_text = self._call_llm(ARTICLE_SYSTEM_PROMPT, user_prompt)

            # Parse JSON response
            article_data = self._parse_article_response(response_text)
            if not article_data:
                return None

            # Add metadata
            article = {
                "id": self._generate_article_id(market_data),
                "article_type": "analysis",
                "title": article_data.get("title", "Untitled"),
                "teaser": article_data.get("teaser", ""),
                "content": article_data.get("content", ""),
                "market_ticker": market_data.get("ticker"),
                "market_title": market_data.get("title"),
                "probability": market_data.get("probability_pct"),
                "generated_at": datetime.utcnow().isoformat(),
                "close_time": market_data.get("close_time"),
                "volume": market_data.get("volume", 0),
                "status": "active",
            }

            # Validate article length
            word_count = len(article["content"].split())
            if word_count < config.MIN_ARTICLE_LENGTH:
                logger.warning(f"Article too short ({word_count} words), regenerating...")
                # Could implement retry logic here

            article["word_count"] = word_count
            logger.info(f"Generated article: {article['title'][:50]}... ({word_count} words)")

            return article

        except Exception as e:
            logger.error(f"Failed to generate article: {e}")
            return None

    def generate_results_article(self, market_data: Dict[str, Any],
                                   original_article: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Generate a results article for a resolved market

        Args:
            market_data: Market data including resolution info
            original_article: The original analysis article if available

        Returns:
            Article dict with results analysis
        """
        try:
            outcome = market_data.get("result", "YES" if market_data.get("yes_price", 0) > 50 else "NO")
            final_prob = market_data.get("final_probability", market_data.get("probability_pct", 50))
            original_prob = original_article.get("probability", 50) if original_article else final_prob

            user_prompt = RESULTS_USER_PROMPT_TEMPLATE.format(
                title=market_data.get("title", "Unknown Market"),
                outcome=outcome,
                final_probability=final_prob,
                original_probability=original_prob,
                volume=market_data.get("volume", 0),
                close_time=market_data.get("close_time_readable", "Unknown"),
                subtitle=market_data.get("subtitle", market_data.get("title", ""))
            )

            logger.info(f"Generating results article for market: {market_data.get('ticker', 'unknown')}")
            response_text = self._call_llm(RESULTS_SYSTEM_PROMPT, user_prompt)

            article_data = self._parse_article_response(response_text)
            if not article_data:
                return None

            article = {
                "id": self._generate_article_id(market_data) + "-results",
                "article_type": "results",
                "title": article_data.get("title", "Untitled"),
                "teaser": article_data.get("teaser", ""),
                "content": article_data.get("content", ""),
                "market_ticker": market_data.get("ticker"),
                "market_title": market_data.get("title"),
                "probability": final_prob,
                "outcome": outcome,
                "generated_at": datetime.utcnow().isoformat(),
                "close_time": market_data.get("close_time"),
                "volume": market_data.get("volume", 0),
                "status": "resolved",
                "original_article_id": original_article.get("id") if original_article else None,
            }

            article["word_count"] = len(article["content"].split())
            logger.info(f"Generated results article: {article['title'][:50]}...")

            return article

        except Exception as e:
            logger.error(f"Failed to generate results article: {e}")
            return None

    def _format_price_movement(self, market_data: Dict[str, Any]) -> str:
        """Format price movement for the prompt"""
        change = market_data.get("price_change")
        if change is None:
            return "No recent data available"

        direction = "up" if change > 0 else "down"
        return f"{direction} {abs(change)} percentage points recently"

    def _parse_article_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Parse the JSON response from the LLM"""
        try:
            # Try to extract JSON from the response
            # Handle case where LLM might wrap JSON in markdown code blocks
            text = response_text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]

            return json.loads(text.strip())
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse article JSON: {e}")
            logger.debug(f"Raw response: {response_text[:500]}")
            return None

    def _generate_article_id(self, market_data: Dict[str, Any]) -> str:
        """Generate a unique ID for an article"""
        ticker = market_data.get("ticker", "unknown")
        timestamp = datetime.utcnow().strftime("%Y%m%d%H")
        hash_input = f"{ticker}-{timestamp}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:12]


# Singleton instance
_generator_instance: Optional[ArticleGenerator] = None

def get_generator() -> ArticleGenerator:
    """Get or create the article generator singleton"""
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = ArticleGenerator()
    return _generator_instance
