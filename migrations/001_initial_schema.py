"""
Initial database schema migration
Creates all core tables for the cash flow application
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
    
    print("Creating initial database schema...")
    
    # Users table for authentication
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Settings table for application configuration
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Sales orders table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales_orders (
            id TEXT PRIMARY KEY,
            customer_name TEXT,
            product TEXT,
            amount REAL,
            currency TEXT DEFAULT 'USD',
            order_date DATE,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Cash out transactions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cash_out (
            id TEXT PRIMARY KEY,
            description TEXT,
            amount REAL,
            currency TEXT DEFAULT 'USD',
            category TEXT,
            transaction_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Foreign exchange rates table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fx_rates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_currency TEXT,
            to_currency TEXT,
            rate REAL,
            rate_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(from_currency, to_currency, rate_date)
        )
    ''')
    
    # Costs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS costs (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT,
            amount REAL NOT NULL,
            currency TEXT DEFAULT 'USD',
            cost_date DATE,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Recurring costs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recurring_costs (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT,
            amount REAL NOT NULL,
            currency TEXT DEFAULT 'USD',
            frequency TEXT DEFAULT 'monthly',
            start_date DATE,
            end_date DATE,
            description TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Monthly costs summary table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS costs_monthly (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            month TEXT,
            category TEXT,
            total_amount REAL,
            currency TEXT DEFAULT 'USD',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Loan payments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS loan_payments (
            id TEXT PRIMARY KEY,
            loan_name TEXT,
            principal REAL,
            interest REAL,
            total_payment REAL,
            currency TEXT DEFAULT 'USD',
            due_date DATE,
            status TEXT DEFAULT 'scheduled',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Payment schedule table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payment_schedule (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT,
            currency TEXT DEFAULT 'USD',
            amount_expected REAL NOT NULL,
            amount_actual REAL,
            comment TEXT,
            recurrence TEXT,
            due_date DATE,
            status TEXT DEFAULT 'scheduled',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Integrations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS integrations (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            integration_type TEXT NOT NULL,
            status TEXT DEFAULT 'inactive',
            config TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create indexes for better performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sales_orders_date ON sales_orders(order_date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_cash_out_date ON cash_out(transaction_date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_costs_date ON costs(cost_date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_payment_schedule_due_date ON payment_schedule(due_date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_fx_rates_date ON fx_rates(rate_date)')
    
    conn.commit()
    conn.close()
    
    print("✅ Initial schema migration completed successfully")

def down():
    """Rollback the migration"""
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    print("Rolling back initial schema migration...")
    
    # Drop tables in reverse order
    tables = [
        'integrations',
        'payment_schedule', 
        'loan_payments',
        'costs_monthly',
        'recurring_costs',
        'costs',
        'fx_rates',
        'cash_out',
        'sales_orders',
        'settings',
        'users'
    ]
    
    for table in tables:
        cursor.execute(f'DROP TABLE IF EXISTS {table}')
    
    conn.commit()
    conn.close()
    
    print("✅ Initial schema rollback completed")

if __name__ == '__main__':
    up()
