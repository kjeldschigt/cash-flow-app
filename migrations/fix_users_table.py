"""
Database migration to fix users table schema and add default data.
"""

import sqlite3
import logging
from datetime import datetime
from typing import Optional
import bcrypt
import uuid

logger = logging.getLogger(__name__)

def check_table_exists(cursor: sqlite3.Cursor, table_name: str) -> bool:
    """Check if a table exists in the database."""
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name=?
    """, (table_name,))
    return cursor.fetchone() is not None

def check_column_exists(cursor: sqlite3.Cursor, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns

def create_users_table(cursor: sqlite3.Cursor) -> None:
    """Create users table with proper schema."""
    cursor.execute("""
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
    """)
    logger.info("Created users table")

def add_missing_columns(cursor: sqlite3.Cursor) -> None:
    """Add missing columns to existing users table."""
    # Check and add username column if missing
    if not check_column_exists(cursor, 'users', 'username'):
        cursor.execute("ALTER TABLE users ADD COLUMN username TEXT")
        logger.info("Added username column to users table")
    
    # Check and add updated_at column if missing
    if not check_column_exists(cursor, 'users', 'updated_at'):
        cursor.execute("ALTER TABLE users ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        logger.info("Added updated_at column to users table")

def fix_null_usernames(cursor: sqlite3.Cursor) -> None:
    """Fix NULL username values by generating them from email."""
    cursor.execute("""
        UPDATE users 
        SET username = SUBSTR(email, 1, INSTR(email, '@') - 1)
        WHERE username IS NULL AND email IS NOT NULL
    """)
    
    # Handle cases where email might also be NULL or invalid
    cursor.execute("""
        UPDATE users 
        SET username = 'user_' || id
        WHERE username IS NULL
    """)
    
    rows_updated = cursor.rowcount
    if rows_updated > 0:
        logger.info(f"Fixed {rows_updated} NULL username entries")

def create_default_admin_user(cursor: sqlite3.Cursor) -> Optional[str]:
    """Create default admin user if no users exist."""
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    
    if user_count == 0:
        # Generate admin user
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
        
        logger.info(f"Created default admin user: {username}")
        return password
    
    return None

def create_settings_table(cursor: sqlite3.Cursor) -> None:
    """Create settings table if it doesn't exist."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    logger.info("Created settings table")

def add_default_settings(cursor: sqlite3.Cursor) -> None:
    """Add default application settings."""
    default_settings = [
        ('theme', 'light', 'Application theme (light/dark)'),
        ('currency', 'USD', 'Default currency'),
        ('date_format', '%Y-%m-%d', 'Default date format'),
        ('decimal_places', '2', 'Number of decimal places for currency'),
        ('session_timeout', '3600', 'Session timeout in seconds'),
        ('password_min_length', '8', 'Minimum password length'),
        ('enable_2fa', 'false', 'Enable two-factor authentication'),
        ('backup_enabled', 'true', 'Enable automatic backups'),
    ]
    
    for key, value, description in default_settings:
        cursor.execute("""
            INSERT OR IGNORE INTO settings (key, value, description)
            VALUES (?, ?, ?)
        """, (key, value, description))
    
    logger.info("Added default settings")

def run_migration(database_path: str = "cashflow.db") -> dict:
    """
    Run the users table migration.
    
    Returns:
        dict: Migration results including any default admin password
    """
    results = {
        'success': False,
        'admin_password': None,
        'changes_made': [],
        'errors': []
    }
    
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        # Enable foreign keys
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # Check if users table exists
        if not check_table_exists(cursor, 'users'):
            create_users_table(cursor)
            results['changes_made'].append('Created users table')
        else:
            add_missing_columns(cursor)
            results['changes_made'].append('Updated users table schema')
        
        # Fix NULL usernames
        fix_null_usernames(cursor)
        results['changes_made'].append('Fixed NULL username entries')
        
        # Create default admin user if needed
        admin_password = create_default_admin_user(cursor)
        if admin_password:
            results['admin_password'] = admin_password
            results['changes_made'].append('Created default admin user')
        
        # Create settings table
        if not check_table_exists(cursor, 'settings'):
            create_settings_table(cursor)
            add_default_settings(cursor)
            results['changes_made'].append('Created settings table with defaults')
        
        conn.commit()
        results['success'] = True
        
        logger.info("Migration completed successfully")
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        results['errors'].append(str(e))
        if 'conn' in locals():
            conn.rollback()
    
    finally:
        if 'conn' in locals():
            conn.close()
    
    return results

def main():
    """Main function for command line execution"""
    run_migration()

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    main()
    results = run_migration()
    
    if results['success']:
        print("✅ Migration completed successfully!")
        if results['changes_made']:
            print("\nChanges made:")
            for change in results['changes_made']:
                print(f"  - {change}")
        
        if results['admin_password']:
            print(f"\n🔑 Default admin user created:")
            print(f"   Username: admin")
            print(f"   Password: {results['admin_password']}")
            print(f"   ⚠️  Please change this password after first login!")
    else:
        print("❌ Migration failed!")
        if results['errors']:
            print("\nErrors:")
            for error in results['errors']:
                print(f"  - {error}")
