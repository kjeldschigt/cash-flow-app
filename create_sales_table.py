#!/usr/bin/env python3
"""
Script to create sales_orders table and insert sample data.
"""

import sys
import os
import sqlite3

# Add src directory to path
src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
sys.path.insert(0, src_path)

try:
    from src.container import get_container
    
    # Get database connection
    container = get_container()
    conn = container.get_db_connection()
    
    print("Connected to database successfully")
    
    # Create sales_orders table
    conn.execute('''
    CREATE TABLE IF NOT EXISTS sales_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_date TEXT NOT NULL,
        amount REAL NOT NULL
    )
    ''')
    print("Created sales_orders table")
    
    # Check if data already exists
    cursor = conn.execute('SELECT COUNT(*) FROM sales_orders')
    existing_count = cursor.fetchone()[0]
    
    if existing_count == 0:
        # Insert example data
        sample_data = [
            ('2025-01-01', 500.00),
            ('2025-03-15', 1200.00),
            ('2025-07-10', 800.00),
            ('2025-02-20', 950.00),
            ('2025-05-05', 1500.00)
        ]
        
        conn.executemany('INSERT INTO sales_orders (order_date, amount) VALUES (?, ?)', sample_data)
        conn.commit()
        print(f"Inserted {len(sample_data)} sample records")
    else:
        print(f"Table already contains {existing_count} records, skipping insert")
    
    # Verify the data
    cursor = conn.execute('SELECT COUNT(*) FROM sales_orders')
    count = cursor.fetchone()[0]
    print(f'Sales orders table now has {count} records')
    
    # Show sample of the data
    cursor = conn.execute('SELECT * FROM sales_orders LIMIT 3')
    rows = cursor.fetchall()
    print('Sample records:')
    for row in rows:
        print(f'  ID: {row[0]}, Date: {row[1]}, Amount: ${row[2]:.2f}')
    
    conn.close()
    print("Database operations completed successfully")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
