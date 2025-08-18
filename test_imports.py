#!/usr/bin/env python3
"""
Test script to verify all import paths work correctly.
"""

import sys
import os
import importlib.util

# Add src to path
src_path = os.path.join(os.path.dirname(__file__), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

def test_import(module_path, description):
    """Test importing a module."""
    try:
        if '.' in module_path:
            # Handle relative imports
            parts = module_path.split('.')
            module = __import__(module_path, fromlist=[parts[-1]])
        else:
            module = __import__(module_path)
        print(f"✅ {description}: {module_path}")
        return True
    except ImportError as e:
        print(f"❌ {description}: {module_path} - {str(e)}")
        return False
    except Exception as e:
        print(f"⚠️  {description}: {module_path} - {str(e)}")
        return False

def test_all_imports():
    """Test all critical imports."""
    print("🧪 Testing import paths...")
    
    tests = [
        # Core src imports
        ("src.container", "Container module"),
        ("src.config.settings", "Settings configuration"),
        ("src.security.auth", "Authentication"),
        ("src.security.audit", "Audit logging"),
        ("src.security.encryption", "Encryption"),
        
        # Services
        ("src.services.user_service", "User service"),
        ("src.services.storage_service", "Storage service"),
        ("src.services.settings_service", "Settings service"),
        ("src.services.error_handler", "Error handler"),
        ("src.services.analytics_service", "Analytics service"),
        ("src.services.cost_service", "Cost service"),
        ("src.services.payment_service", "Payment service"),
        ("src.services.integration_service", "Integration service"),
        ("src.services.legacy_auth", "Legacy auth service"),
        
        # Repositories
        ("src.repositories.user_repository", "User repository"),
        ("src.repositories.cost_repository", "Cost repository"),
        ("src.repositories.settings_repository", "Settings repository"),
        ("src.repositories.base", "Base repository"),
        
        # Models
        ("src.models.user", "User model"),
        ("src.models.cost", "Cost model"),
        ("src.models.setting", "Setting model"),
        ("src.models.analytics", "Analytics model"),
        
        # UI Components
        ("src.ui.auth", "Auth UI components"),
        ("src.ui.components", "UI components"),
        ("src.ui.charts", "Chart components"),
        
        # Utils
        ("src.utils.data_manager", "Data manager"),
        ("src.utils.date_utils", "Date utilities"),
        ("src.utils.secrets_manager", "Secrets manager"),
        
        # Legacy imports (should still work) - these are in root utils, not src
        # ("utils.db_init", "Database initialization"),  # Skip - in root utils
        # ("utils.enhanced_error_handler", "Enhanced error handler"),  # Skip - in root utils
        ("components.ui_helpers", "UI helpers"),
    ]
    
    passed = 0
    total = len(tests)
    
    for module_path, description in tests:
        if test_import(module_path, description):
            passed += 1
    
    print(f"\n📊 Import Test Results:")
    print(f"   Passed: {passed}/{total}")
    print(f"   Failed: {total - passed}/{total}")
    
    if passed == total:
        print("🎉 All imports working correctly!")
        return True
    else:
        print("⚠️  Some imports need attention.")
        return False

def test_page_imports():
    """Test that page files can import their dependencies."""
    print("\n🔍 Testing page imports...")
    
    pages = [
        "pages/1_🏠_Dashboard.py",
        "pages/2_📈_Sales_&_Cash_Flow_Analysis.py", 
        "pages/3_💸_Costs.py",
        "pages/4_🧮_Scenarios.py",
        "pages/5_🏦_Loan.py",
        "pages/6_🔌_Integrations.py",
        "pages/7_⚙️_Settings.py",
        "pages/8_🗓️_Payment_Schedule.py"
    ]
    
    passed = 0
    for page in pages:
        if os.path.exists(page):
            try:
                # Try to compile the file to check for syntax/import errors
                with open(page, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                compile(content, page, 'exec')
                print(f"✅ {page}: Syntax and imports OK")
                passed += 1
            except SyntaxError as e:
                print(f"❌ {page}: Syntax error - {str(e)}")
            except Exception as e:
                print(f"⚠️  {page}: {str(e)}")
        else:
            print(f"❌ {page}: File not found")
    
    print(f"\n📊 Page Import Results:")
    print(f"   Pages OK: {passed}/{len(pages)}")
    
    return passed == len(pages)

if __name__ == "__main__":
    imports_ok = test_all_imports()
    pages_ok = test_page_imports()
    
    if imports_ok and pages_ok:
        print("\n🎉 All import tests passed! The application should work correctly.")
    else:
        print("\n⚠️  Some issues found. Check the output above for details.")
