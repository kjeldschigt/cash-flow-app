#!/usr/bin/env python3
"""
Test script to verify authentication functionality works correctly.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.repositories.base import DatabaseConnection
from src.services.user_service import UserService
from src.security.auth import AuthManager
from src.config.settings import Settings
from src.models.user import User, UserRole

def test_authentication():
    """Test authentication functionality."""
    print("Testing authentication system...")
    
    try:
        # Initialize services
        db_connection = DatabaseConnection("cash_flow.db")
        user_service = UserService(db_connection)
        settings = Settings()
        auth_manager = AuthManager(user_service, settings)
        
        # Test cases
        test_cases = [
            ("admin@example.com", "admin123", "Admin email login"),
            ("admin", "admin123", "Admin username login"),
            ("invalid@example.com", "wrongpass", "Invalid credentials"),
            ("admin@example.com", "wrongpass", "Wrong password"),
        ]
        
        for identifier, password, description in test_cases:
            print(f"\n--- {description} ---")
            print(f"Trying to authenticate: {identifier}")
            
            user = auth_manager.authenticate_user(identifier, password)
            
            if user:
                print(f"✅ SUCCESS: Authenticated as {user.email} (Role: {user.role.value})")
                print(f"   Username: {user.username}")
                print(f"   User ID: {user.id}")
            else:
                print(f"❌ FAILED: Authentication failed for {identifier}")
        
        # Test individual service methods
        print(f"\n--- Testing UserService methods ---")
        
        # Test get_user_by_email
        user_by_email = user_service.get_user_by_email("admin@example.com")
        if user_by_email:
            print(f"✅ get_user_by_email: Found user {user_by_email.email}")
        else:
            print("❌ get_user_by_email: No user found")
        
        # Test get_user_by_username
        user_by_username = user_service.get_user_by_username("admin")
        if user_by_username:
            print(f"✅ get_user_by_username: Found user {user_by_username.email}")
        else:
            print("❌ get_user_by_username: No user found")
        
        # Test authenticate_with_identifier
        auth_result = user_service.authenticate_with_identifier("admin@example.com", "admin123")
        if auth_result:
            print(f"✅ authenticate_with_identifier: Success for {auth_result.email}")
        else:
            print("❌ authenticate_with_identifier: Failed")
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_authentication()
