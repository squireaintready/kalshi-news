"""
User authentication and management
"""
import logging
import hashlib
import secrets
from datetime import datetime
from typing import Optional, Dict, Any, List
from flask_login import UserMixin
import config

logger = logging.getLogger(__name__)


class User(UserMixin):
    """User model for Flask-Login"""

    def __init__(self, user_data: Dict[str, Any]):
        self.id = user_data.get("id")
        self.email = user_data.get("email")
        self.password_hash = user_data.get("password_hash")
        self.is_admin = user_data.get("is_admin", False)
        self.kalshi_email = user_data.get("kalshi_email")
        self.kalshi_connected = user_data.get("kalshi_connected", False)
        self.created_at = user_data.get("created_at")
        self.last_login = user_data.get("last_login")

    def get_id(self):
        return str(self.id)

    def check_password(self, password: str) -> bool:
        """Verify password against hash"""
        return self.password_hash == self._hash_password(password, self.id)

    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        """Hash password with salt"""
        return hashlib.sha256(f"{password}{salt}{config.FLASK_SECRET_KEY}".encode()).hexdigest()


class UserManager:
    """Manages user operations in PostgreSQL"""

    def __init__(self):
        self._ensure_table()

    def _get_connection(self):
        """Get database connection"""
        import psycopg2
        return psycopg2.connect(config.DATABASE_URL)

    def _ensure_table(self):
        """Create users table if not exists"""
        if not config.DATABASE_URL:
            logger.warning("DATABASE_URL not set, user management disabled")
            return

        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id VARCHAR(32) PRIMARY KEY,
                        email VARCHAR(255) UNIQUE NOT NULL,
                        password_hash VARCHAR(64) NOT NULL,
                        is_admin BOOLEAN DEFAULT FALSE,
                        kalshi_email VARCHAR(255),
                        kalshi_connected BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_login TIMESTAMP
                    )
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS user_bets (
                        id SERIAL PRIMARY KEY,
                        user_id VARCHAR(32) REFERENCES users(id),
                        market_ticker VARCHAR(255) NOT NULL,
                        position VARCHAR(10),
                        quantity INTEGER,
                        average_price FLOAT,
                        synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id, market_ticker)
                    )
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS user_categories (
                        id SERIAL PRIMARY KEY,
                        user_id VARCHAR(32) REFERENCES users(id),
                        keyword VARCHAR(100) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id, keyword)
                    )
                """)
                conn.commit()
                logger.info("User tables initialized")
        except Exception as e:
            logger.error(f"Failed to create user tables: {e}")
        finally:
            conn.close()

    def create_user(self, email: str, password: str) -> Optional[User]:
        """Create a new user"""
        conn = self._get_connection()
        try:
            user_id = secrets.token_hex(16)
            password_hash = User._hash_password(password, user_id)

            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO users (id, email, password_hash)
                    VALUES (%s, %s, %s)
                    RETURNING id, email, password_hash, is_admin, kalshi_email,
                              kalshi_connected, created_at, last_login
                """, (user_id, email.lower(), password_hash))
                row = cur.fetchone()
                conn.commit()

                if row:
                    return User({
                        "id": row[0],
                        "email": row[1],
                        "password_hash": row[2],
                        "is_admin": row[3],
                        "kalshi_email": row[4],
                        "kalshi_connected": row[5],
                        "created_at": row[6],
                        "last_login": row[7]
                    })
            return None
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            return None
        finally:
            conn.close()

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, email, password_hash, is_admin, kalshi_email,
                           kalshi_connected, created_at, last_login
                    FROM users WHERE email = %s
                """, (email.lower(),))
                row = cur.fetchone()
                if row:
                    return User({
                        "id": row[0],
                        "email": row[1],
                        "password_hash": row[2],
                        "is_admin": row[3],
                        "kalshi_email": row[4],
                        "kalshi_connected": row[5],
                        "created_at": row[6],
                        "last_login": row[7]
                    })
            return None
        except Exception as e:
            logger.error(f"Failed to get user: {e}")
            return None
        finally:
            conn.close()

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, email, password_hash, is_admin, kalshi_email,
                           kalshi_connected, created_at, last_login
                    FROM users WHERE id = %s
                """, (user_id,))
                row = cur.fetchone()
                if row:
                    return User({
                        "id": row[0],
                        "email": row[1],
                        "password_hash": row[2],
                        "is_admin": row[3],
                        "kalshi_email": row[4],
                        "kalshi_connected": row[5],
                        "created_at": row[6],
                        "last_login": row[7]
                    })
            return None
        except Exception as e:
            logger.error(f"Failed to get user by id: {e}")
            return None
        finally:
            conn.close()

    def update_last_login(self, user_id: str) -> None:
        """Update user's last login time"""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE users SET last_login = %s WHERE id = %s",
                    (datetime.utcnow(), user_id)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to update last login: {e}")
        finally:
            conn.close()

    def set_kalshi_email(self, user_id: str, kalshi_email: str) -> bool:
        """Set user's Kalshi email for matching"""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE users
                    SET kalshi_email = %s, kalshi_connected = TRUE
                    WHERE id = %s
                """, (kalshi_email, user_id))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to set Kalshi email: {e}")
            return False
        finally:
            conn.close()

    def add_user_ticker(self, user_id: str, ticker: str, title: str = None) -> bool:
        """Add a ticker to user's watchlist"""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                # Add title column if it doesn't exist
                cur.execute("""
                    ALTER TABLE user_bets ADD COLUMN IF NOT EXISTS title TEXT
                """)
                cur.execute("""
                    INSERT INTO user_bets (user_id, market_ticker, position, title)
                    VALUES (%s, %s, 'WATCHING', %s)
                    ON CONFLICT (user_id, market_ticker) DO UPDATE SET title = EXCLUDED.title
                """, (user_id, ticker.upper().strip(), title))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to add ticker: {e}")
            return False
        finally:
            conn.close()

    def remove_user_ticker(self, user_id: str, ticker: str) -> bool:
        """Remove a ticker from user's watchlist"""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM user_bets WHERE user_id = %s AND market_ticker = %s",
                    (user_id, ticker.upper().strip())
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to remove ticker: {e}")
            return False
        finally:
            conn.close()

    def add_user_category(self, user_id: str, keyword: str) -> bool:
        """Add a category/keyword to follow"""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                # Ensure table exists
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS user_categories (
                        id SERIAL PRIMARY KEY,
                        user_id VARCHAR(32) REFERENCES users(id),
                        keyword VARCHAR(100) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id, keyword)
                    )
                """)
                cur.execute("""
                    INSERT INTO user_categories (user_id, keyword)
                    VALUES (%s, %s)
                    ON CONFLICT (user_id, keyword) DO NOTHING
                """, (user_id, keyword.lower().strip()))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to add category: {e}")
            return False
        finally:
            conn.close()

    def remove_user_category(self, user_id: str, keyword: str) -> bool:
        """Remove a category from user's watchlist"""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM user_categories WHERE user_id = %s AND keyword = %s",
                    (user_id, keyword.lower().strip())
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to remove category: {e}")
            return False
        finally:
            conn.close()

    def get_user_categories(self, user_id: str) -> List[str]:
        """Get user's followed categories"""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT keyword FROM user_categories WHERE user_id = %s ORDER BY created_at DESC",
                    (user_id,)
                )
                return [row[0] for row in cur.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get categories: {e}")
            return []
        finally:
            conn.close()

    def save_user_bets(self, user_id: str, bets: List[Dict[str, Any]]) -> bool:
        """Save user's Kalshi positions"""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                for bet in bets:
                    cur.execute("""
                        INSERT INTO user_bets (user_id, market_ticker, position, quantity, average_price)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (user_id, market_ticker) DO UPDATE SET
                            position = EXCLUDED.position,
                            quantity = EXCLUDED.quantity,
                            average_price = EXCLUDED.average_price,
                            synced_at = CURRENT_TIMESTAMP
                    """, (
                        user_id,
                        bet.get("market_ticker"),
                        bet.get("position"),
                        bet.get("quantity"),
                        bet.get("average_price")
                    ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to save user bets: {e}")
            return False
        finally:
            conn.close()

    def get_user_bets(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's saved bets"""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT market_ticker, position, quantity, average_price, synced_at,
                           COALESCE(title, market_ticker) as title
                    FROM user_bets WHERE user_id = %s
                    ORDER BY synced_at DESC
                """, (user_id,))
                rows = cur.fetchall()
                return [
                    {
                        "market_ticker": row[0],
                        "position": row[1],
                        "quantity": row[2],
                        "average_price": row[3],
                        "synced_at": row[4].isoformat() if row[4] else None,
                        "title": row[5]
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Failed to get user bets: {e}")
            return []
        finally:
            conn.close()


# Singleton
_user_manager: Optional[UserManager] = None

def get_user_manager() -> UserManager:
    """Get or create user manager singleton"""
    global _user_manager
    if _user_manager is None:
        _user_manager = UserManager()
    return _user_manager
