"""Database initialization utilities."""

import os
import sqlite3
import logging
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


def check_encryption_key() -> str:
    """
    Check for encryption key in environment variables.

    Returns:
        str: The encryption key

    Raises:
        ValueError: If key is missing in production
    """
    encryption_key = os.getenv("ENCRYPTION_MASTER_KEY")

    if not encryption_key:
        # Check if we're in production
        environment = os.getenv("ENVIRONMENT", "development").lower()

        if environment == "production":
            raise ValueError(
                "ENCRYPTION_MASTER_KEY environment variable is required in production. "
                "Please set this to a secure 256-bit key."
            )
        else:
            # Development fallback - generate a warning
            encryption_key = "dev-key-change-in-production-" + "0" * 32
            logger.warning(
                "⚠️  Using default encryption key for development. "
                "Set ENCRYPTION_MASTER_KEY environment variable for production!"
            )

    return encryption_key


def get_database_info() -> Dict[str, Any]:
    """Get information about the current database state."""
    info = {
        "exists": False,
        "size": 0,
        "tables": [],
        "user_count": 0,
        "last_modified": None,
    }

    try:
        db_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "cash_flow.db"
        )

        if os.path.exists(db_path):
            info["exists"] = True
            info["size"] = os.path.getsize(db_path)
            info["last_modified"] = datetime.fromtimestamp(os.path.getmtime(db_path))

            # Get table information
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            info["tables"] = [row[0] for row in cursor.fetchall()]

            # Get user count if users table exists
            if "users" in info["tables"]:
                cursor.execute("SELECT COUNT(*) FROM users")
                info["user_count"] = cursor.fetchone()[0]

            conn.close()

    except Exception as e:
        logger.error(f"Error getting database info: {str(e)}")

    return info


def initialize_database() -> Dict[str, Any]:
    """Initialize the database with required tables."""
    try:
        # Import from the correct location
        from ...utils.db_init import initialize_database as legacy_init

        return legacy_init()
    except ImportError:
        # Fallback implementation
        db_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "cash_flow.db"
        )

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Create users table if it doesn't exist
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT DEFAULT 'user',
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                )
            """
            )

            # Create settings table if it doesn't exist
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE NOT NULL,
                    value TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            conn.commit()
            conn.close()

            return {
                "success": True,
                "message": "Database initialized successfully",
                "errors": [],
            }

        except Exception as e:
            logger.error(f"Database initialization error: {str(e)}")
            return {
                "success": False,
                "message": "Database initialization failed",
                "errors": [str(e)],
            }
