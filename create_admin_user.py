#!/usr/bin/env python3
"""
Script to create an admin user for testing authentication.
"""

import sys
import os
import sqlite3
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def create_admin_user():
    """Create an admin user in the database."""
    try:
        from src.models.user import User, UserRole
        
        print("Creating admin user...")
        
        # Create admin user
        admin_user = User.create("admin@example.com", "admin123", UserRole.ADMIN, "admin")
        
        # Connect to database
        conn = sqlite3.connect("cash_flow.db")
        cursor = conn.cursor()
        
        # Insert admin user
        cursor.execute("""
            INSERT INTO users (email, password_hash, username, role, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            admin_user.email,
            admin_user.password_hash,
            admin_user.username,
            admin_user.role.value,
            admin_user.is_active,
            admin_user.created_at.isoformat()
        ))
        
        conn.commit()
        user_id = cursor.lastrowid
        
        print(f"✅ Created admin user with ID: {user_id}")
        print(f"   Email: {admin_user.email}")
        print(f"   Username: {admin_user.username}")
        print(f"   Role: {admin_user.role.value}")
        
        # Verify the user was created
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user_row = cursor.fetchone()
        
        if user_row:
            print("✅ User successfully stored in database")
        else:
            print("❌ Failed to store user in database")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error creating admin user: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    create_admin_user()
