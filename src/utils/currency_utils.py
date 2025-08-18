"""
Currency utility functions.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Dict, Any


class CurrencyUtils:
    """Utility functions for currency operations."""
    
    # Common currency symbols
    CURRENCY_SYMBOLS = {
        'USD': '$',
        'CRC': '₡',
        'EUR': '€',
        'GBP': '£',
        'JPY': '¥'
    }
    
    @staticmethod
    def format_amount(amount: Decimal, currency: str = 'USD', show_symbol: bool = True) -> str:
        """Format amount with currency symbol and proper decimal places."""
        if amount is None:
            return "N/A"
        
        # Round to 2 decimal places
        rounded_amount = amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        # Format with commas for thousands
        formatted = f"{rounded_amount:,.2f}"
        
        if show_symbol:
            symbol = CurrencyUtils.CURRENCY_SYMBOLS.get(currency.upper(), currency)
            return f"{symbol}{formatted}"
        
        return formatted
    
    @staticmethod
    def parse_amount(amount_str: str) -> Optional[Decimal]:
        """Parse amount string to Decimal, handling various formats."""
        if not amount_str or amount_str.strip() == '':
            return None
        
        # Remove currency symbols and whitespace
        cleaned = amount_str.strip()
        for symbol in CurrencyUtils.CURRENCY_SYMBOLS.values():
            cleaned = cleaned.replace(symbol, '')
        
        # Remove commas
        cleaned = cleaned.replace(',', '')
        
        try:
            return Decimal(cleaned)
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def convert_currency(
        amount: Decimal, 
        from_currency: str, 
        to_currency: str, 
        exchange_rate: Decimal
    ) -> Decimal:
        """Convert amount from one currency to another."""
        if from_currency.upper() == to_currency.upper():
            return amount
        
        return (amount * exchange_rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def calculate_percentage_change(old_value: Decimal, new_value: Decimal) -> Decimal:
        """Calculate percentage change between two values."""
        if old_value == 0:
            return Decimal('0') if new_value == 0 else Decimal('100')
        
        change = ((new_value - old_value) / old_value) * 100
        return change.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def format_percentage(percentage: Decimal, show_sign: bool = True) -> str:
        """Format percentage for display."""
        rounded = percentage.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        if show_sign and rounded > 0:
            return f"+{rounded}%"
        
        return f"{rounded}%"
    
    @staticmethod
    def sum_amounts(amounts: list[Decimal]) -> Decimal:
        """Sum a list of decimal amounts safely."""
        return sum(amounts, Decimal('0'))
    
    @staticmethod
    def average_amounts(amounts: list[Decimal]) -> Decimal:
        """Calculate average of decimal amounts."""
        if not amounts:
            return Decimal('0')
        
        total = CurrencyUtils.sum_amounts(amounts)
        return (total / len(amounts)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def validate_currency_code(currency: str) -> bool:
        """Validate currency code format (3 letters)."""
        return (
            isinstance(currency, str) and 
            len(currency) == 3 and 
            currency.isalpha()
        )
