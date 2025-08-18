"""
Storage service for data retrieval operations.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, date
import pandas as pd
from ..repositories.base import DatabaseConnection

logger = logging.getLogger(__name__)

# Legacy function imports for backward compatibility
def init_db():
    """Initialize database - legacy function for compatibility."""
    try:
        from ..utils.db_init import initialize_database
        return initialize_database()
    except ImportError:
        from utils.db_init import initialize_database
        return initialize_database()

def get_costs(start_date: Optional[date] = None, end_date: Optional[date] = None) -> List[Dict[str, Any]]:
    """Get costs - legacy function for compatibility."""
    from ..repositories.base import DatabaseConnection
    db = DatabaseConnection()
    service = StorageService(db)
    return service.get_costs(start_date, end_date)

def get_sales_orders(start_date: Optional[date] = None, end_date: Optional[date] = None) -> List[Dict[str, Any]]:
    """Get sales orders - legacy function for compatibility."""
    from ..repositories.base import DatabaseConnection
    db = DatabaseConnection()
    service = StorageService(db)
    return service.get_sales_orders(start_date, end_date)

class StorageService:
    """Service for data storage and retrieval operations."""
    
    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection
    
    def get_costs(self, start_date: Optional[date] = None, end_date: Optional[date] = None) -> List[Dict[str, Any]]:
        """Get cost data from database."""
        try:
            with self.db.get_connection() as conn:
                query = "SELECT * FROM costs"
                params = []
                
                if start_date and end_date:
                    query += " WHERE date BETWEEN ? AND ?"
                    params = [start_date.isoformat(), end_date.isoformat()]
                
                df = pd.read_sql_query(query, conn, params=params)
                return df.to_dict('records')
        except Exception as e:
            logger.error(f"Error retrieving costs: {str(e)}")
            return []
    
    def get_sales_orders(self, start_date: Optional[date] = None, end_date: Optional[date] = None) -> List[Dict[str, Any]]:
        """Get sales order data from database."""
        try:
            with self.db.get_connection() as conn:
                query = "SELECT * FROM sales_orders"
                params = []
                
                if start_date and end_date:
                    query += " WHERE order_date BETWEEN ? AND ?"
                    params = [start_date.isoformat(), end_date.isoformat()]
                
                df = pd.read_sql_query(query, conn, params=params)
                return df.to_dict('records')
        except Exception as e:
            logger.error(f"Error retrieving sales orders: {str(e)}")
            return []
    
    def get_fx_rates(self, start_date: Optional[date] = None, end_date: Optional[date] = None) -> List[Dict[str, Any]]:
        """Get FX rates data from database."""
        try:
            with self.db.get_connection() as conn:
                query = "SELECT * FROM fx_rates"
                params = []
                
                if start_date and end_date:
                    query += " WHERE date BETWEEN ? AND ?"
                    params = [start_date.isoformat(), end_date.isoformat()]
                
                df = pd.read_sql_query(query, conn, params=params)
                return df.to_dict('records')
        except Exception as e:
            logger.error(f"Error retrieving FX rates: {str(e)}")
            return []
    
    def get_loan_payments(self, start_date: Optional[date] = None, end_date: Optional[date] = None) -> List[Dict[str, Any]]:
        """Get loan payment data from database."""
        try:
            with self.db.get_connection() as conn:
                query = "SELECT * FROM loan_payments"
                params = []
                
                if start_date and end_date:
                    query += " WHERE payment_date BETWEEN ? AND ?"
                    params = [start_date.isoformat(), end_date.isoformat()]
                
                df = pd.read_sql_query(query, conn, params=params)
                return df.to_dict('records')
        except Exception as e:
            logger.error(f"Error retrieving loan payments: {str(e)}")
            return []
