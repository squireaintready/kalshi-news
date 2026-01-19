"""
Kalshi API Client for fetching prediction markets data
"""
import requests
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import config

logger = logging.getLogger(__name__)


class KalshiAPIError(Exception):
    """Custom exception for Kalshi API errors"""
    pass


class KalshiClient:
    """Client for interacting with the Kalshi prediction markets API"""

    def __init__(self):
        self.base_url = config.KALSHI_API_BASE
        self.session = requests.Session()
        self.token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None

    def _ensure_authenticated(self) -> None:
        """Ensure we have a valid auth token"""
        if self.token and self.token_expiry and datetime.now() < self.token_expiry:
            return

        if not config.KALSHI_EMAIL or not config.KALSHI_PASSWORD:
            logger.warning("Kalshi credentials not configured, using public endpoints only")
            return

        self._login()

    def _login(self) -> None:
        """Authenticate with Kalshi API"""
        try:
            response = self.session.post(
                f"{self.base_url}/login",
                json={
                    "email": config.KALSHI_EMAIL,
                    "password": config.KALSHI_PASSWORD
                },
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            data = response.json()

            self.token = data.get("token")
            # Token typically valid for 24 hours, refresh after 23
            self.token_expiry = datetime.now() + timedelta(hours=23)
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
            logger.info("Successfully authenticated with Kalshi API")

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to authenticate with Kalshi: {e}")
            raise KalshiAPIError(f"Authentication failed: {e}")

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make an API request with error handling"""
        url = f"{self.base_url}{endpoint}"

        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error from Kalshi API: {e}")
            raise KalshiAPIError(f"API request failed: {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            raise KalshiAPIError(f"Request failed: {e}")
        except ValueError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            raise KalshiAPIError(f"Invalid response: {e}")

    def get_events(self, limit: int = 20, status: str = "open") -> List[Dict[str, Any]]:
        """
        Fetch events from Kalshi
        Events are the top-level groupings (e.g., "2024 Presidential Election")
        """
        try:
            self._ensure_authenticated()
            params = {
                "limit": limit,
                "status": status,
            }
            data = self._make_request("GET", "/events", params=params)
            return data.get("events", [])
        except KalshiAPIError:
            logger.warning("Failed to fetch events, returning empty list")
            return []

    def get_markets(self,
                    limit: int = 50,
                    status: str = "open",
                    cursor: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch active markets from Kalshi
        Markets are individual prediction contracts
        """
        try:
            self._ensure_authenticated()
            params = {
                "limit": limit,
                "status": status,
            }
            if cursor:
                params["cursor"] = cursor

            data = self._make_request("GET", "/markets", params=params)
            return data
        except KalshiAPIError as e:
            logger.warning(f"Failed to fetch markets: {e}")
            return {"markets": [], "cursor": None}

    def get_market(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Fetch details for a specific market by ticker"""
        try:
            self._ensure_authenticated()
            data = self._make_request("GET", f"/markets/{ticker}")
            return data.get("market")
        except KalshiAPIError:
            logger.warning(f"Failed to fetch market {ticker}")
            return None

    def get_market_history(self, ticker: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch price history for a market"""
        try:
            self._ensure_authenticated()
            params = {"limit": limit}
            data = self._make_request("GET", f"/markets/{ticker}/history", params=params)
            return data.get("history", [])
        except KalshiAPIError:
            return []

    def get_trending_markets(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get trending/active markets based on volume and recent activity
        This filters for markets that would make interesting articles
        """
        markets_data = self.get_markets(limit=100, status="open")
        markets = markets_data.get("markets", [])

        if not markets:
            return []

        # Score markets by "interestingness" for article generation
        scored_markets = []
        for market in markets:
            score = self._calculate_market_score(market)
            if score > 0:
                market["_interest_score"] = score
                scored_markets.append(market)

        # Sort by interest score and return top N
        scored_markets.sort(key=lambda m: m.get("_interest_score", 0), reverse=True)
        return scored_markets[:limit]

    def _calculate_market_score(self, market: Dict[str, Any]) -> float:
        """
        Calculate an "interestingness" score for a market
        Higher scores = better candidates for articles
        """
        score = 0.0

        # Volume indicates activity/interest
        volume = market.get("volume", 0) or 0
        volume_24h = market.get("volume_24h", 0) or 0
        score += min(volume / 1000, 50)  # Cap contribution
        score += min(volume_24h / 100, 30)

        # Markets with odds between 20-80% are more interesting (uncertain outcomes)
        yes_price = market.get("yes_bid", 0) or market.get("last_price", 50)
        if 20 <= yes_price <= 80:
            score += 20
        elif 10 <= yes_price <= 90:
            score += 10

        # Recent price movement indicates developing story
        # (would need history endpoint for accurate calculation)

        # Open interest shows sustained engagement
        open_interest = market.get("open_interest", 0) or 0
        score += min(open_interest / 500, 20)

        # Penalize markets closing very soon (not enough to write about)
        close_time = market.get("close_time")
        if close_time:
            try:
                close_dt = datetime.fromisoformat(close_time.replace("Z", "+00:00"))
                hours_until_close = (close_dt - datetime.now(close_dt.tzinfo)).total_seconds() / 3600
                if hours_until_close < 2:
                    score *= 0.3
                elif hours_until_close < 24:
                    score *= 0.7
            except (ValueError, TypeError):
                pass

        return score

    def enrich_market_data(self, market: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich market data with additional context for article generation
        """
        enriched = market.copy()

        # Calculate human-readable probability
        yes_price = market.get("yes_bid") or market.get("last_price", 50)
        enriched["probability_pct"] = yes_price
        enriched["probability_readable"] = f"{yes_price}%"

        # Format close time
        close_time = market.get("close_time")
        if close_time:
            try:
                close_dt = datetime.fromisoformat(close_time.replace("Z", "+00:00"))
                enriched["close_time_readable"] = close_dt.strftime("%B %d, %Y at %I:%M %p UTC")
                days_until = (close_dt - datetime.now(close_dt.tzinfo)).days
                enriched["days_until_close"] = days_until
            except (ValueError, TypeError):
                enriched["close_time_readable"] = "Unknown"
                enriched["days_until_close"] = None

        # Get price history if available
        ticker = market.get("ticker")
        if ticker:
            history = self.get_market_history(ticker, limit=50)
            if history:
                enriched["price_history"] = history
                # Calculate recent movement
                if len(history) >= 2:
                    recent_price = history[0].get("yes_price", yes_price)
                    older_price = history[-1].get("yes_price", yes_price)
                    enriched["price_change"] = recent_price - older_price
                    enriched["price_change_direction"] = "up" if enriched["price_change"] > 0 else "down"

        return enriched


# Singleton instance for easy importing
_client_instance: Optional[KalshiClient] = None

def get_client() -> KalshiClient:
    """Get or create the Kalshi client singleton"""
    global _client_instance
    if _client_instance is None:
        _client_instance = KalshiClient()
    return _client_instance
