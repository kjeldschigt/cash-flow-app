import sqlite3
import pandas as pd
import streamlit as st
import os

def init_db():
    """Initialize SQLite database with required tables"""
    conn = sqlite3.connect('cashflow.db')
    cur = conn.cursor()
    
    # Create tables if they don't exist
    cur.execute('''CREATE TABLE IF NOT EXISTS sales_orders 
                   (date TEXT, sales_usd REAL)''')
    
    cur.execute('''CREATE TABLE IF NOT EXISTS cash_out 
                   (date TEXT, costs_usd REAL, costs_crc REAL)''')
    
    cur.execute('''CREATE TABLE IF NOT EXISTS fx_rates 
                   (month TEXT, low REAL, base REAL, high REAL)''')
    
    cur.execute('''CREATE TABLE IF NOT EXISTS loan_payments 
                   (date TEXT, amount REAL, type TEXT)''')
    
    cur.execute('''CREATE TABLE IF NOT EXISTS costs_monthly 
                   (month TEXT, category TEXT, amount REAL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    conn.commit()
    conn.close()

def load_table(table_name):
    """Load data from specified table"""
    conn = sqlite3.connect('cashflow.db')
    try:
        df = pd.read_sql(f'SELECT * FROM {table_name}', conn)
        conn.close()
        return df
    except Exception as e:
        conn.close()
        return pd.DataFrame()

def upsert_from_csv(table_name, csv_path):
    """Load CSV data into database table"""
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        conn = sqlite3.connect('cashflow.db')
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        conn.close()
        return True
    return False

def _check_and_populate_tables():
    """Check if tables are empty and populate from CSV files if needed"""
    # Check if sales_orders table is empty
    sales_df = load_table('sales_orders')
    if sales_df.empty:
        upsert_from_csv('sales_orders', 'data/sample_sales_orders.csv')
    
    # Check if cash_out table is empty
    costs_df = load_table('cash_out')
    if costs_df.empty:
        upsert_from_csv('cash_out', 'data/sample_cash_out.csv')
    
    # Check if fx_rates table is empty
    fx_df = load_table('fx_rates')
    if fx_df.empty:
        upsert_from_csv('fx_rates', 'data/sample_fx_rates.csv')

# Initialize database on first import
if not os.path.exists('cashflow.db'):
    init_db()
    _check_and_populate_tables()

def load_sales_data():
    """Load sales orders from database"""
    df = load_table('sales_orders')
    if not df.empty and 'date' in df.columns:
        df['Date'] = pd.to_datetime(df['date'])
        df['Sales_USD'] = df['sales_usd']
        df = df[['Date', 'Sales_USD']]
    else:
        # Fallback to hardcoded data
        data = {
            'Date': ['2025-01-01', '2025-02-01', '2025-03-01'],
            'Sales_USD': [12500, 14200, 10800]
        }
        df = pd.DataFrame(data)
        df['Date'] = pd.to_datetime(df['Date'])
    return df

def load_costs_data():
    """Load cost data from database"""
    df = load_table('cash_out')
    if not df.empty and 'date' in df.columns:
        df['Date'] = pd.to_datetime(df['date'])
        df['Costs_USD'] = df['costs_usd']
        df['Costs_CRC'] = df['costs_crc']
        df = df[['Date', 'Costs_USD', 'Costs_CRC']]
    else:
        # Fallback to hardcoded data
        data = {
            'Date': ['2025-01-01', '2025-02-01', '2025-03-01'],
            'Costs_USD': [6200, 7500, 5400],
            'Costs_CRC': [3000000, 3500000, 4000000]
        }
        df = pd.DataFrame(data)
        df['Date'] = pd.to_datetime(df['Date'])
    return df

def load_fx_rates():
    """Load FX rates from database"""
    df = load_table('fx_rates')
    if not df.empty and 'month' in df.columns:
        df['Month'] = df['month']
        df['Low_CRC_USD'] = df['low']
        df['Base_CRC_USD'] = df['base']
        df['High_CRC_USD'] = df['high']
        df = df[['Month', 'Low_CRC_USD', 'Base_CRC_USD', 'High_CRC_USD']]
    else:
        # Fallback to hardcoded data
        data = {
            'Month': ['2025-01', '2025-02', '2025-03'],
            'Low_CRC_USD': [500, 505, 510],
            'Base_CRC_USD': [520, 525, 530],
            'High_CRC_USD': [550, 555, 560]
        }
        df = pd.DataFrame(data)
    return df

def insert_monthly_cost(month, category, amount):
    """Insert monthly cost data into costs_monthly table"""
    with sqlite3.connect('cashflow.db') as conn:
        cur = conn.cursor()
        cur.execute('INSERT INTO costs_monthly (month, category, amount) VALUES (?, ?, ?)', 
                    (month, category, amount))
        conn.commit()

def save_settings_to_db(settings_dict):
    """Save settings dictionary to database"""
    with sqlite3.connect('cashflow.db') as conn:
        cur = conn.cursor()
        cur.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
        # Batch insert all settings
        settings_data = [(k, str(v)) for k, v in settings_dict.items()]
        cur.executemany('INSERT OR REPLACE INTO settings VALUES (?, ?)', settings_data)
        conn.commit()

def load_settings():
    """Load settings from database"""
    with sqlite3.connect('cashflow.db') as conn:
        cur = conn.cursor()
        cur.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
        result = dict(cur.execute('SELECT * FROM settings').fetchall())
    return result

def get_combined_data():
    """Get combined sales and costs data"""
    sales_df = load_sales_data()
    costs_df = load_costs_data()
    
    # Merge on Date
    combined = pd.merge(sales_df, costs_df, on='Date', how='outer')
    return combined
