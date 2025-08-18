"""
Analytics and metrics domain models.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional, Dict, Any


@dataclass
class CashFlowMetrics:
    """Cash flow analytics entity."""
    period_start: date
    period_end: date
    total_sales_usd: Decimal
    total_costs_usd: Decimal
    net_cash_flow: Decimal
    avg_daily_sales: Decimal
    avg_transaction_size: Decimal
    transaction_count: int
    sales_growth_rate: Optional[Decimal]
    cost_growth_rate: Optional[Decimal]

    @property
    def profit_margin(self) -> Decimal:
        """Calculate profit margin percentage."""
        if self.total_sales_usd == 0:
            return Decimal('0')
        return (self.net_cash_flow / self.total_sales_usd) * 100

    @property
    def burn_rate(self) -> Decimal:
        """Calculate daily burn rate."""
        days = (self.period_end - self.period_start).days
        if days == 0:
            return self.total_costs_usd
        return self.total_costs_usd / days


@dataclass
class BusinessMetrics:
    """Business performance metrics entity."""
    period_start: date
    period_end: date
    total_leads: int
    mql_count: int
    sql_count: int
    conversion_rate: Decimal
    occupancy_rate: Optional[Decimal]
    customer_acquisition_cost: Optional[Decimal]
    lifetime_value: Optional[Decimal]

    @property
    def mql_rate(self) -> Decimal:
        """Calculate MQL conversion rate."""
        if self.total_leads == 0:
            return Decimal('0')
        return (Decimal(self.mql_count) / Decimal(self.total_leads)) * 100

    @property
    def sql_rate(self) -> Decimal:
        """Calculate SQL conversion rate from MQL."""
        if self.mql_count == 0:
            return Decimal('0')
        return (Decimal(self.sql_count) / Decimal(self.mql_count)) * 100

    @property
    def lead_to_sql_rate(self) -> Decimal:
        """Calculate direct lead to SQL conversion rate."""
        if self.total_leads == 0:
            return Decimal('0')
        return (Decimal(self.sql_count) / Decimal(self.total_leads)) * 100


@dataclass
class FXRateData:
    """Foreign exchange rate data entity."""
    month: str
    low_crc_usd: Decimal
    base_crc_usd: Decimal
    high_crc_usd: Decimal

    def convert_crc_to_usd(self, amount_crc: Decimal, rate_type: str = 'base') -> Decimal:
        """Convert CRC amount to USD using specified rate type."""
        rate_map = {
            'low': self.low_crc_usd,
            'base': self.base_crc_usd,
            'high': self.high_crc_usd
        }
        rate = rate_map.get(rate_type, self.base_crc_usd)
        return amount_crc / rate if rate > 0 else Decimal('0')
