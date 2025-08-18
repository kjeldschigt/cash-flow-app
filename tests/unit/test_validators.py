"""
Unit tests for validation functions
"""

import pytest
from datetime import datetime, date
from decimal import Decimal
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from services.validators import (
    validate_amount, validate_date, validate_currency, validate_email,
    validate_category, validate_business_rules, ValidationError
)

class TestAmountValidation:
    """Test amount validation functions"""
    
    def test_validate_amount_positive_float(self):
        """Test validation of positive float amounts"""
        assert validate_amount(100.50) == True
        assert validate_amount(0.01) == True
        assert validate_amount(1000000.99) == True
    
    def test_validate_amount_positive_int(self):
        """Test validation of positive integer amounts"""
        assert validate_amount(100) == True
        assert validate_amount(1) == True
        assert validate_amount(1000000) == True
    
    def test_validate_amount_zero(self):
        """Test validation of zero amount"""
        assert validate_amount(0) == True
        assert validate_amount(0.0) == True
    
    def test_validate_amount_negative(self):
        """Test validation of negative amounts"""
        with pytest.raises(ValidationError, match="Amount must be non-negative"):
            validate_amount(-100)
        with pytest.raises(ValidationError, match="Amount must be non-negative"):
            validate_amount(-0.01)
    
    def test_validate_amount_string_valid(self):
        """Test validation of valid string amounts"""
        assert validate_amount("100.50") == True
        assert validate_amount("1000") == True
        assert validate_amount("0") == True
    
    def test_validate_amount_string_invalid(self):
        """Test validation of invalid string amounts"""
        with pytest.raises(ValidationError, match="Invalid amount format"):
            validate_amount("abc")
        with pytest.raises(ValidationError, match="Invalid amount format"):
            validate_amount("100.50.25")
        with pytest.raises(ValidationError, match="Invalid amount format"):
            validate_amount("")
    
    def test_validate_amount_none(self):
        """Test validation of None amount"""
        with pytest.raises(ValidationError, match="Amount cannot be None"):
            validate_amount(None)
    
    def test_validate_amount_decimal(self):
        """Test validation of Decimal amounts"""
        assert validate_amount(Decimal("100.50")) == True
        assert validate_amount(Decimal("0")) == True
        
        with pytest.raises(ValidationError, match="Amount must be non-negative"):
            validate_amount(Decimal("-100"))
    
    def test_validate_amount_precision(self):
        """Test validation of high precision amounts"""
        # Should handle reasonable precision
        assert validate_amount(100.123456) == True
        
        # Very high precision should be handled
        assert validate_amount(Decimal("100.123456789012345")) == True

class TestDateValidation:
    """Test date validation functions"""
    
    def test_validate_date_datetime_object(self):
        """Test validation of datetime objects"""
        valid_date = datetime(2024, 8, 17)
        assert validate_date(valid_date) == True
    
    def test_validate_date_date_object(self):
        """Test validation of date objects"""
        valid_date = date(2024, 8, 17)
        assert validate_date(valid_date) == True
    
    def test_validate_date_string_valid(self):
        """Test validation of valid date strings"""
        assert validate_date("2024-08-17") == True
        assert validate_date("2024/08/17") == True
        assert validate_date("08/17/2024") == True
        assert validate_date("17-08-2024") == True
    
    def test_validate_date_string_invalid(self):
        """Test validation of invalid date strings"""
        with pytest.raises(ValidationError, match="Invalid date format"):
            validate_date("invalid-date")
        with pytest.raises(ValidationError, match="Invalid date format"):
            validate_date("2024-13-01")  # Invalid month
        with pytest.raises(ValidationError, match="Invalid date format"):
            validate_date("2024-02-30")  # Invalid day
    
    def test_validate_date_future_restriction(self):
        """Test validation with future date restrictions"""
        future_date = datetime(2030, 1, 1)
        
        # Should pass without restriction
        assert validate_date(future_date) == True
        
        # Should fail with future restriction
        with pytest.raises(ValidationError, match="Date cannot be in the future"):
            validate_date(future_date, allow_future=False)
    
    def test_validate_date_none(self):
        """Test validation of None date"""
        with pytest.raises(ValidationError, match="Date cannot be None"):
            validate_date(None)
    
    def test_validate_date_range(self):
        """Test validation with date range restrictions"""
        test_date = date(2024, 8, 17)
        min_date = date(2024, 1, 1)
        max_date = date(2024, 12, 31)
        
        # Should pass within range
        assert validate_date(test_date, min_date=min_date, max_date=max_date) == True
        
        # Should fail outside range
        with pytest.raises(ValidationError, match="Date must be after"):
            validate_date(date(2023, 12, 31), min_date=min_date)
        
        with pytest.raises(ValidationError, match="Date must be before"):
            validate_date(date(2025, 1, 1), max_date=max_date)

class TestCurrencyValidation:
    """Test currency validation functions"""
    
    def test_validate_currency_valid_codes(self):
        """Test validation of valid currency codes"""
        valid_currencies = ["USD", "EUR", "GBP", "JPY", "CAD", "AUD"]
        
        for currency in valid_currencies:
            assert validate_currency(currency) == True
    
    def test_validate_currency_lowercase(self):
        """Test validation of lowercase currency codes"""
        assert validate_currency("usd") == True
        assert validate_currency("eur") == True
    
    def test_validate_currency_invalid_codes(self):
        """Test validation of invalid currency codes"""
        with pytest.raises(ValidationError, match="Invalid currency code"):
            validate_currency("XYZ")
        with pytest.raises(ValidationError, match="Invalid currency code"):
            validate_currency("INVALID")
    
    def test_validate_currency_wrong_length(self):
        """Test validation of wrong length currency codes"""
        with pytest.raises(ValidationError, match="Currency code must be 3 characters"):
            validate_currency("US")
        with pytest.raises(ValidationError, match="Currency code must be 3 characters"):
            validate_currency("USDD")
    
    def test_validate_currency_none_or_empty(self):
        """Test validation of None or empty currency"""
        with pytest.raises(ValidationError, match="Currency code cannot be None or empty"):
            validate_currency(None)
        with pytest.raises(ValidationError, match="Currency code cannot be None or empty"):
            validate_currency("")
        with pytest.raises(ValidationError, match="Currency code cannot be None or empty"):
            validate_currency("   ")

class TestEmailValidation:
    """Test email validation functions"""
    
    def test_validate_email_valid(self):
        """Test validation of valid email addresses"""
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "user+tag@example.org",
            "user123@test-domain.com"
        ]
        
        for email in valid_emails:
            assert validate_email(email) == True
    
    def test_validate_email_invalid_format(self):
        """Test validation of invalid email formats"""
        invalid_emails = [
            "invalid-email",
            "@example.com",
            "user@",
            "user@.com",
            "user..name@example.com",
            "user@example",
            ""
        ]
        
        for email in invalid_emails:
            with pytest.raises(ValidationError, match="Invalid email format"):
                validate_email(email)
    
    def test_validate_email_none(self):
        """Test validation of None email"""
        with pytest.raises(ValidationError, match="Email cannot be None"):
            validate_email(None)
    
    def test_validate_email_case_insensitive(self):
        """Test email validation is case insensitive"""
        assert validate_email("Test@Example.COM") == True
        assert validate_email("USER@domain.org") == True

class TestCategoryValidation:
    """Test category validation functions"""
    
    def test_validate_category_valid(self):
        """Test validation of valid categories"""
        valid_categories = [
            "Operating",
            "Marketing", 
            "Personnel",
            "Equipment",
            "Travel & Entertainment"
        ]
        
        for category in valid_categories:
            assert validate_category(category) == True
    
    def test_validate_category_custom(self):
        """Test validation with custom allowed categories"""
        allowed_categories = ["Custom1", "Custom2", "Custom3"]
        
        assert validate_category("Custom1", allowed_categories) == True
        
        with pytest.raises(ValidationError, match="Invalid category"):
            validate_category("Invalid", allowed_categories)
    
    def test_validate_category_empty_or_none(self):
        """Test validation of empty or None category"""
        with pytest.raises(ValidationError, match="Category cannot be None or empty"):
            validate_category(None)
        with pytest.raises(ValidationError, match="Category cannot be None or empty"):
            validate_category("")
        with pytest.raises(ValidationError, match="Category cannot be None or empty"):
            validate_category("   ")
    
    def test_validate_category_length(self):
        """Test validation of category length"""
        # Very long category should fail
        long_category = "A" * 101  # Assuming 100 char limit
        with pytest.raises(ValidationError, match="Category name too long"):
            validate_category(long_category)

class TestBusinessRulesValidation:
    """Test business rule validation functions"""
    
    def test_validate_business_rules_cost_entry(self):
        """Test business rules for cost entries"""
        valid_cost = {
            'amount': 100.50,
            'category': 'Operating',
            'date': date.today(),
            'currency': 'USD'
        }
        
        assert validate_business_rules(valid_cost, 'cost') == True
    
    def test_validate_business_rules_revenue_entry(self):
        """Test business rules for revenue entries"""
        valid_revenue = {
            'amount': 1000.00,
            'category': 'Sales',
            'date': date.today(),
            'currency': 'USD'
        }
        
        assert validate_business_rules(valid_revenue, 'revenue') == True
    
    def test_validate_business_rules_amount_limits(self):
        """Test business rules for amount limits"""
        # Very large amount should trigger validation
        large_amount_entry = {
            'amount': 1000000.00,  # 1 million
            'category': 'Operating',
            'date': date.today(),
            'currency': 'USD'
        }
        
        with pytest.raises(ValidationError, match="Amount exceeds maximum allowed"):
            validate_business_rules(large_amount_entry, 'cost', max_amount=500000)
    
    def test_validate_business_rules_date_restrictions(self):
        """Test business rules for date restrictions"""
        future_entry = {
            'amount': 100.00,
            'category': 'Operating',
            'date': date(2030, 1, 1),
            'currency': 'USD'
        }
        
        with pytest.raises(ValidationError, match="Future dates not allowed"):
            validate_business_rules(future_entry, 'cost', allow_future_dates=False)
    
    def test_validate_business_rules_required_fields(self):
        """Test business rules for required fields"""
        incomplete_entry = {
            'amount': 100.00,
            'category': 'Operating'
            # Missing date and currency
        }
        
        required_fields = ['amount', 'category', 'date', 'currency']
        
        with pytest.raises(ValidationError, match="Missing required field"):
            validate_business_rules(incomplete_entry, 'cost', required_fields=required_fields)
    
    def test_validate_business_rules_category_restrictions(self):
        """Test business rules for category restrictions"""
        entry_with_invalid_category = {
            'amount': 100.00,
            'category': 'InvalidCategory',
            'date': date.today(),
            'currency': 'USD'
        }
        
        allowed_categories = ['Operating', 'Marketing', 'Personnel']
        
        with pytest.raises(ValidationError, match="Category not allowed"):
            validate_business_rules(
                entry_with_invalid_category, 
                'cost', 
                allowed_categories=allowed_categories
            )

class TestValidationErrorHandling:
    """Test validation error handling and edge cases"""
    
    def test_validation_error_message(self):
        """Test ValidationError message formatting"""
        try:
            validate_amount(-100)
        except ValidationError as e:
            assert "Amount must be non-negative" in str(e)
            assert hasattr(e, 'field')
            assert hasattr(e, 'value')
    
    def test_validation_error_chaining(self):
        """Test validation error chaining"""
        def complex_validation(data):
            validate_amount(data.get('amount'))
            validate_date(data.get('date'))
            validate_currency(data.get('currency'))
        
        invalid_data = {
            'amount': -100,
            'date': 'invalid-date',
            'currency': 'XYZ'
        }
        
        # Should fail on first validation
        with pytest.raises(ValidationError):
            complex_validation(invalid_data)
    
    def test_validation_with_custom_messages(self):
        """Test validation with custom error messages"""
        with pytest.raises(ValidationError, match="Custom error message"):
            validate_amount(-100, error_message="Custom error message")
    
    def test_validation_performance(self, performance_monitor):
        """Test validation performance"""
        performance_monitor.start()
        
        # Perform many validations
        for i in range(10000):
            validate_amount(100 + i)
            validate_currency("USD")
            validate_date(date.today())
        
        performance_monitor.assert_max_duration(1.0)

class TestValidationIntegration:
    """Integration tests for validation functions"""
    
    def test_complete_entry_validation(self):
        """Test validation of complete financial entry"""
        complete_entry = {
            'amount': 1500.75,
            'category': 'Marketing',
            'date': date(2024, 8, 17),
            'currency': 'USD',
            'description': 'Marketing campaign expense',
            'subcategory': 'Digital Advertising'
        }
        
        # Validate all fields
        validate_amount(complete_entry['amount'])
        validate_category(complete_entry['category'])
        validate_date(complete_entry['date'])
        validate_currency(complete_entry['currency'])
        
        # Should pass business rules
        assert validate_business_rules(complete_entry, 'cost') == True
    
    def test_batch_validation(self):
        """Test validation of multiple entries"""
        entries = [
            {'amount': 100, 'category': 'Operating', 'date': date.today(), 'currency': 'USD'},
            {'amount': 200, 'category': 'Marketing', 'date': date.today(), 'currency': 'EUR'},
            {'amount': 300, 'category': 'Personnel', 'date': date.today(), 'currency': 'GBP'}
        ]
        
        for entry in entries:
            validate_amount(entry['amount'])
            validate_category(entry['category'])
            validate_date(entry['date'])
            validate_currency(entry['currency'])
            assert validate_business_rules(entry, 'cost') == True
    
    def test_validation_with_data_transformation(self):
        """Test validation with data transformation"""
        raw_entry = {
            'amount': '1,500.75',  # String with comma
            'category': ' Marketing ',  # With whitespace
            'date': '2024-08-17',  # String date
            'currency': 'usd'  # Lowercase
        }
        
        # Transform and validate
        transformed_amount = float(raw_entry['amount'].replace(',', ''))
        transformed_category = raw_entry['category'].strip()
        transformed_currency = raw_entry['currency'].upper()
        
        validate_amount(transformed_amount)
        validate_category(transformed_category)
        validate_date(raw_entry['date'])
        validate_currency(transformed_currency)
