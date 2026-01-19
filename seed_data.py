"""
Seed the cache with example articles for testing/demo purposes
Run this script to populate the cache without needing API access
"""
import json
from datetime import datetime, timezone, timedelta
from cache import get_cache

# Get current time for relative dates
now = datetime.now(timezone.utc)

EXAMPLE_ARTICLES = [
    # Active analysis article
    {
        "id": "a1b2c3d4e5f6",
        "article_type": "analysis",
        "title": "The March Rate Cut Trade Is Getting Crowded—And That's a Problem",
        "teaser": "Kalshi has a 73% probability priced in for a Fed cut. The consensus feels a bit too comfortable.",
        "content": """The March rate cut is practically a done deal if you believe prediction markets. Kalshi currently shows 73% odds the Fed cuts by their March meeting. That's up from 62% just two weeks ago.

The move higher came after a softer-than-expected jobs report. Traders took it as confirmation that the labor market is cooling enough to give the Fed cover. Maybe. But 73% feels rich.

Here's the setup: January CPI drops on February 12th. That's the last major inflation print before the March 18-19 FOMC meeting. The base effects are tricky—year-over-year comparisons get harder from here. A hot print, even marginally, could unwind a lot of this positioning fast.

Volume on this contract has been enormous. Over 2 million contracts traded. That kind of liquidity usually means institutional money is involved. But crowded trades have a way of reversing sharply when the narrative shifts.

What the market might be underpricing: the labor market isn't actually that weak. The quits rate remains elevated. Workers still feel confident enough to leave jobs voluntarily. That's not the profile of an economy desperate for rate relief.

Fed speakers have been notably cautious. Governor Waller said last week they need "more data" before committing. That's Fed-speak for "we're not in a hurry." The market seems to be ignoring the message.

There's historical precedent for skepticism here. In 2023, prediction markets consistently overshot on rate cut timing. The crowd kept front-running cuts that never came. The pattern repeats.

My read: 73% is probably 10-15 points too high given current uncertainty. The path to a March cut exists, but it requires inflation to cooperate and no labor market surprises. That's a lot of things that need to go right.

The asymmetry favors the NO side here. If CPI comes in cool, the probability might tick up to 80%. If it comes in hot, this could collapse to 50% overnight. Risk-reward skews bearish on the consensus.""",
        "market_ticker": "FED-24MAR-T2.5",
        "market_title": "Will the Fed cut rates by March 2024?",
        "probability": 73,
        "generated_at": (now - timedelta(hours=2)).isoformat(),
        "close_time": (now + timedelta(days=45)).isoformat(),
        "volume": 2145000,
        "word_count": 340,
        "status": "active",
    },
    # Active analysis article
    {
        "id": "b2c3d4e5f6g7",
        "article_type": "analysis",
        "title": "Bitcoin at $100K by Year-End: What the 34% Odds Are Really Telling You",
        "teaser": "The prediction market implies roughly one-in-three odds BTC hits six figures. That pricing contains some interesting assumptions.",
        "content": """Kalshi has Bitcoin reaching $100,000 by December 31st priced at 34%. That's not dismissive, but it's not confident either. One-in-three odds for a roughly 50% move from current levels.

The bull case is straightforward: spot ETF approval could unlock billions in institutional capital. The halving in April 2024 historically precedes major rallies. Reduced supply plus increased demand equals higher prices. Simple math.

But 34% suggests the market sees meaningful obstacles. And there are several worth examining.

The ETF story has been "imminent" for years. Multiple applications are pending with the SEC. Approval would be genuinely significant—BlackRock and Fidelity bringing Bitcoin to retirement accounts is a different game than crypto-native exchanges. But the SEC has found reasons to delay before. Until ink hits paper, it's speculation.

Macro conditions matter more than crypto purists like to admit. Bitcoin still trades like a risk asset. If the Fed doesn't cut rates, or cuts less than expected, risk assets broadly could struggle. The correlation to tech stocks remains high.

The halving is interesting but priced in. Everyone knows it's coming. The question is whether supply reduction alone can drive prices when demand is the variable. Previous halvings occurred in different market structures with less institutional participation.

Volume on this contract sits around 450,000. Decent, but not the deep liquidity you'd want for a confident position either way. The market is interested but not convinced.

What could break this higher: a quick ETF approval, combined with a clear Fed pivot, combined with no major exchange blowups or regulatory surprises. That's three independent things that all need to go right.

What could break it lower: another FTX-style event would crater sentiment instantly. A regulatory crackdown in a major market. Macro risk-off that drags all speculative assets down.

I'd argue 34% is roughly fair. Maybe slightly generous to the bulls given execution risk on the catalysts. The trade here isn't directional—it's recognizing that binary events (ETF yes/no, halving impact, macro shifts) make this more of a coin flip than the pricing suggests.""",
        "market_ticker": "BTCUSD-100K-DEC",
        "market_title": "Will Bitcoin reach $100,000 by December 2024?",
        "probability": 34,
        "generated_at": (now - timedelta(hours=5)).isoformat(),
        "close_time": (now + timedelta(days=180)).isoformat(),
        "volume": 456000,
        "word_count": 380,
        "status": "active",
    },
    # Expired analysis article (with link to results)
    {
        "id": "c3d4e5f6g7h8",
        "article_type": "analysis",
        "title": "Government Shutdown Odds at 61%: The Market Might Actually Be Too Low",
        "teaser": "With three weeks until the funding deadline and no clear path forward, the current pricing looks generous to the optimists.",
        "content": """Kalshi shows 61% odds of a government shutdown in the next 30 days. That number has climbed from 54% over the past two weeks. Given what's happening in Congress, it might still be too low.

The facts: there are roughly three weeks left on the current continuing resolution. No appropriations bills have passed. The new Speaker is managing a caucus where a meaningful faction views shutdown as acceptable leverage. The dynamics are genuinely different this time.

Previous shutdown threats usually had an obvious off-ramp. Some senior member would broker a deal, leadership would whip votes, crisis averted. The current configuration doesn't have that pressure release valve. The members who want to hold the line on spending aren't bluffing—they've said as much publicly.

Over 800,000 contracts have traded on this market. That's substantial liquidity and suggests real money is taking positions. The steady drift higher in probability reflects updated information, not just noise.

The timeline creates its own problems. Even if leadership reaches a deal tomorrow, the legislative process takes time. Writing bill text, CBO scoring, floor debate, Senate passage. We're talking days of procedure even in a best-case scenario. Every day without agreement compresses the window further.

The counter-argument: nobody actually wants to be blamed for a shutdown going into an election year. The political incentives to find some face-saving compromise are strong. A short shutdown over a weekend—technically a "yes" for this market—might be the path of least resistance.

What's interesting: the market doesn't seem to be pricing in how fragile the House math is. Can leadership get 217 votes for any proposal? Based on recent floor performances, that's genuinely uncertain. The margin for error is essentially zero.

My take: this should probably trade in the high 60s or low 70s. The optimistic case requires everything to go smoothly in a Congress that hasn't demonstrated it can do that. The path to YES (shutdown) has multiple on-ramps. The path to NO (resolution) has a narrow lane.""",
        "market_ticker": "SHUTDOWN-30D",
        "market_title": "Will there be a government shutdown in the next 30 days?",
        "probability": 61,
        "generated_at": (now - timedelta(days=35)).isoformat(),
        "close_time": (now - timedelta(days=5)).isoformat(),
        "volume": 823000,
        "word_count": 380,
        "status": "resolved",
        "results_article_id": "c3d4e5f6g7h8-results",
    },
    # Results article for the shutdown market
    {
        "id": "c3d4e5f6g7h8-results",
        "article_type": "results",
        "title": "The Shutdown That Wasn't: How Congress Found Its Off-Ramp",
        "teaser": "The market had it at 61% for a shutdown. They found a deal at the last minute. Here's what the prediction market got right—and wrong.",
        "content": """The government stayed open. After weeks of brinkmanship, Congress passed a short-term continuing resolution with hours to spare. The market had priced a shutdown at 61%—turns out that was too pessimistic.

The resolution came together in classic Washington fashion: a last-minute compromise that nobody particularly liked but everyone could live with. The final vote was bipartisan, which tells you something about where the real opposition was concentrated.

What the market got right: the timeline was genuinely compressed and the political dynamics were hostile. At 61%, the market was saying "more likely than not"—and for most of the final week, that assessment felt accurate. The deal wasn't inevitable; it required several factions to back down from stated positions.

What the market missed: the off-ramp was always there, even if it wasn't visible. Leadership on both sides had stronger incentives to avoid shutdown than the loudest voices suggested. The moderates who ultimately provided the winning margin were never as committed to brinkmanship as the hardliners.

The pattern here is worth noting for future shutdown markets. Congress has a remarkably consistent record of finding last-minute solutions to self-created crises. The probability of "actually going over the cliff" tends to be lower than the rhetoric suggests.

That said, 61% wasn't crazy. In a world where the compromise talks had stalled for another 48 hours, or where the hardliner faction had held together, we'd be writing a very different article. The market captured genuine uncertainty—it just resolved on the less likely side.

For future reference: shutdown markets tend to peak in probability about 5-7 days before deadline, then decline as the pressure to deal intensifies. The 61% we saw was probably close to the high water mark for this cycle.

The broader takeaway: prediction markets are pricing probabilities, not certainties. A 61% chance means 39% of the time, it doesn't happen. This was one of those times.""",
        "market_ticker": "SHUTDOWN-30D",
        "market_title": "Will there be a government shutdown in the next 30 days?",
        "probability": 61,
        "outcome": "NO",
        "generated_at": (now - timedelta(days=4)).isoformat(),
        "close_time": (now - timedelta(days=5)).isoformat(),
        "volume": 823000,
        "word_count": 370,
        "status": "resolved",
        "original_article_id": "c3d4e5f6g7h8",
    },
    # BIG MISS - Market was very wrong (78% YES, resolved NO)
    {
        "id": "e5f6g7h8i9j0",
        "article_type": "results",
        "title": "The 78% Favorite That Crashed: How the Market Got This So Wrong",
        "teaser": "Prediction markets had this at 78% YES. It resolved NO. A case study in overconfidence.",
        "content": """This one stings. The market had priced a Supreme Court ruling in favor of the administration at 78%. It resolved the other way. That's not a minor miss—that's the crowd getting it substantially wrong.

Let's unpack what happened.

The conventional wisdom was solid on paper. The administration had won at the appellate level. The court's recent composition suggested a favorable lean. Legal analysts—the credentialed kind—were largely aligned with the market's read. 78% felt earned, not inflated.

And then the ruling came down 6-3 the other way.

What the market missed: the legal question was narrower than the political framing suggested. The majority opinion focused on procedural grounds that most market participants probably weren't tracking closely. The justices who crossed ideological lines did so on technical legal reasoning, not political alignment.

This is a recurring failure mode in prediction markets involving legal outcomes. Participants tend to model the court as a political body and underweight the possibility of legalistic surprises. The 78% reflected political analysis, not legal analysis. Those aren't the same thing.

The volume on this contract was substantial—over 1.2 million shares traded. That means a lot of money was on the wrong side. The people who bought NO at 22 cents collected at a dollar. That's a 4.5x return for fading the consensus.

Worth noting: 78% still means 22% of the time, the other thing happens. Markets aren't broken when unlikely outcomes occur. But this particular miss feels more like a systematic blind spot than bad luck. The crowd was confident for reasons that turned out to be the wrong reasons.

The lesson here: legal markets deserve more epistemic humility than they typically get. Courts are not legislatures. Oral arguments are not reliable signals. And the base rate of prediction market misses on Supreme Court cases is higher than most participants seem to price in.

For what it's worth, I had this one wrong too. The consensus felt right. It wasn't.""",
        "market_ticker": "SCOTUS-ADMIN-2024",
        "market_title": "Will SCOTUS rule in favor of the administration?",
        "probability": 78,
        "outcome": "NO",
        "generated_at": (now - timedelta(days=2)).isoformat(),
        "close_time": (now - timedelta(days=3)).isoformat(),
        "volume": 1245000,
        "word_count": 350,
        "status": "resolved",
        "original_article_id": None,
    },
    # Another active article
    {
        "id": "d4e5f6g7h8i9",
        "article_type": "analysis",
        "title": "Will AI Replace 10% of Jobs by 2025? The Market Says Probably Not",
        "teaser": "At 18% odds, prediction markets are skeptical of near-term AI job displacement. The timeline might be the problem.",
        "content": """The question of AI job displacement has moved from theoretical to tradeable. Kalshi has a market on whether AI will replace 10% or more of current jobs by end of 2025, and it's pricing that outcome at just 18%.

That's a remarkably low number given the breathless coverage of AI capabilities. But the market might be onto something about timelines.

The 10% threshold is significant. We're talking about roughly 16 million jobs in the US alone. Even if AI can theoretically perform certain tasks, the actual displacement requires companies to implement systems, retrain workflows, and make hiring decisions differently. That takes time.

Current AI adoption data supports the skepticism. Most enterprises are still in pilot phases. The gap between "AI can do this demo" and "AI is handling this at scale in production" remains substantial. Integration challenges, reliability concerns, and organizational inertia all slow deployment.

The labor market data shows minimal AI impact so far. Unemployment remains low. Job openings are still elevated in most sectors. If mass displacement were imminent, we'd expect to see leading indicators—and we're not.

What could make the market wrong: a major breakthrough in AI agents that handle complex, multi-step tasks reliably. Or a recession that gives companies cover to cut headcount aggressively while blaming AI. Either scenario could accelerate the timeline.

The 18% feels about right for the specific timeframe. The question isn't whether AI will displace jobs—it almost certainly will eventually. The question is whether 2025 is too soon. Based on current adoption curves, it probably is.

My read: this market is correctly pricing the implementation lag between AI capability and AI deployment. The hype cycle and the reality cycle operate on different timescales.""",
        "market_ticker": "AI-JOBS-2025",
        "market_title": "Will AI replace 10%+ of jobs by 2025?",
        "probability": 18,
        "generated_at": (now - timedelta(hours=8)).isoformat(),
        "close_time": (now + timedelta(days=340)).isoformat(),
        "volume": 234000,
        "word_count": 320,
        "status": "active",
    },
]


def seed_cache():
    """Seed the cache with example articles"""
    cache = get_cache()

    # Clear existing and add fresh
    cache.save_articles([])

    for article in EXAMPLE_ARTICLES:
        cache.add_article(article)
        type_label = article.get("article_type", "analysis").upper()
        status = "EXPIRED" if article.get("status") == "resolved" else "ACTIVE"
        print(f"[{type_label}] [{status}] {article['title'][:50]}...")

    print(f"\nSeeded {len(EXAMPLE_ARTICLES)} articles to cache.")
    print("  - 3 active analysis articles")
    print("  - 1 expired analysis article")
    print("  - 1 results article (normal)")
    print("  - 1 results article (BIG MISS - 78% wrong)")


if __name__ == "__main__":
    seed_cache()
