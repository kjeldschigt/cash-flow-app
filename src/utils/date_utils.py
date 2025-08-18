"""
Date utility functions.
"""

from datetime import datetime, date, timedelta
from typing import Tuple, Optional
import calendar


class DateUtils:
    """Utility functions for date operations."""
    
    @staticmethod
    def get_month_range(year: int, month: int) -> Tuple[date, date]:
        """Get first and last day of a month."""
        first_day = date(year, month, 1)
        last_day = date(year, month, calendar.monthrange(year, month)[1])
        return first_day, last_day
    
    @staticmethod
    def get_current_month_range() -> Tuple[date, date]:
        """Get first and last day of current month."""
        today = date.today()
        return DateUtils.get_month_range(today.year, today.month)
    
    @staticmethod
    def get_previous_month_range() -> Tuple[date, date]:
        """Get first and last day of previous month."""
        today = date.today()
        if today.month == 1:
            return DateUtils.get_month_range(today.year - 1, 12)
        else:
            return DateUtils.get_month_range(today.year, today.month - 1)
    
    @staticmethod
    def get_quarter_range(year: int, quarter: int) -> Tuple[date, date]:
        """Get first and last day of a quarter."""
        if quarter not in [1, 2, 3, 4]:
            raise ValueError("Quarter must be 1, 2, 3, or 4")
        
        start_month = (quarter - 1) * 3 + 1
        end_month = start_month + 2
        
        first_day = date(year, start_month, 1)
        last_day = date(year, end_month, calendar.monthrange(year, end_month)[1])
        
        return first_day, last_day
    
    @staticmethod
    def get_year_range(year: int) -> Tuple[date, date]:
        """Get first and last day of a year."""
        return date(year, 1, 1), date(year, 12, 31)
    
    @staticmethod
    def add_months(start_date: date, months: int) -> date:
        """Add months to a date."""
        month = start_date.month - 1 + months
        year = start_date.year + month // 12
        month = month % 12 + 1
        day = min(start_date.day, calendar.monthrange(year, month)[1])
        return date(year, month, day)
    
    @staticmethod
    def get_next_recurrence_date(last_date: date, recurrence: str) -> date:
        """Calculate next recurrence date based on recurrence type."""
        recurrence_map = {
            'weekly': timedelta(weeks=1),
            'bi-weekly': timedelta(weeks=2),
            'monthly': None,  # Handle separately
            'every 2 months': None,  # Handle separately
            'quarterly': None,  # Handle separately
            'semiannual': None,  # Handle separately
            'yearly': None  # Handle separately
        }
        
        if recurrence in recurrence_map and recurrence_map[recurrence]:
            return last_date + recurrence_map[recurrence]
        elif recurrence == 'monthly':
            return DateUtils.add_months(last_date, 1)
        elif recurrence == 'every 2 months':
            return DateUtils.add_months(last_date, 2)
        elif recurrence == 'quarterly':
            return DateUtils.add_months(last_date, 3)
        elif recurrence == 'semiannual':
            return DateUtils.add_months(last_date, 6)
        elif recurrence == 'yearly':
            return DateUtils.add_months(last_date, 12)
        else:
            raise ValueError(f"Unknown recurrence type: {recurrence}")
    
    @staticmethod
    def format_date_range(start_date: date, end_date: date) -> str:
        """Format date range for display."""
        if start_date.year == end_date.year:
            if start_date.month == end_date.month:
                return f"{start_date.strftime('%b %d')} - {end_date.strftime('%d, %Y')}"
            else:
                return f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}"
        else:
            return f"{start_date.strftime('%b %d, %Y')} - {end_date.strftime('%b %d, %Y')}"
    
    @staticmethod
    def is_business_day(check_date: date) -> bool:
        """Check if date is a business day (Monday-Friday)."""
        return check_date.weekday() < 5
    
    @staticmethod
    def get_business_days_in_range(start_date: date, end_date: date) -> int:
        """Count business days in date range."""
        count = 0
        current = start_date
        while current <= end_date:
            if DateUtils.is_business_day(current):
                count += 1
            current += timedelta(days=1)
        return count
