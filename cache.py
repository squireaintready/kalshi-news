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


class PostgresCache(CacheBackend):
    """PostgreSQL-based cache implementation for persistent article storage"""

    def __init__(self, database_url: str = None):
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
        except ImportError:
            raise ImportError("psycopg2-binary package not installed. Run: pip install psycopg2-binary")

        self.database_url = database_url or config.DATABASE_URL
        self._init_db()
        logger.info("Initialized PostgreSQL cache")

    def _get_connection(self):
        """Get a database connection"""
        import psycopg2
        return psycopg2.connect(self.database_url)

    def _init_db(self):
        """Initialize database tables"""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS articles (
                        id VARCHAR(255) PRIMARY KEY,
                        article_type VARCHAR(50),
                        title TEXT,
                        teaser TEXT,
                        content TEXT,
                        market_ticker VARCHAR(255),
                        market_title TEXT,
                        probability FLOAT,
                        outcome VARCHAR(10),
                        generated_at TIMESTAMP,
                        close_time TEXT,
                        volume INTEGER,
                        status VARCHAR(50),
                        word_count INTEGER,
                        original_article_id VARCHAR(255),
                        data JSONB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS cache (
                        key VARCHAR(255) PRIMARY KEY,
                        value JSONB,
                        expires_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
                logger.info("PostgreSQL tables initialized")
        finally:
            conn.close()

    def get(self, key: str) -> Optional[Any]:
        """Retrieve a value from PostgreSQL cache"""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT value, expires_at FROM cache WHERE key = %s",
                    (key,)
                )
                row = cur.fetchone()
                if row:
                    value, expires_at = row
                    if expires_at and datetime.utcnow() > expires_at:
                        self.delete(key)
                        return None
                    return value
                return None
        finally:
            conn.close()

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Store a value in PostgreSQL cache"""
        ttl = ttl or config.CACHE_TTL
        conn = self._get_connection()
        try:
            from datetime import timedelta
            expires_at = datetime.utcnow() + timedelta(seconds=ttl) if ttl else None
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO cache (key, value, expires_at)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (key) DO UPDATE SET
                        value = EXCLUDED.value,
                        expires_at = EXCLUDED.expires_at,
                        created_at = CURRENT_TIMESTAMP
                """, (key, json.dumps(value), expires_at))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"PostgreSQL set error for key {key}: {e}")
            return False
        finally:
            conn.close()

    def delete(self, key: str) -> bool:
        """Delete a value from PostgreSQL cache"""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM cache WHERE key = %s", (key,))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"PostgreSQL delete error for key {key}: {e}")
            return False
        finally:
            conn.close()

    def get_all_articles(self) -> List[Dict[str, Any]]:
        """Get all articles from PostgreSQL"""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, article_type, title, teaser, content, market_ticker,
                           market_title, probability, outcome, generated_at, close_time,
                           volume, status, word_count, original_article_id, data
                    FROM articles
                    ORDER BY created_at DESC
                    LIMIT 50
                """)
                rows = cur.fetchall()
                articles = []
                for row in rows:
                    article = {
                        "id": row[0],
                        "article_type": row[1],
                        "title": row[2],
                        "teaser": row[3],
                        "content": row[4],
                        "market_ticker": row[5],
                        "market_title": row[6],
                        "probability": row[7],
                        "outcome": row[8],
                        "generated_at": row[9].isoformat() if row[9] else None,
                        "close_time": row[10],
                        "volume": row[11],
                        "status": row[12],
                        "word_count": row[13],
                        "original_article_id": row[14],
                    }
                    if row[15]:
                        article.update(row[15])
                    articles.append(article)
                return articles
        except Exception as e:
            logger.error(f"Failed to get articles from PostgreSQL: {e}")
            return []
        finally:
            conn.close()

    def save_articles(self, articles: List[Dict[str, Any]]) -> bool:
        """Save multiple articles (used for bulk operations)"""
        for article in articles:
            self.add_article(article)
        return True

    def add_article(self, article: Dict[str, Any]) -> bool:
        """Add a single article to PostgreSQL"""
        conn = self._get_connection()
        try:
            generated_at = None
            if article.get("generated_at"):
                try:
                    generated_at = datetime.fromisoformat(article["generated_at"].replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    generated_at = datetime.utcnow()

            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO articles (id, article_type, title, teaser, content, market_ticker,
                                         market_title, probability, outcome, generated_at, close_time,
                                         volume, status, word_count, original_article_id, data)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        title = EXCLUDED.title,
                        teaser = EXCLUDED.teaser,
                        content = EXCLUDED.content,
                        status = EXCLUDED.status,
                        data = EXCLUDED.data
                """, (
                    article.get("id"),
                    article.get("article_type"),
                    article.get("title"),
                    article.get("teaser"),
                    article.get("content"),
                    article.get("market_ticker"),
                    article.get("market_title"),
                    article.get("probability"),
                    article.get("outcome"),
                    generated_at,
                    article.get("close_time"),
                    article.get("volume"),
                    article.get("status"),
                    article.get("word_count"),
                    article.get("original_article_id"),
                    json.dumps({k: v for k, v in article.items() if k not in [
                        "id", "article_type", "title", "teaser", "content", "market_ticker",
                        "market_title", "probability", "outcome", "generated_at", "close_time",
                        "volume", "status", "word_count", "original_article_id"
                    ]})
                ))
                conn.commit()
            logger.info(f"Saved article to PostgreSQL: {article.get('title', '')[:50]}")
            return True
        except Exception as e:
            logger.error(f"Failed to save article to PostgreSQL: {e}")
            return False
        finally:
            conn.close()

    def get_article_by_id(self, article_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific article by ID"""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, article_type, title, teaser, content, market_ticker,
                           market_title, probability, outcome, generated_at, close_time,
                           volume, status, word_count, original_article_id, data
                    FROM articles WHERE id = %s
                """, (article_id,))
                row = cur.fetchone()
                if row:
                    article = {
                        "id": row[0],
                        "article_type": row[1],
                        "title": row[2],
                        "teaser": row[3],
                        "content": row[4],
                        "market_ticker": row[5],
                        "market_title": row[6],
                        "probability": row[7],
                        "outcome": row[8],
                        "generated_at": row[9].isoformat() if row[9] else None,
                        "close_time": row[10],
                        "volume": row[11],
                        "status": row[12],
                        "word_count": row[13],
                        "original_article_id": row[14],
                    }
                    if row[15]:
                        article.update(row[15])
                    return article
                return None
        except Exception as e:
            logger.error(f"Failed to get article from PostgreSQL: {e}")
            return None
        finally:
            conn.close()


# Factory function to get appropriate cache backend
_cache_instance: Optional[CacheBackend] = None

def get_cache() -> CacheBackend:
    """Get or create the cache singleton based on configuration"""
    global _cache_instance
    if _cache_instance is None:
        cache_type = config.CACHE_TYPE.lower()
        if cache_type == "postgres" and config.DATABASE_URL:
            _cache_instance = PostgresCache()
        elif cache_type == "redis":
            _cache_instance = RedisCache()
        else:
            _cache_instance = FileCache()
    return _cache_instance
