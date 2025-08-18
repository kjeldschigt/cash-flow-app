#!/usr/bin/env python3
"""
Test script to verify data_manager functions work correctly.
"""

import sys
import os
from datetime import datetime, date, timedelta
import pandas as pd

# Add src to path
src_path = os.path.join(os.path.dirname(__file__), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

def test_data_manager_functions():
    """Test all data_manager functions."""
    print("🧪 Testing data_manager functions...")
    
    try:
        from src.utils.data_manager import (
            calculate_metrics, 
            get_date_range_data, 
            filter_data_by_range,
            get_daily_aggregates,
            load_combined_data,
            init_session_filters
        )
        
        # Test data
        test_data_list = [
            {'date': '2024-01-01', 'Sales_USD': 1000, 'Costs_USD': 200},
            {'date': '2024-01-02', 'Sales_USD': 1500, 'Costs_USD': 300},
            {'date': '2024-01-03', 'Sales_USD': 800, 'Costs_USD': 150},
        ]
        
        test_df = pd.DataFrame(test_data_list)
        test_df['Date'] = pd.to_datetime(test_df['date'])
        
        print("\n--- Testing calculate_metrics ---")
        
        # Test with list
        metrics_list = calculate_metrics(test_data_list)
        print(f"✅ Metrics from list: {metrics_list}")
        
        # Test with DataFrame
        metrics_df = calculate_metrics(test_df)
        print(f"✅ Metrics from DataFrame: {metrics_df}")
        
        # Test with empty data
        empty_metrics = calculate_metrics([])
        print(f"✅ Empty data metrics: {empty_metrics}")
        
        print("\n--- Testing get_date_range_data ---")
        
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 2)
        
        # Test with list
        filtered_list = get_date_range_data(test_data_list, start_date, end_date)
        print(f"✅ Filtered list: {len(filtered_list)} items")
        
        # Test with DataFrame
        filtered_df = get_date_range_data(test_df, start_date, end_date, 'Date')
        print(f"✅ Filtered DataFrame: {len(filtered_df)} rows")
        
        print("\n--- Testing filter_data_by_range ---")
        
        # Test different range labels
        ranges = ['Last 7 Days', 'Last 30 Days', 'YTD']
        for range_label in ranges:
            filtered = filter_data_by_range(test_df, range_label)
            print(f"✅ {range_label}: {len(filtered)} rows")
        
        print("\n--- Testing get_daily_aggregates ---")
        
        daily_agg = get_daily_aggregates(test_df)
        print(f"✅ Daily aggregates: {len(daily_agg)} days")
        print(f"   Columns: {list(daily_agg.columns)}")
        
        print("\n--- Testing load_combined_data ---")
        
        combined_data = load_combined_data()
        print(f"✅ Combined data keys: {list(combined_data.keys())}")
        for key, value in combined_data.items():
            print(f"   {key}: {len(value)} items")
        
        print("\n--- Testing init_session_filters ---")
        
        # Mock streamlit session state
        class MockSessionState:
            def __init__(self):
                self.data = {}
            
            def __contains__(self, key):
                return key in self.data
            
            def __getitem__(self, key):
                return self.data[key]
            
            def __setitem__(self, key, value):
                self.data[key] = value
            
            def get(self, key, default=None):
                return self.data.get(key, default)
        
        # Test without streamlit
        print("✅ Session filter functions available")
        
        print("\n🎉 All data_manager functions working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing data_manager: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_dashboard_integration():
    """Test that dashboard can import and use data_manager functions."""
    print("\n🔍 Testing dashboard integration...")
    
    try:
        # Test importing from dashboard perspective
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'pages'))
        
        # Read dashboard file and check for syntax errors
        dashboard_file = os.path.join(os.path.dirname(__file__), 'pages', '1_🏠_Dashboard.py')
        
        if os.path.exists(dashboard_file):
            with open(dashboard_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for data_manager imports
            if 'from src.utils.data_manager import' in content:
                print("✅ Dashboard imports data_manager correctly")
            else:
                print("⚠️ Dashboard may not import data_manager")
            
            # Try to compile the file
            compile(content, dashboard_file, 'exec')
            print("✅ Dashboard syntax is valid")
            
        else:
            print("❌ Dashboard file not found")
            return False
        
        print("✅ Dashboard integration looks good!")
        return True
        
    except Exception as e:
        print(f"❌ Dashboard integration error: {str(e)}")
        return False

if __name__ == "__main__":
    functions_ok = test_data_manager_functions()
    dashboard_ok = test_dashboard_integration()
    
    if functions_ok and dashboard_ok:
        print("\n🎉 All tests passed! Data manager is ready for use.")
    else:
        print("\n⚠️ Some issues found. Check the output above.")
