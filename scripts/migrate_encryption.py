#!/usr/bin/env python3
"""
Migration script for upgrading encryption from static salt to random salt per operation.
This script should be run once when upgrading to the new encryption system.
"""

import os
import sys
import sqlite3
import logging
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from src.security.encryption import DataEncryption

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def find_database_files():
    """Find all database files that might contain encrypted data."""
    db_files = []
    project_root = Path(__file__).parent.parent
    
    # Common database file patterns
    patterns = ['*.db', '*.sqlite', '*.sqlite3']
    
    for pattern in patterns:
        db_files.extend(project_root.glob(pattern))
        db_files.extend(project_root.glob(f'**/{pattern}'))
    
    return [db for db in db_files if db.exists()]


def get_encrypted_columns():
    """Define which tables and columns contain encrypted data."""
    return {
        'users': ['password_hash'],  # If passwords are encrypted (usually just hashed)
        'api_keys': ['encrypted_key'],
        'settings': ['encrypted_value'],
        'sensitive_data': ['encrypted_content'],
        # Add more tables/columns as needed
    }


def migrate_database_encryption(db_path: Path, encryption: DataEncryption):
    """Migrate encrypted data in a specific database."""
    logger.info(f"Migrating encryption in database: {db_path}")
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Get all tables in the database
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        encrypted_columns = get_encrypted_columns()
        migrated_count = 0
        
        for table in tables:
            if table in encrypted_columns:
                columns = encrypted_columns[table]
                
                # Get table info to verify columns exist
                cursor.execute(f"PRAGMA table_info({table});")
                existing_columns = [row[1] for row in cursor.fetchall()]
                
                for column in columns:
                    if column in existing_columns:
                        logger.info(f"Migrating {table}.{column}")
                        
                        # Get all rows with encrypted data
                        cursor.execute(f"SELECT rowid, {column} FROM {table} WHERE {column} IS NOT NULL AND {column} != '';")
                        rows = cursor.fetchall()
                        
                        for rowid, encrypted_data in rows:
                            try:
                                # Attempt migration
                                migrated_data = encryption.migrate_legacy_encrypted_data(encrypted_data)
                                
                                # Only update if migration actually changed the data
                                if migrated_data != encrypted_data:
                                    cursor.execute(f"UPDATE {table} SET {column} = ? WHERE rowid = ?", 
                                                 (migrated_data, rowid))
                                    migrated_count += 1
                                    
                            except Exception as e:
                                logger.warning(f"Failed to migrate row {rowid} in {table}.{column}: {e}")
        
        conn.commit()
        conn.close()
        
        logger.info(f"Migration completed for {db_path}. Migrated {migrated_count} records.")
        return migrated_count
        
    except Exception as e:
        logger.error(f"Error migrating database {db_path}: {e}")
        return 0


def backup_database(db_path: Path) -> Path:
    """Create a backup of the database before migration."""
    backup_path = db_path.with_suffix(f'{db_path.suffix}.backup')
    
    try:
        import shutil
        shutil.copy2(db_path, backup_path)
        logger.info(f"Created backup: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"Failed to create backup: {e}")
        raise


def main():
    """Main migration function."""
    print("🔐 Cash Flow Dashboard - Encryption Migration")
    print("=" * 50)
    
    # Initialize encryption system
    try:
        encryption = DataEncryption()
        logger.info("Encryption system initialized")
    except Exception as e:
        logger.error(f"Failed to initialize encryption: {e}")
        sys.exit(1)
    
    # Find database files
    db_files = find_database_files()
    
    if not db_files:
        logger.info("No database files found. Migration not needed.")
        return
    
    print(f"Found {len(db_files)} database file(s):")
    for db in db_files:
        print(f"  - {db}")
    
    # Confirm migration
    response = input("\nProceed with encryption migration? (y/N): ").lower()
    if response != 'y':
        print("Migration cancelled.")
        return
    
    total_migrated = 0
    
    for db_path in db_files:
        try:
            # Create backup
            backup_path = backup_database(db_path)
            
            # Perform migration
            migrated_count = migrate_database_encryption(db_path, encryption)
            total_migrated += migrated_count
            
            print(f"✅ Migrated {migrated_count} records in {db_path.name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to migrate {db_path}: {e}")
            continue
    
    print(f"\n🎉 Migration completed!")
    print(f"Total records migrated: {total_migrated}")
    print("\n⚠️  Important:")
    print("1. Test your application thoroughly")
    print("2. Keep database backups until you're sure everything works")
    print("3. The old static salt method is no longer supported")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nMigration cancelled by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)
