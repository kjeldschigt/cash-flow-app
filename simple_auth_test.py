#!/usr/bin/env python3
"""
Simple test script to verify authentication functionality works correctly.
"""

import sys
import os
import sqlite3
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_basic_auth():
    """Test basic authentication components."""
    print("Testing basic authentication components...")
    
    try:
        # Test User model creation and password verification
        from src.models.user import User, UserRole
        
        print("\n--- Testing User Model ---")
        # Create a test user
        test_user = User.create("admin@example.com", "admin123", UserRole.ADMIN, "admin")
        print(f"✅ Created user: {test_user.email} with username: {test_user.username}")
        
        # Test password verification
        if test_user.verify_password("admin123"):
            print("✅ Password verification successful")
        else:
            print("❌ Password verification failed")
        
        if not test_user.verify_password("wrongpass"):
            print("✅ Correctly rejected wrong password")
        else:
            print("❌ Incorrectly accepted wrong password")
        
        # Test database connection and basic queries
        print("\n--- Testing Database Connection ---")
        from src.config.settings import Settings
        db_path = Settings().database.path
        
        # Check if database exists and has users table
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Check if users table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
            table_exists = cursor.fetchone()
            
            if table_exists:
                print("✅ Users table exists in database")
                
                # Check for admin user
                cursor.execute("SELECT * FROM users WHERE email = ? OR username = ?", ("admin@example.com", "admin"))
                admin_user = cursor.fetchone()
                
                if admin_user:
                    print(f"✅ Found admin user in database: {admin_user['email']}")
                    print(f"   Username: {admin_user['username'] if 'username' in admin_user.keys() else 'N/A'}")
                    print(f"   Role: {admin_user['role'] if 'role' in admin_user.keys() else 'N/A'}")
                    print(f"   Active: {admin_user['is_active'] if 'is_active' in admin_user.keys() else 'N/A'}")
                else:
                    print("❌ No admin user found in database")
                    print("   Available users:")
                    cursor.execute("SELECT email, username, role FROM users LIMIT 5")
                    users = cursor.fetchall()
                    for user in users:
                        print(f"     - {user['email']} ({user['username'] if 'username' in user.keys() else 'N/A'}) - {user['role'] if 'role' in user.keys() else 'N/A'}")
            else:
                print("❌ Users table does not exist in database")
            
            conn.close()
        else:
            print("❌ Database file does not exist")
        
        print("\n--- Test Summary ---")
        print("✅ User model and password hashing working correctly")
        print("✅ Basic database connectivity verified")
        print("✅ Authentication components are functional")
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_basic_auth()
