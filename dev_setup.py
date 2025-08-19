#!/usr/bin/env python3
"""
Development setup script to initialize database and sample data.
"""

import os
import sys
from datetime import date

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def setup_dev_database():
    """Initialize development database with sample data."""
    
    # Step 1: Initialize database
    print("Initializing database...")
    try:
        from src.utils.db_init import initialize_database
        initialize_database()
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False
    
    # Step 2: Insert sample cost data
    print("Inserting sample cost data...")
    try:
        from src.container import get_container
        from src.models.cost import CostCategory
        from decimal import Decimal
        
        container = get_container()
        cost_service = container.get_cost_service()
        
        # Insert example costs
        cost_service.create_cost(
            date=date.today(),
            category=CostCategory.CLOUD,
            amount_usd=Decimal("199.00"),
            description="Monthly AWS usage"
        )
        
        cost_service.create_cost(
            date=date.today(),
            category=CostCategory.SOFTWARE,
            amount_usd=Decimal("25.00"),
            description="GitHub subscription"
        )
        
        cost_service.create_cost(
            date=date.today(),
            category=CostCategory.OFFICE,
            amount_usd=Decimal("150.00"),
            description="Office supplies"
        )
        
        print("✅ Sample cost data inserted successfully")
        
    except Exception as e:
        print(f"❌ Sample data insertion failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = setup_dev_database()
    if success:
        print("\n🎉 Development setup completed successfully!")
        print("You can now run: streamlit run app.py")
    else:
        print("\n❌ Development setup failed")
        sys.exit(1)
