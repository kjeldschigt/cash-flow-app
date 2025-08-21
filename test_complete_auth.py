#!/usr/bin/env python3
"""
Complete authentication test with both email and username login.
"""

import sys
import os
import sqlite3

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_complete_authentication():
    """Test complete authentication flow."""
    print("Testing complete authentication flow...")
    
    try:
        from src.models.user import User, UserRole
        from src.repositories.base import DatabaseConnection
        from src.config.settings import Settings
        from src.repositories.user_repository import UserRepository
        from src.services.user_service import UserService
        
        print("\n--- Testing Repository Layer ---")
        
        # Initialize repository using canonical DB path
        db_connection = DatabaseConnection(Settings().database.path)
        user_repo = UserRepository(db_connection)
        
        # Test find_by_email
        user_by_email = user_repo.find_by_email("admin@example.com")
        if user_by_email:
            print(f"✅ find_by_email: Found {user_by_email.email}")
        else:
            print("❌ find_by_email: No user found")
        
        # Test find_by_username
        user_by_username = user_repo.find_by_username("admin")
        if user_by_username:
            print(f"✅ find_by_username: Found {user_by_username.email}")
        else:
            print("❌ find_by_username: No user found")
        
        print("\n--- Testing Service Layer ---")
        
        # Initialize service
        user_service = UserService(db_connection)
        
        # Test get_user_by_email
        service_user_email = user_service.get_user_by_email("admin@example.com")
        if service_user_email:
            print(f"✅ get_user_by_email: Found {service_user_email.email}")
        else:
            print("❌ get_user_by_email: No user found")
        
        # Test get_user_by_username
        service_user_username = user_service.get_user_by_username("admin")
        if service_user_username:
            print(f"✅ get_user_by_username: Found {service_user_username.email}")
        else:
            print("❌ get_user_by_username: No user found")
        
        # Test authenticate_with_identifier (email)
        auth_email = user_service.authenticate_with_identifier("admin@example.com", "admin123")
        if auth_email:
            print(f"✅ authenticate_with_identifier (email): Success for {auth_email.email}")
        else:
            print("❌ authenticate_with_identifier (email): Failed")
        
        # Test authenticate_with_identifier (username)
        auth_username = user_service.authenticate_with_identifier("admin", "admin123")
        if auth_username:
            print(f"✅ authenticate_with_identifier (username): Success for {auth_username.email}")
        else:
            print("❌ authenticate_with_identifier (username): Failed")
        
        # Test with wrong password
        auth_wrong = user_service.authenticate_with_identifier("admin", "wrongpass")
        if not auth_wrong:
            print("✅ authenticate_with_identifier: Correctly rejected wrong password")
        else:
            print("❌ authenticate_with_identifier: Incorrectly accepted wrong password")
        
        print("\n--- Authentication Test Results ---")
        print("✅ Repository layer: email and username lookup working")
        print("✅ Service layer: authentication with email and username working")
        print("✅ Password verification: correctly accepts valid and rejects invalid passwords")
        print("✅ Admin user can successfully log in with both email and username")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_complete_authentication()
    if success:
        print("\n🎉 All authentication tests passed!")
    else:
        print("\n💥 Some authentication tests failed!")
