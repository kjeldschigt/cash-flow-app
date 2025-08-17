import sqlite3
import bcrypt
import streamlit as st
from datetime import datetime
import os

def init_auth_db():
    """Initialize the authentication database with users table"""
    db_path = "users.db"
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create users table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def register_user(email, password):
    """Register a new user with hashed password"""
    try:
        # Hash the password
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(password_bytes, salt)
        
        # Connect to database
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        
        # Insert new user
        cursor.execute(
            "INSERT INTO users (email, password_hash) VALUES (?, ?)",
            (email.lower().strip(), password_hash)
        )
        
        conn.commit()
        conn.close()
        
        return True, "User registered successfully!"
        
    except sqlite3.IntegrityError:
        return False, "Email already exists. Please use a different email."
    except Exception as e:
        return False, f"Registration failed: {str(e)}"

def login_user(email, password):
    """Authenticate user login"""
    try:
        # Connect to database
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        
        # Get user by email
        cursor.execute(
            "SELECT id, email, password_hash FROM users WHERE email = ?",
            (email.lower().strip(),)
        )
        
        user = cursor.fetchone()
        
        if user is None:
            conn.close()
            return False, "Invalid email or password."
        
        user_id, user_email, stored_hash = user
        
        # Verify password
        password_bytes = password.encode('utf-8')
        if bcrypt.checkpw(password_bytes, stored_hash):
            # Update last login
            cursor.execute(
                "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
                (user_id,)
            )
            conn.commit()
            conn.close()
            
            return True, {"id": user_id, "email": user_email}
        else:
            conn.close()
            return False, "Invalid email or password."
            
    except Exception as e:
        return False, f"Login failed: {str(e)}"

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
