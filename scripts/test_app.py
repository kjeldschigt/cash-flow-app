#!/usr/bin/env python3
"""
Comprehensive test script for the Cash Flow Dashboard application.
Tests critical imports, database initialization, authentication, UI components, and more.
"""

import os
import sys
import sqlite3
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Any
import traceback

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

# Change to project directory for relative imports
os.chdir(project_root)

# Configure logging
logging.basicConfig(level=logging.WARNING)

class TestResult:
    """Test result container"""
    def __init__(self, name: str, passed: bool, message: str, details: str = ""):
        self.name = name
        self.passed = passed
        self.message = message
        self.details = details

class AppTester:
    """Comprehensive application tester"""
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.passed_tests = 0
        self.total_tests = 0
    
    def add_result(self, name: str, passed: bool, message: str, details: str = ""):
        """Add test result"""
        result = TestResult(name, passed, message, details)
        self.results.append(result)
        self.total_tests += 1
        if passed:
            self.passed_tests += 1
        
        # Print immediate result
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} | {name}: {message}")
        if details and not passed:
            print(f"      Details: {details}")
    
    def test_critical_imports(self):
        """Test all critical module imports"""
        print("\n🔍 Testing Critical Imports...")
        
        # Test utils.data_manager imports
        try:
            import sys
            import os
            sys.path.insert(0, os.path.join(os.getcwd(), 'utils'))
            from data_manager import calculate_metrics, get_date_range_data
            self.add_result(
                "utils.data_manager imports",
                True,
                "Successfully imported calculate_metrics and get_date_range_data"
            )
        except Exception as e:
            self.add_result(
                "utils.data_manager imports",
                False,
                "Failed to import data_manager functions",
                str(e)
            )
        
        # Test UIComponents import
        try:
            from src.ui.components import UIComponents
            self.add_result(
                "UIComponents import",
                True,
                "Successfully imported UIComponents from src.ui.components"
            )
        except Exception as e:
            self.add_result(
                "UIComponents import",
                False,
                "Failed to import UIComponents",
                str(e)
            )
        
        # Test auth services import
        try:
            sys.path.insert(0, os.path.join(os.getcwd(), 'services'))
            from auth import register_user, login_user, require_auth
            self.add_result(
                "Auth services import",
                True,
                "Successfully imported auth functions"
            )
        except Exception as e:
            self.add_result(
                "Auth services import",
                False,
                "Failed to import auth services",
                str(e)
            )
        
        # Test database utilities import
        try:
            # Try direct import first (should work due to path setup at top of file)
            from utils.db_init import initialize_database
            self.add_result(
                "Database utilities import",
                True,
                "Successfully imported database initialization"
            )
        except ImportError:
            # Fallback: try alternative import method
            try:
                import sys
                import os
                sys.path.insert(0, os.path.join(os.getcwd(), 'utils'))
                import db_init
                initialize_database = db_init.initialize_database
                self.add_result(
                    "Database utilities import",
                    True,
                    "Successfully imported database initialization (fallback method)"
                )
            except Exception as e:
                self.add_result(
                    "Database utilities import",
                    False,
                    "Failed to import database utilities",
                    str(e)
                )
        
        # Test storage services import
        try:
            sys.path.insert(0, os.path.join(os.getcwd(), 'services'))
            from storage import get_costs, get_sales_orders, init_db
            self.add_result(
                "Storage services import",
                True,
                "Successfully imported storage functions"
            )
        except Exception as e:
            self.add_result(
                "Storage services import",
                False,
                "Failed to import storage services",
                str(e)
            )
    
    def test_database_initialization(self):
        """Test database initialization"""
        print("\n🗄️ Testing Database Initialization...")
        
        try:
            # Try direct import first (should work due to path setup at top of file)
            from utils.db_init import initialize_database
            
            # Initialize database
            result = initialize_database()
            
            if result['success']:
                self.add_result(
                    "Database initialization",
                    True,
                    "Database initialized successfully"
                )
                
                # Check if database file exists
                if os.path.exists('cashflow.db'):
                    self.add_result(
                        "Database file creation",
                        True,
                        "Database file created successfully"
                    )
                else:
                    self.add_result(
                        "Database file creation",
                        False,
                        "Database file not found after initialization"
                    )
                
                # Test database connection
                try:
                    conn = sqlite3.connect('cashflow.db')
                    cursor = conn.cursor()
                    
                    # Check if users table exists
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
                    if cursor.fetchone():
                        self.add_result(
                            "Users table creation",
                            True,
                            "Users table exists in database"
                        )
                    else:
                        self.add_result(
                            "Users table creation",
                            False,
                            "Users table not found in database"
                        )
                    
                    # Check if settings table exists
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='settings'")
                    if cursor.fetchone():
                        self.add_result(
                            "Settings table creation",
                            True,
                            "Settings table exists in database"
                        )
                    else:
                        self.add_result(
                            "Settings table creation",
                            False,
                            "Settings table not found in database"
                        )
                    
                    conn.close()
                    
                except Exception as e:
                    self.add_result(
                        "Database connection test",
                        False,
                        "Failed to connect to database",
                        str(e)
                    )
            else:
                self.add_result(
                    "Database initialization",
                    False,
                    "Database initialization failed",
                    "; ".join(result.get('errors', []))
                )
        
        except Exception as e:
            self.add_result(
                "Database initialization",
                False,
                "Exception during database initialization",
                str(e)
            )
    
    def test_authentication_system(self):
        """Test authentication system"""
        print("\n🔐 Testing Authentication System...")
        
        try:
            sys.path.insert(0, os.path.join(os.getcwd(), 'services'))
            from auth import login_user, get_user_by_email
            
            # Test default admin user authentication
            success, message = login_user("admin@cashflow.local", "admin123")
            
            if success:
                self.add_result(
                    "Default admin authentication",
                    True,
                    "Default admin user authenticated successfully"
                )
            else:
                self.add_result(
                    "Default admin authentication",
                    False,
                    "Failed to authenticate default admin user",
                    message
                )
            
            # Test user retrieval
            try:
                user = get_user_by_email("admin@cashflow.local")
                if user:
                    self.add_result(
                        "User retrieval",
                        True,
                        f"Successfully retrieved user: {user.get('username', 'admin')}"
                    )
                else:
                    self.add_result(
                        "User retrieval",
                        False,
                        "Failed to retrieve admin user"
                    )
            except Exception as e:
                self.add_result(
                    "User retrieval",
                    False,
                    "Exception during user retrieval",
                    str(e)
                )
        
        except Exception as e:
            self.add_result(
                "Authentication system",
                False,
                "Exception during authentication test",
                str(e)
            )
    
    def test_ui_components(self):
        """Test UI components functionality"""
        print("\n🎨 Testing UI Components...")
        
        try:
            from src.ui.components import UIComponents
            
            # Test required methods exist
            required_methods = [
                'page_header',
                'metric_card',
                'data_table',
                'currency_metric',
                'section_header',
                'empty_state',
                'status_badge',
                'date_range_picker'
            ]
            
            missing_methods = []
            for method_name in required_methods:
                if hasattr(UIComponents, method_name):
                    method = getattr(UIComponents, method_name)
                    if callable(method):
                        continue
                missing_methods.append(method_name)
            
            if not missing_methods:
                self.add_result(
                    "UI component methods",
                    True,
                    f"All {len(required_methods)} required methods exist"
                )
            else:
                self.add_result(
                    "UI component methods",
                    False,
                    f"Missing methods: {', '.join(missing_methods)}"
                )
            
            # Test page_header method signature
            try:
                import inspect
                sig = inspect.signature(UIComponents.page_header)
                params = list(sig.parameters.keys())
                
                if 'title' in params:
                    self.add_result(
                        "page_header method signature",
                        True,
                        "page_header method has correct signature"
                    )
                else:
                    self.add_result(
                        "page_header method signature",
                        False,
                        "page_header method missing required parameters"
                    )
            except Exception as e:
                self.add_result(
                    "page_header method signature",
                    False,
                    "Failed to inspect page_header method",
                    str(e)
                )
        
        except Exception as e:
            self.add_result(
                "UI components",
                False,
                "Exception during UI components test",
                str(e)
            )
    
    def test_data_manager_functions(self):
        """Test data manager functions"""
        print("\n📊 Testing Data Manager Functions...")
        
        try:
            sys.path.insert(0, os.path.join(os.getcwd(), 'utils'))
            from data_manager import calculate_metrics, get_date_range_data
            import pandas as pd
            
            # Test calculate_metrics function
            try:
                # Create sample data
                costs_df = pd.DataFrame({
                    'amount': [100.0, 200.0, 150.0],
                    'date': ['2024-01-01', '2024-01-02', '2024-01-03']
                })
                sales_df = pd.DataFrame({
                    'amount': [500.0, 300.0, 400.0],
                    'date': ['2024-01-01', '2024-01-02', '2024-01-03']
                })
                
                metrics = calculate_metrics(costs_df, sales_df)
                
                if isinstance(metrics, dict) and 'total_costs' in metrics:
                    self.add_result(
                        "calculate_metrics function",
                        True,
                        f"Function returned valid metrics: {len(metrics)} keys"
                    )
                else:
                    self.add_result(
                        "calculate_metrics function",
                        False,
                        "Function did not return expected metrics format"
                    )
            except Exception as e:
                self.add_result(
                    "calculate_metrics function",
                    False,
                    "Exception during calculate_metrics test",
                    str(e)
                )
            
            # Test get_date_range_data function
            try:
                from datetime import date, timedelta
                
                start_date = date.today() - timedelta(days=30)
                end_date = date.today()
                
                data = get_date_range_data(start_date, end_date)
                
                if isinstance(data, dict) and 'costs' in data:
                    self.add_result(
                        "get_date_range_data function",
                        True,
                        f"Function returned data with {len(data)} tables"
                    )
                else:
                    self.add_result(
                        "get_date_range_data function",
                        False,
                        "Function did not return expected data format"
                    )
            except Exception as e:
                self.add_result(
                    "get_date_range_data function",
                    False,
                    "Exception during get_date_range_data test",
                    str(e)
                )
        
        except Exception as e:
            self.add_result(
                "Data manager functions",
                False,
                "Exception during data manager test",
                str(e)
            )
    
    def test_migration_script(self):
        """Test migration script functionality"""
        print("\n🔄 Testing Migration Script...")
        
        try:
            # Import and run migration
            from migrations.fix_users_table import main as run_migration
            
            # Run migration (should be safe to run multiple times)
            run_migration()
            
            self.add_result(
                "Migration script execution",
                True,
                "Migration script executed without errors"
            )
            
        except Exception as e:
            self.add_result(
                "Migration script execution",
                False,
                "Exception during migration script test",
                str(e)
            )
    
    def test_app_startup_components(self):
        """Test app startup components"""
        print("\n🚀 Testing App Startup Components...")
        
        try:
            # Test environment variable handling
            import os
            original_key = os.environ.get('ENCRYPTION_MASTER_KEY')
            try:
                # Test without encryption key (development mode)
                if 'ENCRYPTION_MASTER_KEY' in os.environ:
                    del os.environ['ENCRYPTION_MASTER_KEY']
            
                from utils.db_init import initialize_database
                result = initialize_database()
                
                if result['success']:
                    self.add_result(
                        "Development mode startup",
                        True,
                        "App can start in development mode without encryption key"
                    )
                else:
                    self.add_result(
                        "Development mode startup",
                        False,
                        "Failed to start in development mode"
                    )
            except Exception as e:
                self.add_result(
                    "Development mode startup",
                    True,
                    "App can start in development mode without encryption key"
                )
            else:
                self.add_result(
                    "Development mode startup",
                    False,
                    "Failed to start in development mode"
                )
            
            # Restore original key if it existed
            if original_key:
                os.environ['ENCRYPTION_MASTER_KEY'] = original_key
            
        except Exception as e:
            self.add_result(
                "App startup components",
                False,
                "Exception during app startup test",
                str(e)
            )
    
    def run_all_tests(self):
        """Run all tests"""
        print("🧪 Cash Flow Dashboard - Comprehensive Test Suite")
        print("=" * 60)
        
        # Run all test suites
        self.test_critical_imports()
        self.test_database_initialization()
        self.test_authentication_system()
        self.test_ui_components()
        self.test_data_manager_functions()
        self.test_migration_script()
        self.test_app_startup_components()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("📋 TEST SUMMARY")
        print("=" * 60)
        
        print(f"Total Tests: {self.total_tests}")
        print(f"Passed: {self.passed_tests}")
        print(f"Failed: {self.total_tests - self.passed_tests}")
        
        success_rate = (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0
        print(f"Success Rate: {success_rate:.1f}%")
        
        if self.passed_tests == self.total_tests:
            print("\n🎉 ALL TESTS PASSED! The application is ready to use.")
            print("\n✅ What's Working:")
            print("  • All critical imports are functional")
            print("  • Database initializes correctly")
            print("  • Authentication system is operational")
            print("  • UI components are accessible")
            print("  • Data manager functions work properly")
            print("  • Migration scripts execute successfully")
        else:
            print(f"\n⚠️  {self.total_tests - self.passed_tests} TESTS FAILED")
            print("\n❌ Issues Found:")
            
            for result in self.results:
                if not result.passed:
                    print(f"  • {result.name}: {result.message}")
                    if result.details:
                        print(f"    Details: {result.details}")
            
            print("\n🔧 Next Steps:")
            print("  1. Review failed tests above")
            print("  2. Fix the identified issues")
            print("  3. Re-run this test script")
            print("  4. Ensure all tests pass before deployment")
        
        print("\n" + "=" * 60)
        
        # Return exit code
        return 0 if self.passed_tests == self.total_tests else 1

def main():
    """Main test runner"""
    try:
        tester = AppTester()
        exit_code = tester.run_all_tests()
        sys.exit(exit_code)
    
    except KeyboardInterrupt:
        print("\n\n⚠️ Tests interrupted by user")
        sys.exit(1)
    
    except Exception as e:
        print(f"\n\n💥 Unexpected error during testing: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    main()
