#!/usr/bin/env python3
"""
Script to fix import paths throughout the application to use the new src structure.
"""

import os
import re
import glob

# Mapping of old imports to new imports
IMPORT_MAPPINGS = {
    # Services mappings
    'from services.storage import': 'from src.services.storage_service import',
    'from services.auth import': 'from src.security.auth import',
    'from services.settings_manager import': 'from src.services.settings_service import',
    'from services.airtable import': 'from src.services.integration_service import',
    'from services.stripe import': 'from src.services.payment_service import',
    'from services.fx import': 'from src.services.fx_service import',
    'from services.loan import': 'from src.services.loan_service import',
    
    # Utils mappings
    'from utils.data_manager import': 'from src.utils.data_manager import',
    'from utils.error_handler import': 'from src.services.error_handler import',
    'from utils.enhanced_error_handler import': 'from src.services.error_handler import',
    'from utils.db_init import': 'from utils.db_init import',  # Keep in root utils
    'from utils.theme_manager import': 'from utils.theme_manager import',  # Keep in root utils
    
    # Components mappings
    'from components.ui_helpers import': 'from components.ui_helpers import',  # Keep in root components
    'from components.dashboard_charts import': 'from components.dashboard_charts import',
    'from components.dashboard_metrics import': 'from components.dashboard_metrics import',
    'from components.dashboard_comparisons import': 'from components.dashboard_comparisons import',
    'from components.cost_entry import': 'from components.cost_entry import',
    
    # Src imports that need fixing
    'from src.services.error_handler import get_error_handler': 'from src.services.error_handler import ErrorHandler',
    'from src.container import get_container': 'from src.container import get_container',
    'from src.ui.auth import AuthComponents': 'from src.ui.auth import AuthComponents',
    'from src.ui.components import UIComponents': 'from src.ui.components import UIComponents',
}

# Function name mappings
FUNCTION_MAPPINGS = {
    'get_costs': 'get_costs',
    'get_sales_orders': 'get_sales_orders', 
    'get_fx_rates': 'get_fx_rates',
    'get_loan_payments': 'get_loan_payments',
    'require_auth': 'require_authentication',
    'handle_error': 'handle_error',
    'get_error_handler': 'ErrorHandler',
    'get_setting': 'get_setting',
}

def fix_file_imports(file_path):
    """Fix imports in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Apply import mappings
        for old_import, new_import in IMPORT_MAPPINGS.items():
            content = content.replace(old_import, new_import)
        
        # Fix sys.path additions to be more consistent
        if 'sys.path.insert(0, os.path.join(os.path.dirname(__file__), \'..\', \'src\'))' in content:
            content = content.replace(
                'sys.path.insert(0, os.path.join(os.path.dirname(__file__), \'..\', \'src\'))',
                '''src_path = os.path.join(os.path.dirname(__file__), '..', 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)'''
            )
        
        # Fix relative imports within src
        if '/src/' in file_path:
            # For files within src, use relative imports
            content = re.sub(r'from src\.', 'from .', content)
        
        # Only write if content changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Fixed imports in: {file_path}")
            return True
        else:
            print(f"⚪ No changes needed: {file_path}")
            return False
            
    except Exception as e:
        print(f"❌ Error fixing {file_path}: {e}")
        return False

def fix_all_imports():
    """Fix imports in all Python files."""
    print("🔧 Fixing import paths throughout the application...")
    
    # Directories to process
    directories = [
        'pages/',
        'components/',
        'services/',
        'utils/',
        'src/',
        'tests/',
        'scripts/',
    ]
    
    files_fixed = 0
    total_files = 0
    
    # Process app.py first
    if fix_file_imports('app.py'):
        files_fixed += 1
    total_files += 1
    
    # Process all directories
    for directory in directories:
        if os.path.exists(directory):
            for file_path in glob.glob(f"{directory}/**/*.py", recursive=True):
                total_files += 1
                if fix_file_imports(file_path):
                    files_fixed += 1
    
    print(f"\n📊 Summary:")
    print(f"   Total files processed: {total_files}")
    print(f"   Files with fixes: {files_fixed}")
    print(f"   Files unchanged: {total_files - files_fixed}")

if __name__ == "__main__":
    fix_all_imports()
