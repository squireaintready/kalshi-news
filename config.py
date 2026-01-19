"""
Configuration settings for the Kalshi News Article Platform
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Kalshi API Configuration
KALSHI_API_BASE = "https://api.elections.kalshi.com/trade-api/v2"
KALSHI_EMAIL = os.getenv("KALSHI_EMAIL", "")
KALSHI_PASSWORD = os.getenv("KALSHI_PASSWORD", "")

# LLM Configuration (supports both OpenAI and Anthropic)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "anthropic")  # "openai" or "anthropic"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Flask Configuration
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "kalshi-news-secret-key-change-me")
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "False").lower() == "true"

# Cache Configuration
CACHE_TYPE = os.getenv("CACHE_TYPE", "file")  # "file" or "redis"
CACHE_DIR = os.getenv("CACHE_DIR", "cache")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))  # 1 hour default

# Scheduler Configuration
ARTICLE_REFRESH_INTERVAL_MINUTES = int(os.getenv("ARTICLE_REFRESH_INTERVAL", "20"))
RESOLUTION_CHECK_INTERVAL_MINUTES = int(os.getenv("RESOLUTION_CHECK_INTERVAL", "10"))
MAX_MARKETS_TO_FETCH = int(os.getenv("MAX_MARKETS_TO_FETCH", "15"))
MAX_ARTICLES_TO_GENERATE = int(os.getenv("MAX_ARTICLES_TO_GENERATE", "3"))
MAX_RESULTS_ARTICLES_TO_GENERATE = int(os.getenv("MAX_RESULTS_ARTICLES", "2"))

# Article Generation Settings
MIN_ARTICLE_LENGTH = 400
MAX_ARTICLE_LENGTH = 650
