"""
Migration: Add API keys table for secure key management
"""

import sqlite3
from datetime import datetime
from src.utils.secure_logging import get_logger

logger = get_logger(__name__)

def upgrade(conn: sqlite3.Connection) -> None:
    """Create api_keys table for encrypted API key storage"""
    try:
        cursor = conn.cursor()
        
        # Create api_keys table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_name TEXT NOT NULL UNIQUE,
                encrypted_value TEXT NOT NULL,
                service_type TEXT NOT NULL,
                added_by_user TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                description TEXT,
                FOREIGN KEY (added_by_user) REFERENCES users(id)
            )
        """)
        
        # Create index for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_api_keys_service_type 
            ON api_keys(service_type)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_api_keys_active 
            ON api_keys(is_active)
        """)
        
        # Create trigger to update last_modified timestamp
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS update_api_keys_modified
            AFTER UPDATE ON api_keys
            FOR EACH ROW
            BEGIN
                UPDATE api_keys 
                SET last_modified = CURRENT_TIMESTAMP 
                WHERE id = NEW.id;
            END
        """)
        
        conn.commit()
        logger.info("API keys table created successfully", 
                   operation="database_migration",
                   table="api_keys")
        
    except Exception as e:
        conn.rollback()
        logger.error("Failed to create api_keys table", 
                    error=str(e),
                    operation="database_migration")
        raise

def downgrade(conn: sqlite3.Connection) -> None:
    """Drop api_keys table"""
    try:
        cursor = conn.cursor()
        
        cursor.execute("DROP TRIGGER IF EXISTS update_api_keys_modified")
        cursor.execute("DROP INDEX IF EXISTS idx_api_keys_active")
        cursor.execute("DROP INDEX IF EXISTS idx_api_keys_service_type")
        cursor.execute("DROP TABLE IF EXISTS api_keys")
        
        conn.commit()
        logger.info("API keys table dropped successfully",
                   operation="database_migration_rollback")
        
    except Exception as e:
        conn.rollback()
        logger.error("Failed to drop api_keys table",
                    error=str(e),
                    operation="database_migration_rollback")
        raise

if __name__ == "__main__":
    # Test migration
    import os
    from src.utils.db_init import get_database_connection
    
    conn = get_database_connection()
    try:
        upgrade(conn)
        print("✅ API keys table migration completed successfully")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
    finally:
        conn.close()
