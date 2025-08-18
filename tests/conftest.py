"""
Pytest configuration and fixtures for the Cash Flow Dashboard test suite
"""

import pytest
import sqlite3
import tempfile
import os
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
from unittest.mock import Mock, patch
import sys

# Add project root to Python path to allow imports from 'src'
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.config.settings import Settings, DatabaseConfig, SecurityConfig
from src.models.cost import Cost
from src.models.user import User, UserRole
from src.repositories.base import DatabaseConnection
from src.services.storage_service import init_db

@pytest.fixture(scope="session")
def test_settings():
    """Create test settings configuration"""
    return Settings(
        database=DatabaseConfig(
            path=":memory:",
            users_db_path=":memory:",
            connection_timeout=5.0
        ),
        security=SecurityConfig(
            secret_key="test_secret_key_for_testing_only_32_chars",
            session_timeout_minutes=60,
            bcrypt_rounds=4  # Faster for tests
        )
    )

@pytest.fixture
def temp_db():
    """Create temporary database for testing"""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_file.close()
    
    # Initialize database
    conn = sqlite3.connect(temp_file.name)
    cursor = conn.cursor()
    
    # Create test tables
    cursor.execute('''
        CREATE TABLE costs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            subcategory TEXT,
            description TEXT,
            currency TEXT DEFAULT 'USD',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE sales_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            currency TEXT DEFAULT 'USD',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'USER',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    
    yield temp_file.name
    
    # Cleanup
    os.unlink(temp_file.name)

@pytest.fixture
def sample_costs_data():
    """Generate sample costs data for testing"""
    base_date = datetime.now() - timedelta(days=30)
    
    costs = []
    categories = ['Operating', 'Marketing', 'Personnel', 'Equipment']
    
    for i in range(50):
        cost_date = base_date + timedelta(days=i % 30)
        costs.append({
            'date': cost_date.strftime('%Y-%m-%d'),
            'amount': 100 + (i * 10) + (i % 7 * 50),
            'category': categories[i % len(categories)],
            'subcategory': f'Sub-{categories[i % len(categories)]}',
            'description': f'Test cost entry {i}',
            'currency': 'USD'
        })
    
    return costs

@pytest.fixture
def sample_sales_data():
    """Generate sample sales data for testing"""
    base_date = datetime.now() - timedelta(days=30)
    
    sales = []
    categories = ['Product Sales', 'Service Revenue', 'Subscriptions']
    
    for i in range(30):
        sale_date = base_date + timedelta(days=i)
        sales.append({
            'date': sale_date.strftime('%Y-%m-%d'),
            'amount': 1000 + (i * 50) + (i % 5 * 200),
            'category': categories[i % len(categories)],
            'description': f'Test sale entry {i}',
            'currency': 'USD'
        })
    
    return sales

@pytest.fixture
def populated_test_db(temp_db, sample_costs_data, sample_sales_data):
    """Create populated test database"""
    db_conn = DatabaseConnection(db_path=temp_db)
    conn = db_conn.get_connection()
    cursor = conn.cursor()
    
    # Insert sample costs
    for cost in sample_costs_data:
        cursor.execute('''
            INSERT INTO costs (date, amount, category, subcategory, description, currency)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (cost['date'], cost['amount'], cost['category'], 
              cost['subcategory'], cost['description'], cost['currency']))
    
    # Insert sample sales
    for sale in sample_sales_data:
        cursor.execute('''
            INSERT INTO sales_orders (date, amount, category, description, currency)
            VALUES (?, ?, ?, ?, ?)
        ''', (sale['date'], sale['amount'], sale['category'], 
              sale['description'], sale['currency']))
    
    # Insert test user
    cursor.execute('''
        INSERT INTO users (email, password_hash, role)
        VALUES (?, ?, ?)
    ''', ('test@example.com', 'hashed_password', 'ADMIN'))
    
    conn.commit()
    conn.close()
    
    return temp_db

@pytest.fixture
def mock_stripe():
    """Mock Stripe API for testing"""
    with patch('stripe.Account') as mock_account, \
         patch('stripe.Customer') as mock_customer, \
         patch('stripe.PaymentIntent') as mock_payment:
        
        # Configure mock responses
        mock_account.retrieve.return_value = Mock(id='acct_test123')
        mock_customer.create.return_value = Mock(id='cus_test123')
        mock_payment.create.return_value = Mock(
            id='pi_test123',
            status='succeeded',
            amount=1000
        )
        
        yield {
            'account': mock_account,
            'customer': mock_customer,
            'payment': mock_payment
        }

@pytest.fixture
def mock_airtable():
    """Mock Airtable API for testing"""
    with patch('requests.get') as mock_get, \
         patch('requests.post') as mock_post:
        
        # Configure mock responses
        mock_get.return_value = Mock(
            status_code=200,
            json=lambda: {
                'records': [
                    {
                        'id': 'rec123',
                        'fields': {
                            'Name': 'Test Record',
                            'Amount': 1000,
                            'Date': '2024-08-17'
                        }
                    }
                ]
            }
        )
        
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {
                'id': 'rec456',
                'fields': {
                    'Name': 'Created Record',
                    'Amount': 500
                }
            }
        )
        
        yield {
            'get': mock_get,
            'post': mock_post
        }

@pytest.fixture
def test_user():
    """Create test user instance"""
    return User(
        id=1,
        email='test@example.com',
        role=UserRole.ADMIN,
        created_at=datetime.now()
    )

@pytest.fixture
def test_cost():
    """Create test cost instance"""
    return Cost(
        id=1,
        date=datetime.now().date(),
        amount=100.50,
        category='Operating',
        subcategory='Office Supplies',
        description='Test cost entry',
        currency='USD'
    )

@pytest.fixture
def financial_data_samples():
    """Provide sample financial data for calculations"""
    return {
        'revenues': [1000, 1200, 1100, 1300, 1250],
        'costs': [800, 900, 850, 950, 900],
        'dates': pd.date_range('2024-01-01', periods=5, freq='M'),
        'currencies': ['USD', 'EUR', 'GBP'],
        'exchange_rates': {
            'USD': 1.0,
            'EUR': 0.85,
            'GBP': 0.73
        }
    }

@pytest.fixture
def mock_email_service():
    """Mock email service for testing notifications"""
    with patch('smtplib.SMTP') as mock_smtp:
        mock_server = Mock()
        mock_smtp.return_value = mock_server
        
        yield mock_server

@pytest.fixture
def performance_test_data():
    """Generate large dataset for performance testing"""
    dates = pd.date_range('2020-01-01', '2024-08-17', freq='D')
    
    large_dataset = []
    for i, date in enumerate(dates):
        large_dataset.append({
            'id': i,
            'date': date,
            'amount': 100 + (i % 1000),
            'category': f'Category_{i % 10}',
            'description': f'Performance test entry {i}'
        })
    
    return pd.DataFrame(large_dataset)

@pytest.fixture(autouse=True)
def cleanup_session_state():
    """Clean up any session state between tests"""
    # This would clean up Streamlit session state if needed
    yield
    # Cleanup code here

# Test configuration
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as a performance test"
    )
    config.addinivalue_line(
        "markers", "security: mark test as a security test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )

# Custom assertions
class CustomAssertions:
    """Custom assertion helpers for financial data"""
    
    @staticmethod
    def assert_currency_equal(actual, expected, tolerance=0.01):
        """Assert currency values are equal within tolerance"""
        assert abs(actual - expected) <= tolerance, f"Expected {expected}, got {actual}"
    
    @staticmethod
    def assert_percentage_equal(actual, expected, tolerance=0.1):
        """Assert percentage values are equal within tolerance"""
        assert abs(actual - expected) <= tolerance, f"Expected {expected}%, got {actual}%"
    
    @staticmethod
    def assert_dataframe_structure(df, expected_columns, min_rows=0):
        """Assert DataFrame has expected structure"""
        assert isinstance(df, pd.DataFrame), "Expected pandas DataFrame"
        assert list(df.columns) == expected_columns, f"Expected columns {expected_columns}, got {list(df.columns)}"
        assert len(df) >= min_rows, f"Expected at least {min_rows} rows, got {len(df)}"

@pytest.fixture
def assert_helper():
    """Provide custom assertion helpers"""
    return CustomAssertions()

# Database helpers
class DatabaseHelpers:
    """Helper functions for database testing"""
    
    @staticmethod
    def count_records(db_path, table_name):
        """Count records in a table"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    @staticmethod
    def get_latest_record(db_path, table_name, order_by='id'):
        """Get the latest record from a table"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {table_name} ORDER BY {order_by} DESC LIMIT 1")
        record = cursor.fetchone()
        conn.close()
        return record

@pytest.fixture
def db_helpers():
    """Provide database helper functions"""
    return DatabaseHelpers()

# Performance monitoring
@pytest.fixture
def performance_monitor():
    """Monitor test performance"""
    import time
    
    class PerformanceMonitor:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def start(self):
            self.start_time = time.time()
        
        def stop(self):
            self.end_time = time.time()
            return self.end_time - self.start_time
        
        def assert_max_duration(self, max_seconds):
            duration = self.stop()
            assert duration <= max_seconds, f"Test took {duration:.2f}s, expected <= {max_seconds}s"
    
    return PerformanceMonitor()

# Environment setup
@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment"""
    # Set test environment variables
    os.environ['TESTING'] = 'true'
    os.environ['DATABASE_PATH'] = ':memory:'
    os.environ['SECRET_KEY'] = 'test_secret_key_for_testing_only_32_chars'
    
    yield
    
    # Cleanup
    if 'TESTING' in os.environ:
        del os.environ['TESTING']
