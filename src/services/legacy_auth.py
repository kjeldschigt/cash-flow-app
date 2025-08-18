"""
Legacy authentication service for backward compatibility.
"""

import sqlite3
import bcrypt
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

def init_auth_db():
    """Initialize legacy authentication database."""
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error initializing auth database: {str(e)}")
        return False

def register_user(email: str, password: str) -> Tuple[bool, str]:
    """Register a new user in legacy database."""
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            conn.close()
            return False, "User already exists"
        
        # Hash password
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(password_bytes, salt)
        
        # Insert user
        cursor.execute(
            "INSERT INTO users (email, password_hash) VALUES (?, ?)",
            (email, password_hash)
        )
        
        conn.commit()
        conn.close()
        return True, "User registered successfully"
        
    except Exception as e:
        logger.error(f"Error registering user: {str(e)}")
        return False, f"Registration failed: {str(e)}"
