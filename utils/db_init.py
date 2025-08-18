"""
Database initialization utilities for the Cash Flow Dashboard application.
"""

import os
import sqlite3
import logging
from datetime import datetime
from typing import Optional, Dict, Any
import streamlit as st

# Import migration functions
import sys
import os
project_root = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, project_root)

from migrations.fix_users_table import run_migration
from services.storage import init_db
from services.auth import init_auth_db, create_default_admin_user

logger = logging.getLogger(__name__)

def check_encryption_key() -> str:
    """
    Check for encryption key in environment variables.
    
    Returns:
        str: The encryption key
        
    Raises:
        ValueError: If key is missing in production
    """
    encryption_key = os.getenv('ENCRYPTION_MASTER_KEY')
    
    if not encryption_key:
        # Check if we're in production
        environment = os.getenv('ENVIRONMENT', 'development').lower()
        
        if environment == 'production':
            raise ValueError(
                "ENCRYPTION_MASTER_KEY environment variable is required in production. "
                "Please set this to a secure 256-bit key."
            )
        else:
            # Development fallback - generate a warning
            encryption_key = "dev-key-change-in-production-" + "0" * 32
            logger.warning(
                "⚠️  Using default encryption key for development. "
                "Set ENCRYPTION_MASTER_KEY environment variable for production!"
            )
            
            # Show warning in Streamlit if available
            if hasattr(st, 'warning'):
                st.warning(
                    "🔑 Development Mode: Using default encryption key. "
                    "Set ENCRYPTION_MASTER_KEY for production!"
                )
    
    return encryption_key

def database_exists(db_path: str = "cashflow.db") -> bool:
    """Check if database file exists and has tables."""
    if not os.path.exists(db_path):
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if main tables exist
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name IN ('users', 'costs', 'sales_orders')
        """)
        tables = cursor.fetchall()
        conn.close()
        
        return len(tables) >= 2  # At least users and one other table
        
    except Exception as e:
        logger.error(f"Error checking database: {str(e)}")
        return False

def create_database_schema(db_path: str = "cashflow.db") -> bool:
    """Create database schema with all required tables."""
    try:
        # Initialize main database tables
        init_db()
        
        # Initialize authentication tables
        init_auth_db()
        
        logger.info("Database schema created successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error creating database schema: {str(e)}")
        return False

def run_database_migrations(db_path: str = "cashflow.db") -> Dict[str, Any]:
    """Run database migrations to fix schema issues."""
    try:
        logger.info("Running database migrations...")
        results = run_migration(db_path)
        
        if results['success']:
            logger.info("Database migrations completed successfully")
            if results['changes_made']:
                for change in results['changes_made']:
                    logger.info(f"  - {change}")
        else:
            logger.error("Database migrations failed")
            for error in results.get('errors', []):
                logger.error(f"  - {error}")
        
        return results
        
    except Exception as e:
        logger.error(f"Error running migrations: {str(e)}")
        return {
            'success': False,
            'errors': [str(e)],
            'changes_made': [],
            'admin_password': None
        }

def ensure_default_admin_user() -> Optional[str]:
    """Ensure default admin user exists, create if needed."""
    try:
        admin_password = create_default_admin_user()
        if admin_password:
            logger.warning(f"Default admin user created with password: {admin_password}")
            return admin_password
        return None
        
    except Exception as e:
        logger.error(f"Error ensuring default admin user: {str(e)}")
        return None

def initialize_database(force_recreate: bool = False) -> Dict[str, Any]:
    """
    Initialize database with proper schema and default data.
    
    Args:
        force_recreate: If True, recreate database even if it exists
        
    Returns:
        dict: Initialization results
    """
    results = {
        'success': False,
        'database_created': False,
        'migrations_run': False,
        'admin_password': None,
        'messages': [],
        'errors': []
    }
    
    try:
        # Check encryption key first
        encryption_key = check_encryption_key()
        results['messages'].append("Encryption key validated")
        
        db_path = "cashflow.db"
        
        # Check if database exists
        db_exists = database_exists(db_path)
        
        if force_recreate or not db_exists:
            if force_recreate and os.path.exists(db_path):
                # Backup existing database
                backup_path = f"cashflow_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                os.rename(db_path, backup_path)
                results['messages'].append(f"Existing database backed up to {backup_path}")
            
            # Create new database schema
            if create_database_schema(db_path):
                results['database_created'] = True
                results['messages'].append("Database schema created")
            else:
                results['errors'].append("Failed to create database schema")
                return results
        
        # Run migrations to ensure schema is up to date
        migration_results = run_database_migrations(db_path)
        results['migrations_run'] = migration_results['success']
        
        if migration_results['success']:
            results['messages'].extend([f"Migration: {change}" for change in migration_results['changes_made']])
            if migration_results['admin_password']:
                results['admin_password'] = migration_results['admin_password']
        else:
            results['errors'].extend(migration_results['errors'])
        
        # Ensure default admin user exists
        if not results['admin_password']:
            admin_password = ensure_default_admin_user()
            if admin_password:
                results['admin_password'] = admin_password
                results['messages'].append("Default admin user ensured")
        
        results['success'] = True
        logger.info("Database initialization completed successfully")
        
    except ValueError as e:
        # Encryption key error
        results['errors'].append(str(e))
        logger.error(f"Database initialization failed: {str(e)}")
        
    except Exception as e:
        results['errors'].append(f"Unexpected error: {str(e)}")
        logger.error(f"Database initialization failed: {str(e)}")
    
    return results

def get_database_info() -> Dict[str, Any]:
    """Get information about the current database state."""
    info = {
        'exists': False,
        'size': 0,
        'tables': [],
        'user_count': 0,
        'last_modified': None
    }
    
    try:
        db_path = "cashflow.db"
        
        if os.path.exists(db_path):
            info['exists'] = True
            info['size'] = os.path.getsize(db_path)
            info['last_modified'] = datetime.fromtimestamp(os.path.getmtime(db_path))
            
            # Get table information
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            info['tables'] = [row[0] for row in cursor.fetchall()]
            
            # Get user count if users table exists
            if 'users' in info['tables']:
                cursor.execute("SELECT COUNT(*) FROM users")
                info['user_count'] = cursor.fetchone()[0]
            
            conn.close()
            
    except Exception as e:
        logger.error(f"Error getting database info: {str(e)}")
    
    return info

if __name__ == "__main__":
    # Configure logging for standalone execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("🚀 Initializing Cash Flow Dashboard Database...")
    
    results = initialize_database()
    
    if results['success']:
        print("✅ Database initialization completed successfully!")
        
        if results['messages']:
            print("\n📋 Actions taken:")
            for message in results['messages']:
                print(f"  • {message}")
        
        if results['admin_password']:
            print(f"\n🔑 Default Admin Credentials:")
            print(f"   Username: admin")
            print(f"   Password: {results['admin_password']}")
            print(f"   ⚠️  Please change this password after first login!")
        
        # Show database info
        db_info = get_database_info()
        print(f"\n📊 Database Info:")
        print(f"   Size: {db_info['size']:,} bytes")
        print(f"   Tables: {len(db_info['tables'])}")
        print(f"   Users: {db_info['user_count']}")
        
    else:
        print("❌ Database initialization failed!")
        if results['errors']:
            print("\n🚨 Errors:")
            for error in results['errors']:
                print(f"  • {error}")
