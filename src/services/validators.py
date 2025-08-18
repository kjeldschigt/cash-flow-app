"""
Validation functions for financial data and business rules
"""

import re
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Union
import logging

logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Custom exception for validation errors"""
    
    def __init__(self, message: str, field: str = None, value: Any = None):
        super().__init__(message)
        self.field = field
        self.value = value
        self.message = message

def validate_amount(
    amount: Union[int, float, str, Decimal], 
    error_message: str = None
) -> bool:
    """
    Validate financial amount
    
    Args:
        amount: Amount to validate
        error_message: Custom error message
        
    Returns:
        True if valid
        
    Raises:
        ValidationError: If amount is invalid
    """
    if amount is None:
        raise ValidationError("Amount cannot be None", "amount", amount)
    
    try:
        # Convert to float for validation
        if isinstance(amount, str):
            # Remove commas and whitespace
            cleaned_amount = amount.replace(',', '').strip()
            if not cleaned_amount:
                raise ValidationError("Invalid amount format", "amount", amount)
            numeric_amount = float(cleaned_amount)
        elif isinstance(amount, Decimal):
            numeric_amount = float(amount)
        else:
            numeric_amount = float(amount)
        
        if numeric_amount < 0:
            message = error_message or "Amount must be non-negative"
            raise ValidationError(message, "amount", amount)
        
        return True
        
    except (ValueError, InvalidOperation):
        raise ValidationError("Invalid amount format", "amount", amount)

def validate_date(
    date_value: Union[datetime, date, str],
    allow_future: bool = True,
    min_date: date = None,
    max_date: date = None
) -> bool:
    """
    Validate date value
    
    Args:
        date_value: Date to validate
        allow_future: Whether future dates are allowed
        min_date: Minimum allowed date
        max_date: Maximum allowed date
        
    Returns:
        True if valid
        
    Raises:
        ValidationError: If date is invalid
    """
    if date_value is None:
        raise ValidationError("Date cannot be None", "date", date_value)
    
    # Convert to date object
    if isinstance(date_value, str):
        try:
            # Try multiple date formats
            date_formats = [
                '%Y-%m-%d',
                '%Y/%m/%d', 
                '%m/%d/%Y',
                '%d-%m-%Y',
                '%d/%m/%Y'
            ]
            
            parsed_date = None
            for fmt in date_formats:
                try:
                    parsed_date = datetime.strptime(date_value, fmt).date()
                    break
                except ValueError:
                    continue
            
            if parsed_date is None:
                raise ValidationError("Invalid date format", "date", date_value)
            
            date_obj = parsed_date
            
        except ValueError:
            raise ValidationError("Invalid date format", "date", date_value)
    
    elif isinstance(date_value, datetime):
        date_obj = date_value.date()
    elif isinstance(date_value, date):
        date_obj = date_value
    else:
        raise ValidationError("Invalid date type", "date", date_value)
    
    # Check future date restriction
    if not allow_future and date_obj > date.today():
        raise ValidationError("Date cannot be in the future", "date", date_value)
    
    # Check date range
    if min_date and date_obj < min_date:
        raise ValidationError(f"Date must be after {min_date}", "date", date_value)
    
    if max_date and date_obj > max_date:
        raise ValidationError(f"Date must be before {max_date}", "date", date_value)
    
    return True

def validate_currency(currency_code: str) -> bool:
    """
    Validate currency code
    
    Args:
        currency_code: Currency code to validate
        
    Returns:
        True if valid
        
    Raises:
        ValidationError: If currency code is invalid
    """
    if currency_code is None or not currency_code or currency_code.strip() == "":
        raise ValidationError("Currency code cannot be None or empty", "currency", currency_code)
    
    # Clean and normalize
    cleaned_code = currency_code.strip().upper()
    
    if len(cleaned_code) != 3:
        raise ValidationError("Currency code must be 3 characters", "currency", currency_code)
    
    # List of valid ISO 4217 currency codes
    valid_currencies = {
        'USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF', 'CNY', 'SEK', 'NZD',
        'MXN', 'SGD', 'HKD', 'NOK', 'TRY', 'ZAR', 'BRL', 'INR', 'KRW', 'PLN',
        'THB', 'IDR', 'HUF', 'CZK', 'ILS', 'CLP', 'PHP', 'AED', 'COP', 'SAR',
        'MYR', 'RON', 'BGN', 'HRK', 'ISK', 'RUB', 'UAH', 'EGP', 'QAR', 'KWD'
    }
    
    if cleaned_code not in valid_currencies:
        raise ValidationError("Invalid currency code", "currency", currency_code)
    
    return True

def validate_email(email: str) -> bool:
    """
    Validate email address
    
    Args:
        email: Email address to validate
        
    Returns:
        True if valid
        
    Raises:
        ValidationError: If email is invalid
    """
    if email is None:
        raise ValidationError("Email cannot be None", "email", email)
    
    # Basic email regex pattern
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(email_pattern, email):
        raise ValidationError("Invalid email format", "email", email)
    
    return True

def validate_category(
    category: str, 
    allowed_categories: List[str] = None
) -> bool:
    """
    Validate category name
    
    Args:
        category: Category to validate
        allowed_categories: List of allowed categories
        
    Returns:
        True if valid
        
    Raises:
        ValidationError: If category is invalid
    """
    if category is None or not category or category.strip() == "":
        raise ValidationError("Category cannot be None or empty", "category", category)
    
    cleaned_category = category.strip()
    
    # Check length
    if len(cleaned_category) > 100:
        raise ValidationError("Category name too long", "category", category)
    
    # Default allowed categories if none provided
    if allowed_categories is None:
        allowed_categories = [
            'Operating', 'Marketing', 'Personnel', 'Equipment', 'Travel & Entertainment',
            'Professional Services', 'Utilities', 'Insurance', 'Rent', 'Office Supplies',
            'Software', 'Hardware', 'Training', 'Legal', 'Accounting', 'Other',
            'Sales', 'Service Revenue', 'Subscriptions', 'Product Sales', 'Consulting'
        ]
    
    if cleaned_category not in allowed_categories:
        raise ValidationError("Invalid category", "category", category)
    
    return True

def validate_business_rules(
    data: Dict[str, Any], 
    entry_type: str,
    max_amount: float = 1000000,
    allow_future_dates: bool = True,
    required_fields: List[str] = None,
    allowed_categories: List[str] = None
) -> bool:
    """
    Validate business rules for financial entries
    
    Args:
        data: Data to validate
        entry_type: Type of entry ('cost', 'revenue', etc.)
        max_amount: Maximum allowed amount
        allow_future_dates: Whether future dates are allowed
        required_fields: List of required fields
        allowed_categories: List of allowed categories
        
    Returns:
        True if valid
        
    Raises:
        ValidationError: If business rules are violated
    """
    # Default required fields
    if required_fields is None:
        required_fields = ['amount', 'category', 'date', 'currency']
    
    # Check required fields
    for field in required_fields:
        if field not in data or data[field] is None:
            raise ValidationError(f"Missing required field: {field}", field, None)
    
    # Validate amount limits
    if 'amount' in data:
        amount = float(data['amount']) if isinstance(data['amount'], str) else data['amount']
        if amount > max_amount:
            raise ValidationError("Amount exceeds maximum allowed", "amount", amount)
    
    # Validate date restrictions
    if 'date' in data and not allow_future_dates:
        date_value = data['date']
        if isinstance(date_value, str):
            date_obj = datetime.strptime(date_value, '%Y-%m-%d').date()
        elif isinstance(date_value, datetime):
            date_obj = date_value.date()
        else:
            date_obj = date_value
        
        if date_obj > date.today():
            raise ValidationError("Future dates not allowed", "date", date_value)
    
    # Validate category restrictions
    if 'category' in data and allowed_categories:
        if data['category'] not in allowed_categories:
            raise ValidationError("Category not allowed", "category", data['category'])
    
    # Entry type specific validations
    if entry_type == 'cost':
        # Cost-specific business rules
        pass
    elif entry_type == 'revenue':
        # Revenue-specific business rules
        pass
    
    return True

def validate_financial_input(value: Any) -> bool:
    """
    General financial input validation
    
    Args:
        value: Value to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        validate_amount(value)
        return True
    except ValidationError:
        return False

def format_currency(amount: float, currency: str = "USD") -> str:
    """
    Format currency amount for display
    
    Args:
        amount: Amount to format
        currency: Currency code
        
    Returns:
        Formatted currency string
    """
    currency_symbols = {
        "USD": "$",
        "EUR": "€", 
        "GBP": "£",
        "JPY": "¥",
        "CAD": "C$",
        "AUD": "A$"
    }
    
    symbol = currency_symbols.get(currency, currency)
    
    if amount < 0:
        return f"-{symbol}{abs(amount):,.2f}"
    else:
        return f"{symbol}{amount:,.2f}"

# Financial calculation functions for the tests
def calculate_profit_margin(revenue: float, costs: float) -> float:
    """Calculate profit margin percentage"""
    if revenue == 0:
        return 0.0
    return ((revenue - costs) / revenue) * 100

def calculate_cash_flow(inflows: List[float], outflows: List[float]) -> float:
    """Calculate net cash flow"""
    total_inflows = sum(inflows) if inflows else 0
    total_outflows = sum(outflows) if outflows else 0
    return total_inflows - total_outflows

def calculate_roi(initial_investment: float, final_value: float) -> float:
    """Calculate return on investment percentage"""
    if initial_investment == 0:
        raise ValueError("Initial investment cannot be zero")
    return ((final_value - initial_investment) / initial_investment) * 100

def calculate_growth_rate(old_value: float, new_value: float, periods: int) -> float:
    """Calculate growth rate percentage"""
    if old_value == 0:
        raise ValueError("Old value cannot be zero")
    if periods == 1:
        return ((new_value - old_value) / old_value) * 100
    else:
        # Compound annual growth rate
        return (((new_value / old_value) ** (1/periods)) - 1) * 100

def convert_currency(
    amount: float, 
    from_currency: str, 
    to_currency: str, 
    exchange_rates: Dict[str, float]
) -> float:
    """Convert currency amount"""
    if from_currency == to_currency:
        return amount
    
    if from_currency not in exchange_rates:
        raise ValueError(f"Exchange rate not found for {from_currency}")
    if to_currency not in exchange_rates:
        raise ValueError(f"Exchange rate not found for {to_currency}")
    
    # Convert to base currency (usually USD) then to target currency
    base_amount = amount / exchange_rates[from_currency]
    return base_amount * exchange_rates[to_currency]

def calculate_compound_interest(
    principal: float, 
    rate: float, 
    periods: int, 
    compounding_frequency: int = 1
) -> float:
    """Calculate compound interest"""
    return principal * (1 + rate/compounding_frequency) ** (compounding_frequency * periods)

def calculate_present_value(future_value: float, discount_rate: float, periods: int) -> float:
    """Calculate present value"""
    return future_value / (1 + discount_rate) ** periods

def calculate_future_value(present_value: float, interest_rate: float, periods: int) -> float:
    """Calculate future value"""
    return present_value * (1 + interest_rate) ** periods

def calculate_break_even(
    fixed_costs: float, 
    variable_cost_per_unit: float, 
    price_per_unit: float
) -> float:
    """Calculate break-even point in units"""
    if price_per_unit <= variable_cost_per_unit:
        raise ValueError("Price per unit must be greater than variable cost per unit")
    
    return fixed_costs / (price_per_unit - variable_cost_per_unit)
