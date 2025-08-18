"""
Integration tests for database operations and data integrity
"""

import pytest
import sqlite3
import sys
import os
from datetime import datetime, date
from decimal import Decimal
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from src.services.storage_service import (
    init_db, get_db_connection, add_cost, get_costs, update_cost, delete_cost,
    add_sales_order, get_sales_orders, get_payment_schedule, add_payment_schedule
)
from models.cost import Cost

@pytest.mark.integration
class TestDatabaseIntegration:
    """Test database operations and data integrity"""
    
    @pytest.fixture
    def clean_test_db(self, tmp_path):
        """Create a clean test database"""
        db_path = tmp_path / "test_cash_flow.db"
        
        # Temporarily override the database path
        original_db_path = os.environ.get('DATABASE_PATH')
        os.environ['DATABASE_PATH'] = str(db_path)
        
        # Initialize the database
        init_db()
        
        yield str(db_path)
        
        # Restore original database path
        if original_db_path:
            os.environ['DATABASE_PATH'] = original_db_path
        else:
            os.environ.pop('DATABASE_PATH', None)
    
    def test_database_initialization(self, clean_test_db):
        """Test database initialization creates all required tables"""
        conn = sqlite3.connect(clean_test_db)
        cursor = conn.cursor()
        
        # Check that all required tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = [
            'costs', 'recurring_costs', 'sales_orders', 'cash_out',
            'fx_rates', 'loan_payments', 'costs_monthly', 'payment_schedule'
        ]
        
        for table in expected_tables:
            assert table in tables, f"Table {table} not found in database"
        
        conn.close()
    
    def test_cost_crud_operations(self, clean_test_db):
        """Test complete CRUD operations for costs"""
        # Create
        cost_data = {
            'date': date(2024, 8, 17),
            'amount': Decimal('100.50'),
            'category': 'Operating',
            'subcategory': 'Office Supplies',
            'description': 'Test cost',
            'currency': 'USD'
        }
        
        add_cost(cost_data)
        
        # Read
        costs_df = get_costs()
        assert len(costs_df) == 1
        assert costs_df.iloc[0]['amount'] == 100.50
        assert costs_df.iloc[0]['category'] == 'Operating'
        
        # Update
        cost_id = costs_df.iloc[0]['id']
        update_cost(cost_id, amount=150.75, description='Updated cost')
        
        updated_costs_df = get_costs()
        assert updated_costs_df.iloc[0]['amount'] == 150.75
        assert updated_costs_df.iloc[0]['description'] == 'Updated cost'
        
        # Delete
        delete_cost(cost_id)
        
        final_costs_df = get_costs()
        assert len(final_costs_df) == 0
    
    def test_sales_order_operations(self, clean_test_db):
        """Test sales order database operations"""
        sales_order_data = {
            'date': date(2024, 8, 17),
            'amount': Decimal('500.00'),
            'customer': 'Test Customer',
            'status': 'completed',
            'currency': 'USD'
        }
        
        add_sales_order(sales_order_data)
        
        sales_orders_df = get_sales_orders()
        assert len(sales_orders_df) == 1
        assert sales_orders_df.iloc[0]['amount'] == 500.00
        assert sales_orders_df.iloc[0]['customer'] == 'Test Customer'
    
    def test_payment_schedule_operations(self, clean_test_db):
        """Test payment schedule database operations"""
        payment_data = {
            'id': 'pay_123',
            'name': 'Monthly Rent',
            'category': 'Operating',
            'currency': 'USD',
            'amount_expected': Decimal('2000.00'),
            'amount_actual': None,
            'comment': 'Office rent payment',
            'recurrence_pattern': 'monthly',
            'due_date': date(2024, 9, 1),
            'status': 'scheduled'
        }
        
        add_payment_schedule(payment_data)
        
        schedule_df = get_payment_schedule()
        assert len(schedule_df) == 1
        assert schedule_df.iloc[0]['name'] == 'Monthly Rent'
        assert schedule_df.iloc[0]['amount_expected'] == 2000.00
    
    def test_data_integrity_constraints(self, clean_test_db):
        """Test database constraints and data integrity"""
        # Test unique constraint on cost ID
        cost_data = {
            'id': 'cost_123',
            'date': date(2024, 8, 17),
            'amount': Decimal('100.00'),
            'category': 'Operating',
            'currency': 'USD'
        }
        
        add_cost(cost_data)
        
        # Adding same ID should handle gracefully
        with pytest.raises(Exception):
            add_cost(cost_data)
    
    def test_foreign_key_relationships(self, clean_test_db):
        """Test foreign key relationships between tables"""
        # This would test relationships if we had them defined
        # For now, we'll test data consistency
        
        # Add a cost
        cost_data = {
            'date': date(2024, 8, 17),
            'amount': Decimal('100.00'),
            'category': 'Operating',
            'currency': 'USD'
        }
        add_cost(cost_data)
        
        # Add related sales order
        sales_data = {
            'date': date(2024, 8, 17),
            'amount': Decimal('500.00'),
            'customer': 'Test Customer',
            'status': 'completed',
            'currency': 'USD'
        }
        add_sales_order(sales_data)
        
        # Verify both records exist
        costs_df = get_costs()
        sales_df = get_sales_orders()
        
        assert len(costs_df) == 1
        assert len(sales_df) == 1
    
    def test_transaction_rollback(self, clean_test_db):
        """Test transaction rollback on error"""
        conn = get_db_connection()
        
        try:
            cursor = conn.cursor()
            cursor.execute("BEGIN TRANSACTION")
            
            # Insert valid data
            cursor.execute("""
                INSERT INTO costs (date, amount, category, currency)
                VALUES (?, ?, ?, ?)
            """, (date(2024, 8, 17), 100.00, 'Operating', 'USD'))
            
            # Insert invalid data (this should fail)
            cursor.execute("""
                INSERT INTO costs (date, amount, category, currency)
                VALUES (?, ?, ?, ?)
            """, (None, None, None, None))  # Invalid data
            
            conn.commit()
            
        except Exception:
            conn.rollback()
        finally:
            conn.close()
        
        # Verify no data was inserted due to rollback
        costs_df = get_costs()
        assert len(costs_df) == 0
    
    def test_concurrent_access(self, clean_test_db):
        """Test concurrent database access"""
        import threading
        import time
        
        def add_costs_worker(worker_id):
            for i in range(10):
                cost_data = {
                    'date': date(2024, 8, 17),
                    'amount': Decimal(f'{worker_id * 10 + i}.00'),
                    'category': f'Category_{worker_id}',
                    'currency': 'USD'
                }
                add_cost(cost_data)
                time.sleep(0.01)  # Small delay to simulate real usage
        
        # Create multiple threads
        threads = []
        for worker_id in range(3):
            thread = threading.Thread(target=add_costs_worker, args=(worker_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all costs were added
        costs_df = get_costs()
        assert len(costs_df) == 30  # 3 workers * 10 costs each
    
    def test_data_migration_compatibility(self, clean_test_db):
        """Test data migration and schema compatibility"""
        # Add data with current schema
        cost_data = {
            'date': date(2024, 8, 17),
            'amount': Decimal('100.00'),
            'category': 'Operating',
            'currency': 'USD'
        }
        add_cost(cost_data)
        
        # Simulate schema migration by adding a new column
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("ALTER TABLE costs ADD COLUMN tags TEXT")
            conn.commit()
        except sqlite3.OperationalError:
            # Column might already exist
            pass
        
        conn.close()
        
        # Verify data is still accessible
        costs_df = get_costs()
        assert len(costs_df) == 1
        assert costs_df.iloc[0]['amount'] == 100.00
    
    def test_bulk_operations_performance(self, clean_test_db, performance_monitor):
        """Test performance of bulk database operations"""
        # Prepare bulk data
        bulk_costs = []
        for i in range(1000):
            cost_data = {
                'date': date(2024, 8, 17),
                'amount': Decimal(f'{100 + i}.00'),
                'category': f'Category_{i % 10}',
                'currency': 'USD'
            }
            bulk_costs.append(cost_data)
        
        performance_monitor.start()
        
        # Bulk insert
        for cost_data in bulk_costs:
            add_cost(cost_data)
        
        performance_monitor.assert_max_duration(5.0)
        
        # Verify all data was inserted
        costs_df = get_costs()
        assert len(costs_df) == 1000
    
    def test_data_validation_at_db_level(self, clean_test_db):
        """Test data validation at database level"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Test invalid date format
        with pytest.raises(Exception):
            cursor.execute("""
                INSERT INTO costs (date, amount, category, currency)
                VALUES (?, ?, ?, ?)
            """, ('invalid-date', 100.00, 'Operating', 'USD'))
        
        # Test negative amount (if we had constraints)
        # This would require adding CHECK constraints to the schema
        
        conn.close()
    
    def test_database_backup_and_restore(self, clean_test_db, tmp_path):
        """Test database backup and restore functionality"""
        # Add some data
        cost_data = {
            'date': date(2024, 8, 17),
            'amount': Decimal('100.00'),
            'category': 'Operating',
            'currency': 'USD'
        }
        add_cost(cost_data)
        
        # Create backup
        backup_path = tmp_path / "backup.db"
        
        source_conn = sqlite3.connect(clean_test_db)
        backup_conn = sqlite3.connect(str(backup_path))
        
        source_conn.backup(backup_conn)
        
        source_conn.close()
        backup_conn.close()
        
        # Verify backup contains data
        backup_conn = sqlite3.connect(str(backup_path))
        cursor = backup_conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM costs")
        count = cursor.fetchone()[0]
        
        assert count == 1
        backup_conn.close()

@pytest.mark.integration
class TestDatabasePerformance:
    """Test database performance characteristics"""
    
    @pytest.fixture
    def populated_test_db(self, clean_test_db):
        """Create a test database with sample data"""
        # Add sample costs
        for i in range(100):
            cost_data = {
                'date': date(2024, 8, 17),
                'amount': Decimal(f'{100 + i}.00'),
                'category': f'Category_{i % 5}',
                'currency': 'USD'
            }
            add_cost(cost_data)
        
        return clean_test_db
    
    def test_query_performance(self, populated_test_db, performance_monitor):
        """Test query performance with indexed and non-indexed columns"""
        performance_monitor.start()
        
        # Test simple select
        costs_df = get_costs()
        
        performance_monitor.assert_max_duration(0.5)
        assert len(costs_df) == 100
    
    def test_aggregation_performance(self, populated_test_db, performance_monitor):
        """Test aggregation query performance"""
        conn = get_db_connection()
        
        performance_monitor.start()
        
        # Test aggregation queries
        cursor = conn.cursor()
        cursor.execute("""
            SELECT category, COUNT(*), SUM(amount), AVG(amount)
            FROM costs
            GROUP BY category
        """)
        results = cursor.fetchall()
        
        performance_monitor.assert_max_duration(0.2)
        assert len(results) == 5  # 5 categories
        
        conn.close()
    
    def test_index_effectiveness(self, populated_test_db):
        """Test database index effectiveness"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create index on category
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_costs_category ON costs(category)")
        
        # Test query with index
        cursor.execute("EXPLAIN QUERY PLAN SELECT * FROM costs WHERE category = ?", ('Category_1',))
        query_plan = cursor.fetchall()
        
        # Should use index scan instead of table scan
        plan_text = ' '.join([str(row) for row in query_plan])
        assert 'idx_costs_category' in plan_text or 'INDEX' in plan_text.upper()
        
        conn.close()

@pytest.mark.integration
class TestDatabaseSecurity:
    """Test database security and access controls"""
    
    def test_sql_injection_prevention(self, clean_test_db):
        """Test SQL injection prevention in parameterized queries"""
        # Attempt SQL injection through cost data
        malicious_data = {
            'date': date(2024, 8, 17),
            'amount': Decimal('100.00'),
            'category': "'; DROP TABLE costs; --",
            'currency': 'USD'
        }
        
        # This should not cause SQL injection due to parameterized queries
        add_cost(malicious_data)
        
        # Verify table still exists and data is properly escaped
        costs_df = get_costs()
        assert len(costs_df) == 1
        assert costs_df.iloc[0]['category'] == "'; DROP TABLE costs; --"
    
    def test_database_permissions(self, clean_test_db):
        """Test database file permissions"""
        import stat
        
        # Check database file permissions
        file_stat = os.stat(clean_test_db)
        file_mode = stat.filemode(file_stat.st_mode)
        
        # Database should not be world-readable
        assert not (file_stat.st_mode & stat.S_IROTH)
        assert not (file_stat.st_mode & stat.S_IWOTH)
    
    def test_connection_security(self, clean_test_db):
        """Test database connection security"""
        conn = get_db_connection()
        
        # Test that connection uses secure settings
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys")
        foreign_keys_enabled = cursor.fetchone()[0]
        
        # Foreign keys should be enabled for data integrity
        assert foreign_keys_enabled == 1
        
        conn.close()
