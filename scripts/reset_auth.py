#!/usr/bin/env python3
"""
Authentication Reset Script for Cash Flow Dashboard

This script provides utilities to reset user authentication:
- Create new admin user
- Clear existing sessions
- Reset passwords
- Provide new credentials
"""

import os
import sys
import sqlite3
import bcrypt
import uuid
import logging
from datetime import datetime
from typing import Optional, Tuple
import argparse

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.security.auth import get_db_connection, register_user, reset_password
from utils.db_init import initialize_database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def clear_all_sessions():
    """Clear all user sessions (if using session storage)"""
    try:
        # For Streamlit, sessions are handled in memory
        # This would be more relevant for Redis-based sessions
        logger.info("Session clearing completed (Streamlit sessions are memory-based)")
        return True
    except Exception as e:
        logger.error(f"Error clearing sessions: {str(e)}")
        return False

def delete_all_users() -> bool:
    """Delete all users from the database (DANGEROUS - use with caution)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get count before deletion
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        if user_count == 0:
            logger.info("No users found to delete")
            conn.close()
            return True
        
        # Delete all users
        cursor.execute("DELETE FROM users")
        conn.commit()
        conn.close()
        
        logger.info(f"Deleted {user_count} users from database")
        return True
        
    except Exception as e:
        logger.error(f"Error deleting users: {str(e)}")
        return False

def create_admin_user(username: str = "admin", email: str = "admin@cashflow.local", password: str = "admin123") -> Tuple[bool, str]:
    """Create a new admin user with specified credentials"""
    try:
        success, message = register_user(email, password, username, "admin")
        if success:
            logger.info(f"Admin user created successfully: {username}")
        else:
            logger.error(f"Failed to create admin user: {message}")
        return success, message
    except Exception as e:
        logger.error(f"Error creating admin user: {str(e)}")
        return False, str(e)

def reset_user_password(email: str, new_password: str) -> Tuple[bool, str]:
    """Reset password for a specific user"""
    try:
        success, message = reset_password(email, new_password)
        if success:
            logger.info(f"Password reset successfully for: {email}")
        else:
            logger.error(f"Failed to reset password for {email}: {message}")
        return success, message
    except Exception as e:
        logger.error(f"Error resetting password: {str(e)}")
        return False, str(e)

def list_users() -> list:
    """List all users in the database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, username, email, role, is_active, created_at, last_login
            FROM users
            ORDER BY created_at DESC
        """)
        
        users = cursor.fetchall()
        conn.close()
        
        return users
        
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        return []

def deactivate_user(email: str) -> Tuple[bool, str]:
    """Deactivate a user account"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE users 
            SET is_active = FALSE, updated_at = ?
            WHERE email = ?
        """, (datetime.now().isoformat(), email.lower().strip()))
        
        if cursor.rowcount == 0:
            conn.close()
            return False, "User not found"
        
        conn.commit()
        conn.close()
        
        logger.info(f"User deactivated: {email}")
        return True, "User deactivated successfully"
        
    except Exception as e:
        logger.error(f"Error deactivating user: {str(e)}")
        return False, str(e)

def activate_user(email: str) -> Tuple[bool, str]:
    """Activate a user account"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE users 
            SET is_active = TRUE, updated_at = ?
            WHERE email = ?
        """, (datetime.now().isoformat(), email.lower().strip()))
        
        if cursor.rowcount == 0:
            conn.close()
            return False, "User not found"
        
        conn.commit()
        conn.close()
        
        logger.info(f"User activated: {email}")
        return True, "User activated successfully"
        
    except Exception as e:
        logger.error(f"Error activating user: {str(e)}")
        return False, str(e)

def full_auth_reset() -> dict:
    """Perform a complete authentication reset"""
    results = {
        'success': False,
        'actions': [],
        'errors': [],
        'admin_credentials': None
    }
    
    try:
        print("🔄 Starting full authentication reset...")
        
        # 1. Clear sessions
        if clear_all_sessions():
            results['actions'].append("Cleared all sessions")
        
        # 2. Delete all users
        if delete_all_users():
            results['actions'].append("Deleted all existing users")
        else:
            results['errors'].append("Failed to delete users")
        
        # 3. Reinitialize database
        db_results = initialize_database()
        if db_results['success']:
            results['actions'].append("Reinitialized database")
            if db_results['admin_password']:
                results['admin_credentials'] = {
                    'username': 'admin',
                    'password': db_results['admin_password']
                }
        else:
            results['errors'].extend(db_results['errors'])
        
        # 4. Create fresh admin user if not created by initialization
        if not results['admin_credentials']:
            success, message = create_admin_user()
            if success:
                results['actions'].append("Created new admin user")
                results['admin_credentials'] = {
                    'username': 'admin',
                    'password': 'admin123'
                }
            else:
                results['errors'].append(f"Failed to create admin user: {message}")
        
        results['success'] = len(results['errors']) == 0
        
    except Exception as e:
        results['errors'].append(f"Unexpected error: {str(e)}")
        logger.error(f"Full auth reset failed: {str(e)}")
    
    return results

def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description="Cash Flow Dashboard Authentication Reset Tool")
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List users command
    subparsers.add_parser('list', help='List all users')
    
    # Create admin command
    create_parser = subparsers.add_parser('create-admin', help='Create admin user')
    create_parser.add_argument('--username', default='admin', help='Admin username')
    create_parser.add_argument('--email', default='admin@cashflow.local', help='Admin email')
    create_parser.add_argument('--password', default='admin123', help='Admin password')
    
    # Reset password command
    reset_parser = subparsers.add_parser('reset-password', help='Reset user password')
    reset_parser.add_argument('email', help='User email')
    reset_parser.add_argument('password', help='New password')
    
    # Deactivate user command
    deactivate_parser = subparsers.add_parser('deactivate', help='Deactivate user')
    deactivate_parser.add_argument('email', help='User email')
    
    # Activate user command
    activate_parser = subparsers.add_parser('activate', help='Activate user')
    activate_parser.add_argument('email', help='User email')
    
    # Full reset command
    subparsers.add_parser('full-reset', help='Complete authentication reset (DANGEROUS)')
    
    # Clear sessions command
    subparsers.add_parser('clear-sessions', help='Clear all user sessions')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    print(f"🔧 Cash Flow Dashboard - Authentication Reset Tool")
    print(f"Command: {args.command}")
    print("-" * 50)
    
    if args.command == 'list':
        users = list_users()
        if users:
            print(f"Found {len(users)} users:")
            print(f"{'ID':<36} {'Username':<15} {'Email':<25} {'Role':<10} {'Active':<8} {'Created'}")
            print("-" * 110)
            for user in users:
                user_id, username, email, role, is_active, created_at, last_login = user
                active_str = "✅" if is_active else "❌"
                created_str = created_at[:19] if created_at else "N/A"
                print(f"{user_id:<36} {username or 'N/A':<15} {email:<25} {role:<10} {active_str:<8} {created_str}")
        else:
            print("No users found.")
    
    elif args.command == 'create-admin':
        success, message = create_admin_user(args.username, args.email, args.password)
        if success:
            print(f"✅ {message}")
            print(f"🔑 Admin Credentials:")
            print(f"   Username: {args.username}")
            print(f"   Email: {args.email}")
            print(f"   Password: {args.password}")
        else:
            print(f"❌ {message}")
    
    elif args.command == 'reset-password':
        success, message = reset_user_password(args.email, args.password)
        if success:
            print(f"✅ {message}")
            print(f"🔑 New credentials for {args.email}:")
            print(f"   Password: {args.password}")
        else:
            print(f"❌ {message}")
    
    elif args.command == 'deactivate':
        success, message = deactivate_user(args.email)
        print(f"{'✅' if success else '❌'} {message}")
    
    elif args.command == 'activate':
        success, message = activate_user(args.email)
        print(f"{'✅' if success else '❌'} {message}")
    
    elif args.command == 'clear-sessions':
        if clear_all_sessions():
            print("✅ All sessions cleared")
        else:
            print("❌ Failed to clear sessions")
    
    elif args.command == 'full-reset':
        print("⚠️  WARNING: This will delete ALL users and reset authentication!")
        confirm = input("Type 'CONFIRM' to proceed: ")
        
        if confirm == 'CONFIRM':
            results = full_auth_reset()
            
            if results['success']:
                print("✅ Full authentication reset completed!")
                
                if results['actions']:
                    print("\n📋 Actions taken:")
                    for action in results['actions']:
                        print(f"  • {action}")
                
                if results['admin_credentials']:
                    print(f"\n🔑 New Admin Credentials:")
                    print(f"   Username: {results['admin_credentials']['username']}")
                    print(f"   Password: {results['admin_credentials']['password']}")
                    print(f"   ⚠️  Please change this password after first login!")
            else:
                print("❌ Full authentication reset failed!")
                if results['errors']:
                    print("\n🚨 Errors:")
                    for error in results['errors']:
                        print(f"  • {error}")
        else:
            print("❌ Operation cancelled")

if __name__ == "__main__":
    main()
