"""
Validation utility functions.
"""

import re
from decimal import Decimal
from datetime import date, datetime
from typing import Any, Optional, List, Dict
from email_validator import validate_email, EmailNotValidError


class ValidationUtils:
    """Utility functions for data validation."""
    
    @staticmethod
    def validate_email_address(email: str) -> tuple[bool, Optional[str]]:
        """Validate email address format."""
        try:
            validate_email(email)
            return True, None
        except EmailNotValidError as e:
            return False, str(e)
    
    @staticmethod
    def validate_password_strength(password: str) -> tuple[bool, List[str]]:
        """Validate password strength and return issues."""
        issues = []
        
        if len(password) < 8:
            issues.append("Password must be at least 8 characters long")
        
        if not re.search(r'[A-Z]', password):
            issues.append("Password must contain at least one uppercase letter")
        
        if not re.search(r'[a-z]', password):
            issues.append("Password must contain at least one lowercase letter")
        
        if not re.search(r'\d', password):
            issues.append("Password must contain at least one number")
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            issues.append("Password must contain at least one special character")
        
        return len(issues) == 0, issues
    
    @staticmethod
    def validate_amount(amount: Any) -> tuple[bool, Optional[str]]:
        """Validate monetary amount."""
        try:
            if amount is None:
                return False, "Amount cannot be empty"
            
            decimal_amount = Decimal(str(amount))
            
            if decimal_amount < 0:
                return False, "Amount cannot be negative"
            
            if decimal_amount > Decimal('999999999.99'):
                return False, "Amount is too large"
            
            return True, None
        except (ValueError, TypeError):
            return False, "Invalid amount format"
    
    @staticmethod
    def validate_date_range(start_date: date, end_date: date) -> tuple[bool, Optional[str]]:
        """Validate date range."""
        if start_date > end_date:
            return False, "Start date must be before end date"
        
        # Check if range is reasonable (not more than 10 years)
        if (end_date - start_date).days > 3650:
            return False, "Date range cannot exceed 10 years"
        
        return True, None
    
    @staticmethod
    def validate_currency_code(currency: str) -> tuple[bool, Optional[str]]:
        """Validate currency code."""
        if not currency or len(currency) != 3:
            return False, "Currency code must be 3 characters"
        
        if not currency.isalpha():
            return False, "Currency code must contain only letters"
        
        return True, None
    
    @staticmethod
    def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> tuple[bool, List[str]]:
        """Validate that required fields are present and not empty."""
        missing_fields = []
        
        for field in required_fields:
            value = data.get(field)
            if value is None or (isinstance(value, str) and value.strip() == ''):
                missing_fields.append(field)
        
        return len(missing_fields) == 0, missing_fields
    
    @staticmethod
    def sanitize_string(value: str, max_length: Optional[int] = None) -> str:
        """Sanitize string input."""
        if not isinstance(value, str):
            value = str(value)
        
        # Strip whitespace
        sanitized = value.strip()
        
        # Remove null bytes
        sanitized = sanitized.replace('\x00', '')
        
        # Truncate if max_length specified
        if max_length and len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        return sanitized
    
    @staticmethod
    def validate_integration_config(integration_type: str, config: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate integration configuration."""
        errors = []
        
        if integration_type.lower() == 'stripe':
            if not config.get('api_key'):
                errors.append("Stripe API key is required")
        
        elif integration_type.lower() == 'airtable':
            if not config.get('api_key'):
                errors.append("Airtable API key is required")
            if not config.get('base_id'):
                errors.append("Airtable base ID is required")
        
        elif integration_type.lower() == 'webhook':
            webhook_url = config.get('webhook_url')
            if not webhook_url:
                errors.append("Webhook URL is required")
            elif not ValidationUtils.validate_url(webhook_url):
                errors.append("Invalid webhook URL format")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """Validate URL format."""
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        return bool(url_pattern.match(url))
