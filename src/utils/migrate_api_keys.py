"""
Utility to run API keys database migration
"""

import os
import sys

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from src.utils.db_init import get_database_connection
import sys

sys.path.append("migrations")
from add_api_keys_table_003 import upgrade


def run_migration():
    """Run the API keys table migration"""
    try:
        conn = get_database_connection()
        upgrade(conn)
        print("✅ API keys table migration completed successfully")
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False


if __name__ == "__main__":
    run_migration()
