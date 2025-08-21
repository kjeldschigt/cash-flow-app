#!/usr/bin/env python3
"""
Migration script to add missing columns to users table.
"""

import sqlite3
import os
from src.config.settings import Settings

def migrate_users_table():
    """Add missing columns to users table."""
    db_path = Settings().database.path
    
    if not os.path.exists(db_path):
        print("❌ Database file does not exist")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("Adding missing columns to users table...")
        
        # Add username column
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN username TEXT")
            print("✅ Added username column")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("✅ Username column already exists")
            else:
                raise
        
        # Add role column
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
            print("✅ Added role column")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("✅ Role column already exists")
            else:
                raise
        
        # Add is_active column
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1")
            print("✅ Added is_active column")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("✅ is_active column already exists")
            else:
                raise
        
        # Add last_login column
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN last_login TIMESTAMP")
            print("✅ Added last_login column")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("✅ last_login column already exists")
            else:
                raise
        
        # Update existing users to have usernames (extract from email)
        cursor.execute("UPDATE users SET username = SUBSTR(email, 1, INSTR(email, '@') - 1) WHERE username IS NULL")
        updated_rows = cursor.rowcount
        if updated_rows > 0:
            print(f"✅ Updated {updated_rows} users with usernames")
        
        # Update existing users to have admin role if email contains admin
        cursor.execute("UPDATE users SET role = 'admin' WHERE email LIKE '%admin%' AND role = 'user'")
        admin_rows = cursor.rowcount
        if admin_rows > 0:
            print(f"✅ Updated {admin_rows} users to admin role")
        
        conn.commit()
        print("✅ Migration completed successfully")
        
        # Show updated table structure
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        print("\nUpdated table structure:")
        for col in columns:
            print(f"  {col[1]} ({col[2]})")
        
        # Show sample data
        cursor.execute("SELECT id, email, username, role, is_active FROM users LIMIT 3")
        users = cursor.fetchall()
        print("\nSample users:")
        for user in users:
            print(f"  ID: {user[0]}, Email: {user[1]}, Username: {user[2]}, Role: {user[3]}, Active: {user[4]}")
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_users_table()
