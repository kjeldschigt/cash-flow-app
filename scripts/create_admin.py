#!/usr/bin/env python3
"""
Command-line script to create an admin user for the Cash Flow Dashboard.
This script should be run during deployment or initial setup.
"""

import os
import sys
import getpass
import secrets
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from src.utils.admin_setup import create_admin_user, check_admin_exists, generate_secure_password
from src.models.user import UserRole


def main():
    """Main function for admin user creation."""
    print("🔐 Cash Flow Dashboard - Admin User Setup")
    print("=" * 50)
    
    # Check if admin already exists
    if check_admin_exists():
        print("✅ Admin user already exists!")
        response = input("Do you want to create another admin user? (y/N): ").lower()
        if response != 'y':
            print("Exiting...")
            return
    
    print("\nCreating admin user...")
    
    # Get email
    while True:
        email = input("Enter admin email: ").strip()
        if email and "@" in email:
            break
        print("❌ Please enter a valid email address!")
    
    # Password options
    print("\nPassword options:")
    print("1. Generate secure password (recommended)")
    print("2. Set custom password")
    
    while True:
        choice = input("Choose option (1 or 2): ").strip()
        if choice in ['1', '2']:
            break
        print("❌ Please enter 1 or 2!")
    
    if choice == '1':
        # Generate secure password
        password = generate_secure_password()
        print(f"\n🔑 Generated secure password: {password}")
        print("⚠️  IMPORTANT: Save this password securely!")
    else:
        # Custom password
        while True:
            password = getpass.getpass("Enter password: ")
            if len(password) < 8:
                print("❌ Password must be at least 8 characters long!")
                continue
            
            confirm = getpass.getpass("Confirm password: ")
            if password != confirm:
                print("❌ Passwords do not match!")
                continue
            
            break
    
    # Create the admin user
    print("\nCreating admin user...")
    success, message = create_admin_user(email, password)
    
    if success:
        print(f"✅ {message}")
        print("\n🎉 Admin user created successfully!")
        print(f"📧 Email: {email}")
        if choice == '1':
            print(f"🔑 Password: {password}")
        print("\n⚠️  Remember to:")
        print("   - Save your credentials securely")
        print("   - Change the password after first login")
        print("   - Enable additional security measures")
    else:
        print(f"❌ Failed to create admin user: {message}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
