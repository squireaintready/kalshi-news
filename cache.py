"""
Caching system for articles and market data
Supports both file-based and Redis caching
"""
import json
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path

import config

logger = logging.getLogger(__name__)


class CacheBackend(ABC):
    """Abstract base class for cache backends"""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Retrieve a value from cache"""
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Store a value in cache"""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete a value from cache"""
        pass

    @abstractmethod
    def get_all_articles(self) -> List[Dict[str, Any]]:
        """Get all cached articles"""
        pass


class FileCache(CacheBackend):
    """File-based cache implementation"""

    def __init__(self, cache_dir: str = None):
        self.cache_dir = Path(cache_dir or config.CACHE_DIR)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.articles_file = self.cache_dir / "articles.json"
        self.metadata_file = self.cache_dir / "metadata.json"
        logger.info(f"Initialized file cache at {self.cache_dir}")

    def _get_cache_path(self, key: str) -> Path:
        """Get file path for a cache key"""
        safe_key = "".join(c if c.isalnum() else "_" for c in key)
        return self.cache_dir / f"{safe_key}.json"

    def get(self, key: str) -> Optional[Any]:
        """Retrieve a value from file cache"""
        cache_path = self._get_cache_path(key)
        if not cache_path.exists():
            return None

        try:
            with open(cache_path, "r") as f:
                data = json.load(f)

            # Check TTL
            if "expires_at" in data:
                expires_at = datetime.fromisoformat(data["expires_at"])
                if datetime.utcnow() > expires_at:
                    self.delete(key)
                    return None

            return data.get("value")
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to read cache key {key}: {e}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Store a value in file cache"""
        cache_path = self._get_cache_path(key)
        ttl = ttl or config.CACHE_TTL

        try:
            data = {
                "value": value,
                "created_at": datetime.utcnow().isoformat(),
            }
            if ttl:
                from datetime import timedelta
                expires = datetime.utcnow() + timedelta(seconds=ttl)
                data["expires_at"] = expires.isoformat()

            with open(cache_path, "w") as f:
                json.dump(data, f, indent=2)

            return True
        except IOError as e:
            logger.error(f"Failed to write cache key {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete a value from file cache"""
        cache_path = self._get_cache_path(key)
        try:
            if cache_path.exists():
                cache_path.unlink()
            return True
        except IOError as e:
            logger.error(f"Failed to delete cache key {key}: {e}")
            return False

    def get_all_articles(self) -> List[Dict[str, Any]]:
        """Get all cached articles"""
        if not self.articles_file.exists():
            return []

        try:
            with open(self.articles_file, "r") as f:
                data = json.load(f)
            return data.get("articles", [])
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to read articles cache: {e}")
            return []

    def save_articles(self, articles: List[Dict[str, Any]]) -> bool:
        """Save articles to cache file"""
        try:
            with open(self.articles_file, "w") as f:
                json.dump({
                    "articles": articles,
                    "updated_at": datetime.utcnow().isoformat()
                }, f, indent=2)
            logger.info(f"Saved {len(articles)} articles to cache")
            return True
        except IOError as e:
            logger.error(f"Failed to save articles: {e}")
            return False

    def add_article(self, article: Dict[str, Any]) -> bool:
        """Add a single article to the cache"""
        articles = self.get_all_articles()

        # Remove existing article with same ID if present
        articles = [a for a in articles if a.get("id") != article.get("id")]

        # Add new article at the beginning
        articles.insert(0, article)

        # Keep only the most recent articles (configurable limit)
        max_articles = 50
        articles = articles[:max_articles]

        return self.save_articles(articles)

    def get_article_by_id(self, article_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific article by ID"""
        articles = self.get_all_articles()
        for article in articles:
            if article.get("id") == article_id:
                return article
        return None


class RedisCache(CacheBackend):
    """Redis-based cache implementation"""

    def __init__(self, redis_url: str = None):
        try:
            import redis
        except ImportError:
            raise ImportError("redis package not installed. Run: pip install redis")

        self.redis_url = redis_url or config.REDIS_URL
        self.client = redis.from_url(self.redis_url)
        self.articles_key = "kalshi_news:articles"
        logger.info(f"Initialized Redis cache at {self.redis_url}")

    def get(self, key: str) -> Optional[Any]:
        """Retrieve a value from Redis"""
        try:
            data = self.client.get(f"kalshi_news:{key}")
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Redis get error for key {key}: {e}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Store a value in Redis"""
        ttl = ttl or config.CACHE_TTL
        try:
            data = json.dumps(value)
            self.client.setex(f"kalshi_news:{key}", ttl, data)
            return True
        except Exception as e:
            logger.error(f"Redis set error for key {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete a value from Redis"""
        try:
            self.client.delete(f"kalshi_news:{key}")
            return True
        except Exception as e:
            logger.error(f"Redis delete error for key {key}: {e}")
            return False

    def get_all_articles(self) -> List[Dict[str, Any]]:
        """Get all cached articles from Redis"""
        try:
            data = self.client.get(self.articles_key)
            if data:
                return json.loads(data)
            return []
        except Exception as e:
            logger.error(f"Failed to get articles from Redis: {e}")
            return []

    def save_articles(self, articles: List[Dict[str, Any]]) -> bool:
        """Save articles to Redis"""
        try:
            data = json.dumps(articles)
            self.client.set(self.articles_key, data)
            return True
        except Exception as e:
            logger.error(f"Failed to save articles to Redis: {e}")
            return False

    def add_article(self, article: Dict[str, Any]) -> bool:
        """Add a single article to Redis cache"""
        articles = self.get_all_articles()
        articles = [a for a in articles if a.get("id") != article.get("id")]
        articles.insert(0, article)
        articles = articles[:50]
        return self.save_articles(articles)

    def get_article_by_id(self, article_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific article by ID"""
        articles = self.get_all_articles()
        for article in articles:
            if article.get("id") == article_id:
                return article
        return None


# Factory function to get appropriate cache backend
_cache_instance: Optional[CacheBackend] = None

def get_cache() -> CacheBackend:
    """Get or create the cache singleton based on configuration"""
    global _cache_instance
    if _cache_instance is None:
        if config.CACHE_TYPE.lower() == "redis":
            _cache_instance = RedisCache()
        else:
            _cache_instance = FileCache()
    return _cache_instance
