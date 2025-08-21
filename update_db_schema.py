"""
Script to update the database schema to use 'recurrence_pattern' instead of 'recurrence'.
"""
import sqlite3
from pathlib import Path
from src.config.settings import Settings

def update_schema():
    db_path = Path(Settings().database.path)
    if not db_path.exists():
        print("Error: Database file not found at", db_path.absolute())
        return
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # Check if we need to update the recurring_costs table
        cursor.execute("PRAGMA table_info(recurring_costs)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'frequency' in columns and 'recurrence_pattern' not in columns:
            print("Updating recurring_costs table...")
            cursor.execute('''
                ALTER TABLE recurring_costs 
                RENAME COLUMN frequency TO recurrence_pattern
            ''')
            print("✅ Updated recurring_costs table")
        
        # Check if payment_schedule table exists and needs updating
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='payment_schedule'")
        if cursor.fetchone():
            cursor.execute("PRAGMA table_info(payment_schedule)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'recurrence' in columns and 'recurrence_pattern' not in columns:
                print("Updating payment_schedule table...")
                cursor.execute('''
                    ALTER TABLE payment_schedule 
                    RENAME COLUMN recurrence TO recurrence_pattern
                ''')
                print("✅ Updated payment_schedule table")
        
        conn.commit()
        print("\n✅ Database schema update completed successfully!")
        
    except sqlite3.Error as e:
        print(f"\n❌ Error updating database: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    print("Starting database schema update...\n")
    update_schema()
    print("\nDone!")
