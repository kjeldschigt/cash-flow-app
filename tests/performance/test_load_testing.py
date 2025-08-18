"""
Performance and load testing suite for the Cash Flow Dashboard
"""

import pytest
import time
import threading
import concurrent.futures
import sys
import os
from datetime import datetime, date, timedelta
from decimal import Decimal
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from src.services.storage_service import add_cost, get_costs, add_sales_order, get_sales_orders
from services.validators import validate_amount, validate_date, validate_currency
from models.cost import Cost

@pytest.mark.performance
class TestDatabasePerformance:
    """Test database performance under load"""
    
    def test_bulk_insert_performance(self, clean_test_db, performance_monitor):
        """Test performance of bulk data insertion"""
        performance_monitor.start()
        
        # Insert 1000 cost records
        for i in range(1000):
            cost_data = {
                'date': date(2024, 8, 17),
                'amount': Decimal(f'{100 + i}.00'),
                'category': f'Category_{i % 10}',
                'subcategory': f'Subcategory_{i % 5}',
                'description': f'Test cost {i}',
                'currency': 'USD'
            }
            add_cost(cost_data)
        
        performance_monitor.assert_max_duration(10.0)
        
        # Verify all records were inserted
        costs_df = get_costs()
        assert len(costs_df) == 1000
    
    def test_concurrent_read_performance(self, populated_test_db, performance_monitor):
        """Test concurrent read performance"""
        def read_costs():
            return get_costs()
        
        performance_monitor.start()
        
        # Execute 50 concurrent reads
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(read_costs) for _ in range(50)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        performance_monitor.assert_max_duration(5.0)
        
        # Verify all reads returned data
        assert all(len(df) > 0 for df in results)
    
    def test_concurrent_write_performance(self, clean_test_db, performance_monitor):
        """Test concurrent write performance"""
        def add_cost_worker(worker_id, num_records):
            for i in range(num_records):
                cost_data = {
                    'date': date(2024, 8, 17),
                    'amount': Decimal(f'{worker_id * 100 + i}.00'),
                    'category': f'Worker_{worker_id}',
                    'currency': 'USD'
                }
                add_cost(cost_data)
        
        performance_monitor.start()
        
        # 5 workers, each adding 100 records
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(add_cost_worker, worker_id, 100)
                for worker_id in range(5)
            ]
            for future in concurrent.futures.as_completed(futures):
                future.result()
        
        performance_monitor.assert_max_duration(15.0)
        
        # Verify all records were added
        costs_df = get_costs()
        assert len(costs_df) == 500
    
    def test_large_dataset_query_performance(self, performance_monitor):
        """Test query performance with large datasets"""
        # Create large dataset
        large_data = []
        for i in range(10000):
            large_data.append({
                'date': date(2024, 1, 1) + timedelta(days=i % 365),
                'amount': Decimal(f'{np.random.uniform(10, 1000):.2f}'),
                'category': f'Category_{i % 20}',
                'currency': 'USD'
            })
        
        # Insert data (not timed)
        for cost_data in large_data:
            add_cost(cost_data)
        
        performance_monitor.start()
        
        # Test various query patterns
        costs_df = get_costs()
        
        # Filter by category
        filtered_df = costs_df[costs_df['category'] == 'Category_1']
        
        # Aggregate operations
        total_by_category = costs_df.groupby('category')['amount'].sum()
        monthly_totals = costs_df.groupby(costs_df['date'].dt.to_period('M'))['amount'].sum()
        
        performance_monitor.assert_max_duration(3.0)
        
        assert len(costs_df) == 10000
        assert len(filtered_df) > 0
        assert len(total_by_category) == 20
    
    def test_memory_usage_under_load(self, clean_test_db):
        """Test memory usage during heavy operations"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Perform memory-intensive operations
        for batch in range(10):
            batch_data = []
            for i in range(1000):
                cost_data = {
                    'date': date(2024, 8, 17),
                    'amount': Decimal(f'{batch * 1000 + i}.00'),
                    'category': f'Batch_{batch}',
                    'currency': 'USD'
                }
                batch_data.append(cost_data)
            
            # Add batch
            for cost_data in batch_data:
                add_cost(cost_data)
            
            # Read data
            costs_df = get_costs()
            
            # Clear batch data
            del batch_data
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB)
        assert memory_increase < 100, f"Memory increased by {memory_increase}MB"

@pytest.mark.performance
class TestValidationPerformance:
    """Test validation function performance"""
    
    def test_amount_validation_performance(self, performance_monitor):
        """Test amount validation performance"""
        test_amounts = [
            Decimal('100.50'), Decimal('0.01'), Decimal('999999.99'),
            Decimal('-100'), 'invalid', None, '', '100.50'
        ] * 1000
        
        performance_monitor.start()
        
        results = [validate_amount(amount) for amount in test_amounts]
        
        performance_monitor.assert_max_duration(1.0)
        assert len(results) == 8000
    
    def test_date_validation_performance(self, performance_monitor):
        """Test date validation performance"""
        test_dates = [
            date(2024, 8, 17), '2024-08-17', 'invalid-date',
            None, '', datetime.now(), '2024-13-45'
        ] * 1000
        
        performance_monitor.start()
        
        results = [validate_date(test_date) for test_date in test_dates]
        
        performance_monitor.assert_max_duration(1.0)
        assert len(results) == 7000
    
    def test_currency_validation_performance(self, performance_monitor):
        """Test currency validation performance"""
        test_currencies = [
            'USD', 'EUR', 'GBP', 'JPY', 'INVALID', '', None, 'usd'
        ] * 1000
        
        performance_monitor.start()
        
        results = [validate_currency(currency) for currency in test_currencies]
        
        performance_monitor.assert_max_duration(0.5)
        assert len(results) == 8000

@pytest.mark.performance
class TestModelPerformance:
    """Test Pydantic model performance"""
    
    def test_model_creation_performance(self, performance_monitor):
        """Test Cost model creation performance"""
        performance_monitor.start()
        
        costs = []
        for i in range(1000):
            cost = Cost(
                date=date(2024, 8, 17),
                amount=Decimal(f'{100 + i}.00'),
                category='Operating',
                currency='USD'
            )
            costs.append(cost)
        
        performance_monitor.assert_max_duration(2.0)
        assert len(costs) == 1000
    
    def test_model_serialization_performance(self, performance_monitor):
        """Test model serialization performance"""
        costs = [
            Cost(
                date=date(2024, 8, 17),
                amount=Decimal(f'{100 + i}.00'),
                category='Operating',
                currency='USD'
            )
            for i in range(1000)
        ]
        
        performance_monitor.start()
        
        # Test JSON serialization
        json_data = [cost.json() for cost in costs]
        
        # Test dict serialization
        dict_data = [cost.dict() for cost in costs]
        
        performance_monitor.assert_max_duration(3.0)
        assert len(json_data) == 1000
        assert len(dict_data) == 1000
    
    def test_model_validation_performance(self, performance_monitor):
        """Test model validation performance"""
        valid_data = {
            'date': date(2024, 8, 17),
            'amount': Decimal('100.00'),
            'category': 'Operating',
            'currency': 'USD'
        }
        
        invalid_data = {
            'date': 'invalid-date',
            'amount': 'not-a-number',
            'category': '',
            'currency': 'INVALID'
        }
        
        performance_monitor.start()
        
        # Test valid data
        valid_costs = []
        for i in range(500):
            try:
                cost = Cost(**valid_data)
                valid_costs.append(cost)
            except Exception:
                pass
        
        # Test invalid data
        invalid_costs = []
        for i in range(500):
            try:
                cost = Cost(**invalid_data)
                invalid_costs.append(cost)
            except Exception:
                pass
        
        performance_monitor.assert_max_duration(2.0)
        assert len(valid_costs) == 500
        assert len(invalid_costs) == 0

@pytest.mark.performance
class TestStreamlitComponentPerformance:
    """Test Streamlit component rendering performance"""
    
    def test_large_dataframe_rendering(self, performance_monitor):
        """Test rendering large DataFrames"""
        # Create large DataFrame
        data = {
            'date': [date(2024, 8, 17)] * 10000,
            'amount': [Decimal('100.00')] * 10000,
            'category': ['Operating'] * 10000,
            'currency': ['USD'] * 10000
        }
        large_df = pd.DataFrame(data)
        
        performance_monitor.start()
        
        # Simulate DataFrame operations that would happen in Streamlit
        filtered_df = large_df[large_df['category'] == 'Operating']
        grouped_df = large_df.groupby('category')['amount'].sum()
        sorted_df = large_df.sort_values('amount', ascending=False)
        
        performance_monitor.assert_max_duration(2.0)
        
        assert len(filtered_df) == 10000
        assert len(grouped_df) == 1
        assert len(sorted_df) == 10000
    
    def test_chart_data_preparation(self, performance_monitor):
        """Test chart data preparation performance"""
        # Generate time series data
        dates = pd.date_range(start='2024-01-01', end='2024-08-17', freq='D')
        amounts = np.random.uniform(100, 1000, len(dates))
        
        df = pd.DataFrame({
            'date': dates,
            'amount': amounts,
            'category': np.random.choice(['Operating', 'Marketing', 'Sales'], len(dates))
        })
        
        performance_monitor.start()
        
        # Prepare data for various chart types
        
        # Line chart data
        daily_totals = df.groupby('date')['amount'].sum()
        
        # Bar chart data
        category_totals = df.groupby('category')['amount'].sum()
        
        # Pie chart data
        category_percentages = (category_totals / category_totals.sum() * 100)
        
        # Heatmap data
        df['month'] = df['date'].dt.month
        df['day'] = df['date'].dt.day
        heatmap_data = df.pivot_table(values='amount', index='month', columns='day', aggfunc='sum')
        
        performance_monitor.assert_max_duration(1.0)
        
        assert len(daily_totals) > 0
        assert len(category_totals) == 3
        assert len(category_percentages) == 3

@pytest.mark.performance
class TestConcurrencyStress:
    """Stress test concurrent operations"""
    
    def test_high_concurrency_reads(self, populated_test_db, performance_monitor):
        """Test system under high concurrent read load"""
        def read_worker():
            for _ in range(10):
                costs_df = get_costs()
                # Simulate processing
                total = costs_df['amount'].sum()
                time.sleep(0.01)
            return True
        
        performance_monitor.start()
        
        # 20 workers, each doing 10 reads
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(read_worker) for _ in range(20)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        performance_monitor.assert_max_duration(10.0)
        assert all(results)
    
    def test_mixed_read_write_load(self, clean_test_db, performance_monitor):
        """Test mixed read/write operations under load"""
        def write_worker(worker_id):
            for i in range(50):
                cost_data = {
                    'date': date(2024, 8, 17),
                    'amount': Decimal(f'{worker_id * 100 + i}.00'),
                    'category': f'Worker_{worker_id}',
                    'currency': 'USD'
                }
                add_cost(cost_data)
                time.sleep(0.01)
        
        def read_worker():
            for _ in range(100):
                costs_df = get_costs()
                time.sleep(0.005)
        
        performance_monitor.start()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            # 5 write workers
            write_futures = [executor.submit(write_worker, i) for i in range(5)]
            
            # 10 read workers
            read_futures = [executor.submit(read_worker) for _ in range(10)]
            
            # Wait for all to complete
            for future in concurrent.futures.as_completed(write_futures + read_futures):
                future.result()
        
        performance_monitor.assert_max_duration(15.0)
        
        # Verify data integrity
        costs_df = get_costs()
        assert len(costs_df) == 250  # 5 workers * 50 records each

@pytest.mark.performance
class TestMemoryLeakDetection:
    """Test for memory leaks during long-running operations"""
    
    def test_repeated_operations_memory_stability(self):
        """Test memory stability during repeated operations"""
        import psutil
        import gc
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        memory_samples = []
        
        for iteration in range(100):
            # Perform operations that might leak memory
            costs = []
            for i in range(100):
                cost = Cost(
                    date=date(2024, 8, 17),
                    amount=Decimal(f'{i}.00'),
                    category='Operating',
                    currency='USD'
                )
                costs.append(cost)
            
            # Serialize and deserialize
            json_data = [cost.json() for cost in costs]
            dict_data = [cost.dict() for cost in costs]
            
            # Clear references
            del costs, json_data, dict_data
            
            # Force garbage collection
            gc.collect()
            
            # Sample memory every 10 iterations
            if iteration % 10 == 0:
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_samples.append(current_memory)
        
        final_memory = process.memory_info().rss / 1024 / 1024
        
        # Memory should not continuously increase
        # Allow for some variance but detect significant leaks
        memory_increase = final_memory - initial_memory
        assert memory_increase < 50, f"Potential memory leak detected: {memory_increase}MB increase"
        
        # Memory samples should not show continuous growth
        if len(memory_samples) > 5:
            # Check if memory is continuously increasing
            increases = sum(1 for i in range(1, len(memory_samples)) 
                          if memory_samples[i] > memory_samples[i-1])
            increase_ratio = increases / (len(memory_samples) - 1)
            
            # Less than 70% of samples should show increase
            assert increase_ratio < 0.7, f"Memory continuously increasing: {increase_ratio:.2%}"

@pytest.mark.performance
class TestScalabilityLimits:
    """Test system scalability limits"""
    
    def test_maximum_record_capacity(self, clean_test_db):
        """Test system behavior at maximum record capacity"""
        # Test with increasingly large datasets
        record_counts = [1000, 5000, 10000, 25000]
        
        for count in record_counts:
            start_time = time.time()
            
            # Add records
            for i in range(count):
                cost_data = {
                    'date': date(2024, 8, 17),
                    'amount': Decimal(f'{i}.00'),
                    'category': f'Category_{i % 100}',
                    'currency': 'USD'
                }
                add_cost(cost_data)
            
            # Test read performance
            costs_df = get_costs()
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Performance should degrade gracefully
            assert duration < count * 0.01, f"Performance degraded too much for {count} records"
            assert len(costs_df) == count
            
            # Clean up for next test
            # (In real test, you'd reset the database)
    
    def test_concurrent_user_simulation(self, clean_test_db, performance_monitor):
        """Simulate multiple concurrent users"""
        def simulate_user(user_id):
            """Simulate a user session"""
            # Add some costs
            for i in range(10):
                cost_data = {
                    'date': date(2024, 8, 17),
                    'amount': Decimal(f'{user_id * 10 + i}.00'),
                    'category': f'User_{user_id}',
                    'currency': 'USD'
                }
                add_cost(cost_data)
            
            # Read and analyze data
            for _ in range(5):
                costs_df = get_costs()
                user_costs = costs_df[costs_df['category'] == f'User_{user_id}']
                total = user_costs['amount'].sum()
                time.sleep(0.1)  # Simulate user think time
        
        performance_monitor.start()
        
        # Simulate 50 concurrent users
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(simulate_user, user_id) for user_id in range(50)]
            for future in concurrent.futures.as_completed(futures):
                future.result()
        
        performance_monitor.assert_max_duration(30.0)
        
        # Verify all user data was recorded
        costs_df = get_costs()
        assert len(costs_df) == 500  # 50 users * 10 costs each
