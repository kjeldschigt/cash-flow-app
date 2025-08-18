"""
Foreign exchange service for currency operations.
"""

from datetime import date
from decimal import Decimal
from typing import Optional, Dict, Any
from ..models.analytics import FXRateData
from ..repositories.base import DatabaseConnection
from ..utils.currency_utils import CurrencyUtils


class FXService:
    """Service for foreign exchange operations."""
    
    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection
    
    def get_fx_rate(self, month: str) -> Optional[FXRateData]:
        """Get FX rate data for a specific month."""
        with self.db.get_connection() as conn:
            query = """
                SELECT month, low_crc_usd, base_crc_usd, high_crc_usd
                FROM fx_rates 
                WHERE month = ?
            """
            
            result = conn.execute(query, (month,)).fetchone()
            
            if result:
                return FXRateData(
                    month=result[0],
                    low_crc_usd=Decimal(str(result[1])),
                    base_crc_usd=Decimal(str(result[2])),
                    high_crc_usd=Decimal(str(result[3]))
                )
        
        return None
    
    def convert_crc_to_usd(
        self, 
        amount_crc: Decimal, 
        month: str, 
        rate_type: str = 'base'
    ) -> Decimal:
        """Convert CRC amount to USD using specified rate type."""
        fx_data = self.get_fx_rate(month)
        if not fx_data:
            # Return 0 if no FX data available
            return Decimal('0')
        
        return fx_data.convert_crc_to_usd(amount_crc, rate_type)
    
    def get_current_month_rate(self) -> Optional[FXRateData]:
        """Get FX rate for current month."""
        current_month = date.today().strftime('%Y-%m')
        return self.get_fx_rate(current_month)
    
    def add_fx_rate(
        self,
        month: str,
        low_rate: Decimal,
        base_rate: Decimal,
        high_rate: Decimal
    ) -> bool:
        """Add or update FX rate for a month."""
        with self.db.get_connection() as conn:
            query = """
                INSERT OR REPLACE INTO fx_rates (month, low_crc_usd, base_crc_usd, high_crc_usd)
                VALUES (?, ?, ?, ?)
            """
            
            conn.execute(query, (month, float(low_rate), float(base_rate), float(high_rate)))
            return True


# Legacy compatibility functions
def get_rate_scenarios(month: str = None):
    """Get FX rate scenarios for a given month."""
    return {
        'low': 0.85,
        'base': 0.90,
        'high': 0.95
    }


def get_monthly_rate(month: str = None):
    """Get monthly FX rate."""
    return 0.90
