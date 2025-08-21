"""
Add audit fields and improve data integrity
Adds created_by, updated_by fields and additional constraints
"""

import sqlite3
from datetime import datetime
import os
from src.config.settings import Settings

def get_db_path():
    """Get the database path"""
    return Settings().database.path

def up():
    """Apply the migration"""
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    print("Adding audit fields and constraints...")
    
    # Add audit fields to existing tables where missing
    tables_to_update = [
        'sales_orders',
        'cash_out', 
        'costs',
        'recurring_costs',
        'loan_payments',
        'payment_schedule',
        'integrations'
    ]
    
    for table in tables_to_update:
        try:
            # Add created_by field
            cursor.execute(f'ALTER TABLE {table} ADD COLUMN created_by TEXT')
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            # Add updated_by field
            cursor.execute(f'ALTER TABLE {table} ADD COLUMN updated_by TEXT')
        except sqlite3.OperationalError:
            pass  # Column already exists
    
    # Add additional constraints and indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_costs_category ON costs(category)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_recurring_costs_active ON recurring_costs(is_active)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_payment_schedule_status ON payment_schedule(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_integrations_type ON integrations(integration_type)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_integrations_status ON integrations(status)')
    
    # Create audit log table for tracking changes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_name TEXT NOT NULL,
            record_id TEXT NOT NULL,
            action TEXT NOT NULL,
            old_values TEXT,
            new_values TEXT,
            changed_by TEXT,
            changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_log_table ON audit_log(table_name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_log_record ON audit_log(record_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_log_date ON audit_log(changed_at)')
    
    conn.commit()
    conn.close()
    
    print("✅ Audit fields migration completed successfully")

def down():
    """Rollback the migration"""
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    print("Rolling back audit fields migration...")
    
    # Drop audit log table
    cursor.execute('DROP TABLE IF EXISTS audit_log')
    
    # Note: SQLite doesn't support dropping columns easily
    # In a production environment, you'd recreate tables without the audit fields
    print("⚠️  Note: Audit fields remain in tables (SQLite limitation)")
    
    conn.commit()
    conn.close()
    
    print("✅ Audit fields rollback completed")

if __name__ == '__main__':
    up()
