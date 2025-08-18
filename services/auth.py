import sqlite3
import bcrypt
import streamlit as st
from datetime import datetime
import os
import uuid
import logging
from typing import Optional, Tuple, Dict, Any

logger = logging.getLogger(__name__)

def get_db_connection():
    """Get database connection to main cashflow database"""
    return sqlite3.connect("cashflow.db")

def create_default_admin_user() -> Optional[str]:
    """Create default admin user if no users exist. Returns password if created."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if any users exist
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        if user_count == 0:
            # Create default admin user
            user_id = str(uuid.uuid4())
            username = "admin"
            email = "admin@cashflow.local"
            password = "admin123"
            
            # Hash password
            password_bytes = password.encode('utf-8')
            salt = bcrypt.gensalt()
            password_hash = bcrypt.hashpw(password_bytes, salt).decode('utf-8')
            
            cursor.execute("""
                INSERT INTO users (id, username, email, password_hash, role, is_active, created_at)
                VALUES (?, ?, ?, ?, 'admin', TRUE, ?)
            """, (user_id, username, email, password_hash, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Created default admin user: {username}")
            return password
        
        conn.close()
        return None
        
    except Exception as e:
        logger.error(f"Error creating default admin user: {str(e)}")
        if 'conn' in locals():
            conn.close()
        return None

def init_auth_db():
    """Initialize the authentication database with users table"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create users table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        
        # Create default admin user if needed
        admin_password = create_default_admin_user()
        if admin_password:
            logger.warning(f"Default admin user created with password: {admin_password}")
            
    except Exception as e:
        logger.error(f"Error initializing auth database: {str(e)}")
        if 'conn' in locals():
            conn.close()

def register_user(email: str, password: str, username: Optional[str] = None, role: str = "user") -> Tuple[bool, str]:
    """Register a new user with hashed password"""
    try:
        # Generate username from email if not provided
        if not username:
            username = email.split('@')[0]
        
        # Hash the password
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(password_bytes, salt).decode('utf-8')
        
        # Connect to database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Generate unique ID
        user_id = str(uuid.uuid4())
        
        # Insert new user
        cursor.execute("""
            INSERT INTO users (id, username, email, password_hash, role, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, TRUE, ?)
        """, (user_id, username, email.lower().strip(), password_hash, role, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        logger.info(f"User registered successfully: {email}")
        return True, "User registered successfully!"
        
    except sqlite3.IntegrityError as e:
        if "username" in str(e):
            return False, "Username already exists. Please choose a different username."
        else:
            return False, "Email already exists. Please use a different email."
    except Exception as e:
        logger.error(f"Registration failed for {email}: {str(e)}")
        return False, f"Registration failed: {str(e)}"

def login_user(email_or_username: str, password: str) -> Tuple[bool, Any]:
    """Authenticate user login with email or username"""
    try:
        # Connect to database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get user by email or username
        cursor.execute("""
            SELECT id, username, email, password_hash, role, is_active 
            FROM users 
            WHERE (email = ? OR username = ?) AND is_active = TRUE
        """, (email_or_username.lower().strip(), email_or_username.lower().strip()))
        
        user = cursor.fetchone()
        
        if user is None:
            conn.close()
            logger.warning(f"Login attempt failed - user not found: {email_or_username}")
            return False, "Invalid credentials."
        
        user_id, username, email, stored_hash, role, is_active = user
        
        # Verify password
        password_bytes = password.encode('utf-8')
        if bcrypt.checkpw(password_bytes, stored_hash.encode('utf-8')):
            # Update last login
            cursor.execute(
                "UPDATE users SET last_login = ? WHERE id = ?",
                (datetime.now().isoformat(), user_id)
            )
            conn.commit()
            conn.close()
            
            logger.info(f"User logged in successfully: {email}")
            return True, {
                "id": user_id,
                "username": username,
                "email": email,
                "role": role
            }
        else:
            conn.close()
            logger.warning(f"Login attempt failed - invalid password: {email_or_username}")
            return False, "Invalid credentials."
            
    except Exception as e:
        logger.error(f"Login failed for {email_or_username}: {str(e)}")
        return False, f"Login failed: {str(e)}"

def reset_password(email: str, new_password: str) -> Tuple[bool, str]:
    """Reset user password"""
    try:
        # Hash the new password
        password_bytes = new_password.encode('utf-8')
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(password_bytes, salt).decode('utf-8')
        
        # Connect to database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Update password
        cursor.execute("""
            UPDATE users 
            SET password_hash = ?, updated_at = ?
            WHERE email = ? AND is_active = TRUE
        """, (password_hash, datetime.now().isoformat(), email.lower().strip()))
        
        if cursor.rowcount == 0:
            conn.close()
            return False, "User not found or inactive."
        
        conn.commit()
        conn.close()
        
        logger.info(f"Password reset successfully for: {email}")
        return True, "Password reset successfully!"
        
    except Exception as e:
        logger.error(f"Password reset failed for {email}: {str(e)}")
        return False, f"Password reset failed: {str(e)}"

def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user information by ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, username, email, role, is_active, created_at, last_login
            FROM users 
            WHERE id = ? AND is_active = TRUE
        """, (user_id,))
        
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return {
                "id": user[0],
                "username": user[1],
                "email": user[2],
                "role": user[3],
                "is_active": user[4],
                "created_at": user[5],
                "last_login": user[6]
            }
        
        return None
        
    except Exception as e:
        logger.error(f"Error getting user by ID {user_id}: {str(e)}")
        return None

def is_authenticated():
    """Check if user is authenticated"""
    return "user" in st.session_state and st.session_state["user"] is not None

def logout_user():
    """Clear user session"""
    if "user" in st.session_state:
        del st.session_state["user"]
    st.rerun()

def require_auth():
    """Redirect to login if not authenticated"""
    if not is_authenticated():
        st.switch_page("app.py")
