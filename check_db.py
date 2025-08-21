"""Script to check database content and schema."""
import sqlite3
from src.config.settings import Settings

def check_database():
    try:
        db_path = Settings().database.path
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # List all tables
        print("\nTables in the database:")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        for table in tables:
            print(f"\nTable: {table[0]}")
            print("Columns:")
            cursor.execute(f"PRAGMA table_info({table[0]})")
            for col in cursor.fetchall():
                print(f"  {col[1]} ({col[2]})")
                
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("Checking database structure...")
    check_database()
