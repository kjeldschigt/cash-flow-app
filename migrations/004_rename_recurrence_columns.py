"""
Migration script to rename 'recurrence' columns to 'recurrence_pattern' in the database.
"""

def upgrade(conn):
    cursor = conn.cursor()
    
    # Rename column in recurring_costs table if it exists
    cursor.execute("PRAGMA table_info(recurring_costs)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'recurrence' in columns and 'recurrence_pattern' not in columns:
        cursor.execute('''
            ALTER TABLE recurring_costs 
            RENAME COLUMN recurrence TO recurrence_pattern
        ''')
    
    # Rename column in payment_schedule table if it exists
    cursor.execute("PRAGMA table_info(payment_schedule)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'recurrence' in columns and 'recurrence_pattern' not in columns:
        cursor.execute('''
            ALTER TABLE payment_schedule 
            RENAME COLUMN recurrence TO recurrence_pattern
        ''')
    
    conn.commit()

def downgrade(conn):
    cursor = conn.cursor()
    
    # Rename column back in recurring_costs table if needed
    cursor.execute("PRAGMA table_info(recurring_costs)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'recurrence_pattern' in columns and 'recurrence' not in columns:
        cursor.execute('''
            ALTER TABLE recurring_costs 
            RENAME COLUMN recurrence_pattern TO recurrence
        ''')
    
    # Rename column back in payment_schedule table if needed
    cursor.execute("PRAGMA table_info(payment_schedule)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'recurrence_pattern' in columns and 'recurrence' not in columns:
        cursor.execute('''
            ALTER TABLE payment_schedule 
            RENAME COLUMN recurrence_pattern TO recurrence
        ''')
    
    conn.commit()
