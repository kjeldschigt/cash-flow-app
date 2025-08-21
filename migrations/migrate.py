"""
Database migration runner
Manages database schema migrations for the cash flow application
"""

import os
import sys
import sqlite3
import importlib.util
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from src.config.settings import Settings

def get_db_path():
    """Get the database path"""
    return Settings().database.path

def init_migration_table():
    """Initialize the migrations tracking table"""
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            migration_name TEXT UNIQUE NOT NULL,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def get_applied_migrations():
    """Get list of already applied migrations"""
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT migration_name FROM migrations ORDER BY id')
        applied = [row[0] for row in cursor.fetchall()]
    except sqlite3.OperationalError:
        # Migrations table doesn't exist yet
        applied = []
    
    conn.close()
    return applied

def get_available_migrations():
    """Get list of available migration files"""
    migrations_dir = Path(__file__).parent
    migration_files = []
    
    for file_path in migrations_dir.glob('*.py'):
        if file_path.name.startswith(('00', '01', '02', '03', '04', '05', '06', '07', '08', '09')):
            migration_files.append(file_path.stem)
    
    return sorted(migration_files)

def load_migration_module(migration_name):
    """Load a migration module dynamically"""
    migrations_dir = Path(__file__).parent
    file_path = migrations_dir / f"{migration_name}.py"
    
    spec = importlib.util.spec_from_file_location(migration_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    return module

def record_migration(migration_name):
    """Record that a migration has been applied"""
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    cursor.execute(
        'INSERT INTO migrations (migration_name) VALUES (?)',
        (migration_name,)
    )
    
    conn.commit()
    conn.close()

def remove_migration_record(migration_name):
    """Remove migration record (for rollbacks)"""
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    cursor.execute(
        'DELETE FROM migrations WHERE migration_name = ?',
        (migration_name,)
    )
    
    conn.commit()
    conn.close()

def migrate_up():
    """Run all pending migrations"""
    print("🚀 Starting database migration...")
    
    # Initialize migration tracking
    init_migration_table()
    
    # Get migration status
    applied = get_applied_migrations()
    available = get_available_migrations()
    
    pending = [m for m in available if m not in applied]
    
    if not pending:
        print("✅ No pending migrations. Database is up to date.")
        return
    
    print(f"📋 Found {len(pending)} pending migrations:")
    for migration in pending:
        print(f"   - {migration}")
    
    # Apply each pending migration
    for migration_name in pending:
        print(f"\n🔄 Applying migration: {migration_name}")
        
        try:
            module = load_migration_module(migration_name)
            module.up()
            record_migration(migration_name)
            print(f"✅ Migration {migration_name} applied successfully")
            
        except Exception as e:
            print(f"❌ Error applying migration {migration_name}: {str(e)}")
            print("🛑 Migration stopped. Fix the error and try again.")
            return False
    
    print(f"\n🎉 All migrations completed successfully!")
    return True

def migrate_down(migration_name=None):
    """Rollback migrations"""
    print("🔄 Starting migration rollback...")
    
    applied = get_applied_migrations()
    
    if not applied:
        print("✅ No migrations to rollback.")
        return
    
    if migration_name:
        if migration_name not in applied:
            print(f"❌ Migration {migration_name} is not applied.")
            return
        
        migrations_to_rollback = [migration_name]
    else:
        # Rollback the last migration
        migrations_to_rollback = [applied[-1]]
    
    print(f"📋 Rolling back migrations: {migrations_to_rollback}")
    
    for migration_name in reversed(migrations_to_rollback):
        print(f"\n🔄 Rolling back migration: {migration_name}")
        
        try:
            module = load_migration_module(migration_name)
            if hasattr(module, 'down'):
                module.down()
                remove_migration_record(migration_name)
                print(f"✅ Migration {migration_name} rolled back successfully")
            else:
                print(f"⚠️  Migration {migration_name} has no rollback method")
                
        except Exception as e:
            print(f"❌ Error rolling back migration {migration_name}: {str(e)}")
            return False
    
    print(f"\n🎉 Rollback completed successfully!")
    return True

def migration_status():
    """Show migration status"""
    print("📊 Migration Status:")
    print("=" * 50)
    
    applied = get_applied_migrations()
    available = get_available_migrations()
    
    for migration in available:
        status = "✅ Applied" if migration in applied else "⏳ Pending"
        print(f"{migration:<30} {status}")
    
    pending_count = len([m for m in available if m not in applied])
    print(f"\nTotal: {len(available)} migrations, {pending_count} pending")

def main():
    """Main CLI interface"""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python migrate.py up          - Apply all pending migrations")
        print("  python migrate.py down        - Rollback last migration")
        print("  python migrate.py down <name> - Rollback specific migration")
        print("  python migrate.py status      - Show migration status")
        return
    
    command = sys.argv[1]
    
    if command == "up":
        migrate_up()
    elif command == "down":
        migration_name = sys.argv[2] if len(sys.argv) > 2 else None
        migrate_down(migration_name)
    elif command == "status":
        migration_status()
    else:
        print(f"Unknown command: {command}")

if __name__ == '__main__':
    main()
