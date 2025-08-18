"""
Unit tests for Pydantic models
"""

import pytest
from datetime import datetime, date
from decimal import Decimal
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from models.cost import Cost
from models.user import User, UserRole
from models.integration import Integration, IntegrationType, IntegrationStatus
from models.analytics import FinancialMetrics, CashFlowData
from pydantic import ValidationError

class TestCostModel:
    """Test Cost model validation and serialization"""
    
    def test_cost_model_valid(self):
        """Test valid cost model creation"""
        cost = Cost(
            id=1,
            date=date.today(),
            amount=Decimal('100.50'),
            category='Operating',
            subcategory='Office Supplies',
            description='Test cost',
            currency='USD'
        )
        
        assert cost.id == 1
        assert cost.amount == Decimal('100.50')
        assert cost.category == 'Operating'
        assert cost.currency == 'USD'
    
    def test_cost_model_required_fields(self):
        """Test cost model with missing required fields"""
        with pytest.raises(ValidationError):
            Cost()  # Missing required fields
    
    def test_cost_model_amount_validation(self):
        """Test cost model amount validation"""
        with pytest.raises(ValidationError, match="ensure this value is greater than or equal to 0"):
            Cost(
                date=date.today(),
                amount=Decimal('-100'),  # Negative amount
                category='Operating',
                currency='USD'
            )
    
    def test_cost_model_currency_validation(self):
        """Test cost model currency validation"""
        # Valid currency should work
        cost = Cost(
            date=date.today(),
            amount=Decimal('100'),
            category='Operating',
            currency='USD'
        )
        assert cost.currency == 'USD'
        
        # Invalid currency length should fail
        with pytest.raises(ValidationError):
            Cost(
                date=date.today(),
                amount=Decimal('100'),
                category='Operating',
                currency='INVALID'  # Too long
            )
    
    def test_cost_model_serialization(self):
        """Test cost model serialization"""
        cost = Cost(
            id=1,
            date=date(2024, 8, 17),
            amount=Decimal('100.50'),
            category='Operating',
            currency='USD'
        )
        
        # Test dict conversion
        cost_dict = cost.dict()
        assert cost_dict['amount'] == Decimal('100.50')
        assert cost_dict['date'] == date(2024, 8, 17)
        
        # Test JSON serialization
        cost_json = cost.json()
        assert '"amount": 100.5' in cost_json
        assert '"currency": "USD"' in cost_json
    
    def test_cost_model_deserialization(self):
        """Test cost model deserialization"""
        cost_data = {
            'id': 1,
            'date': '2024-08-17',
            'amount': '100.50',
            'category': 'Operating',
            'currency': 'USD'
        }
        
        cost = Cost(**cost_data)
        assert cost.amount == Decimal('100.50')
        assert cost.date == date(2024, 8, 17)

class TestUserModel:
    """Test User model validation and serialization"""
    
    def test_user_model_valid(self):
        """Test valid user model creation"""
        user = User(
            id=1,
            email='test@example.com',
            role=UserRole.ADMIN,
            created_at=datetime.now()
        )
        
        assert user.id == 1
        assert user.email == 'test@example.com'
        assert user.role == UserRole.ADMIN
    
    def test_user_model_email_validation(self):
        """Test user model email validation"""
        # Valid email
        user = User(
            email='test@example.com',
            role=UserRole.USER,
            created_at=datetime.now()
        )
        assert user.email == 'test@example.com'
        
        # Invalid email should fail
        with pytest.raises(ValidationError, match="value is not a valid email address"):
            User(
                email='invalid-email',
                role=UserRole.USER,
                created_at=datetime.now()
            )
    
    def test_user_model_role_validation(self):
        """Test user model role validation"""
        # Valid roles
        for role in UserRole:
            user = User(
                email='test@example.com',
                role=role,
                created_at=datetime.now()
            )
            assert user.role == role
        
        # Invalid role should fail
        with pytest.raises(ValidationError):
            User(
                email='test@example.com',
                role='INVALID_ROLE',
                created_at=datetime.now()
            )
    
    def test_user_model_password_handling(self):
        """Test user model password handling"""
        # Password should not be included in serialization
        user = User(
            email='test@example.com',
            role=UserRole.USER,
            created_at=datetime.now()
        )
        
        user_dict = user.dict()
        assert 'password' not in user_dict
        
        user_json = user.json()
        assert 'password' not in user_json

class TestIntegrationModel:
    """Test Integration model validation and serialization"""
    
    def test_integration_model_valid(self):
        """Test valid integration model creation"""
        integration = Integration(
            id='int_123',
            name='Stripe Integration',
            type=IntegrationType.STRIPE,
            is_enabled=True,
            config={'api_key': 'sk_test_123'},
            events=['payment.succeeded'],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            last_sync=None
        )
        
        assert integration.name == 'Stripe Integration'
        assert integration.type == IntegrationType.STRIPE
        assert integration.is_enabled == True
    
    def test_integration_model_type_validation(self):
        """Test integration model type validation"""
        # Valid types
        for integration_type in IntegrationType:
            integration = Integration(
                name='Test Integration',
                type=integration_type,
                is_enabled=True,
                config={},
                events=[],
                created_at=datetime.now(),
                updated_at=datetime.now(),
                last_sync=None
            )
            assert integration.type == integration_type
    
    def test_integration_model_config_validation(self):
        """Test integration model config validation"""
        integration = Integration(
            name='Test Integration',
            type=IntegrationType.STRIPE,
            is_enabled=True,
            config={'api_key': 'test_key', 'webhook_url': 'https://example.com'},
            events=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            last_sync=None
        )
        
        assert integration.config['api_key'] == 'test_key'
        assert integration.config['webhook_url'] == 'https://example.com'
    
    def test_integration_model_methods(self):
        """Test integration model methods"""
        integration = Integration(
            name='Test Integration',
            type=IntegrationType.STRIPE,
            is_enabled=True,
            config={'api_key': 'test_key'},
            events=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            last_sync=None
        )
        
        # Test enable/disable
        integration.disable()
        assert integration.is_enabled == False
        
        integration.enable()
        assert integration.is_enabled == True
        
        # Test config update
        integration.update_config({'new_key': 'new_value'})
        assert integration.config['new_key'] == 'new_value'
        
        # Test API key retrieval
        assert integration.get_api_key() == 'test_key'
        
        # Test configuration check
        assert integration.is_configured() == True

class TestAnalyticsModels:
    """Test Analytics model validation and serialization"""
    
    def test_financial_metrics_model(self):
        """Test FinancialMetrics model"""
        metrics = FinancialMetrics(
            total_revenue=Decimal('100000'),
            total_costs=Decimal('75000'),
            net_profit=Decimal('25000'),
            profit_margin=Decimal('25.0'),
            period_start=date(2024, 1, 1),
            period_end=date(2024, 8, 17),
            currency='USD'
        )
        
        assert metrics.total_revenue == Decimal('100000')
        assert metrics.net_profit == Decimal('25000')
        assert metrics.profit_margin == Decimal('25.0')
        assert metrics.currency == 'USD'
    
    def test_cash_flow_data_model(self):
        """Test CashFlowData model"""
        cash_flow = CashFlowData(
            date=date(2024, 8, 17),
            inflow=Decimal('5000'),
            outflow=Decimal('3000'),
            net_flow=Decimal('2000'),
            cumulative_flow=Decimal('10000'),
            currency='USD'
        )
        
        assert cash_flow.inflow == Decimal('5000')
        assert cash_flow.outflow == Decimal('3000')
        assert cash_flow.net_flow == Decimal('2000')
        assert cash_flow.cumulative_flow == Decimal('10000')

class TestModelValidationEdgeCases:
    """Test edge cases and error conditions for models"""
    
    def test_model_with_none_values(self):
        """Test models with None values where allowed"""
        cost = Cost(
            date=date.today(),
            amount=Decimal('100'),
            category='Operating',
            currency='USD',
            subcategory=None,  # Optional field
            description=None   # Optional field
        )
        
        assert cost.subcategory is None
        assert cost.description is None
    
    def test_model_with_empty_strings(self):
        """Test models with empty strings"""
        with pytest.raises(ValidationError):
            Cost(
                date=date.today(),
                amount=Decimal('100'),
                category='',  # Empty string should fail
                currency='USD'
            )
    
    def test_model_with_large_values(self):
        """Test models with very large values"""
        cost = Cost(
            date=date.today(),
            amount=Decimal('999999999.99'),  # Very large amount
            category='Operating',
            currency='USD'
        )
        
        assert cost.amount == Decimal('999999999.99')
    
    def test_model_with_precision_values(self):
        """Test models with high precision decimal values"""
        cost = Cost(
            date=date.today(),
            amount=Decimal('100.123456789'),
            category='Operating',
            currency='USD'
        )
        
        assert cost.amount == Decimal('100.123456789')

class TestModelSerialization:
    """Test model serialization and deserialization"""
    
    def test_cost_json_serialization(self):
        """Test Cost model JSON serialization"""
        cost = Cost(
            id=1,
            date=date(2024, 8, 17),
            amount=Decimal('100.50'),
            category='Operating',
            currency='USD'
        )
        
        # Serialize to JSON
        json_str = cost.json()
        assert isinstance(json_str, str)
        assert '"amount": 100.5' in json_str
        
        # Deserialize from JSON
        cost_from_json = Cost.parse_raw(json_str)
        assert cost_from_json.amount == cost.amount
        assert cost_from_json.date == cost.date
    
    def test_user_json_serialization(self):
        """Test User model JSON serialization"""
        user = User(
            id=1,
            email='test@example.com',
            role=UserRole.ADMIN,
            created_at=datetime(2024, 8, 17, 12, 0, 0)
        )
        
        # Serialize to JSON
        json_str = user.json()
        assert isinstance(json_str, str)
        assert '"email": "test@example.com"' in json_str
        
        # Deserialize from JSON
        user_from_json = User.parse_raw(json_str)
        assert user_from_json.email == user.email
        assert user_from_json.role == user.role
    
    def test_model_dict_serialization(self):
        """Test model dictionary serialization"""
        cost = Cost(
            date=date.today(),
            amount=Decimal('100'),
            category='Operating',
            currency='USD'
        )
        
        cost_dict = cost.dict()
        assert isinstance(cost_dict, dict)
        assert cost_dict['amount'] == Decimal('100')
        assert cost_dict['category'] == 'Operating'
        
        # Test with exclude
        cost_dict_excluded = cost.dict(exclude={'id'})
        assert 'id' not in cost_dict_excluded
    
    def test_model_copy(self):
        """Test model copying"""
        original_cost = Cost(
            date=date.today(),
            amount=Decimal('100'),
            category='Operating',
            currency='USD'
        )
        
        # Deep copy
        copied_cost = original_cost.copy(deep=True)
        assert copied_cost.amount == original_cost.amount
        assert copied_cost is not original_cost
        
        # Copy with updates
        updated_cost = original_cost.copy(update={'amount': Decimal('200')})
        assert updated_cost.amount == Decimal('200')
        assert original_cost.amount == Decimal('100')

class TestModelValidators:
    """Test custom validators in models"""
    
    def test_cost_amount_validator(self):
        """Test cost amount custom validator"""
        # Valid amounts
        valid_amounts = [0, 0.01, 100, 999999.99]
        
        for amount in valid_amounts:
            cost = Cost(
                date=date.today(),
                amount=Decimal(str(amount)),
                category='Operating',
                currency='USD'
            )
            assert cost.amount == Decimal(str(amount))
        
        # Invalid amounts
        with pytest.raises(ValidationError):
            Cost(
                date=date.today(),
                amount=Decimal('-1'),  # Negative
                category='Operating',
                currency='USD'
            )
    
    def test_user_email_validator(self):
        """Test user email custom validator"""
        # Valid emails
        valid_emails = [
            'test@example.com',
            'user.name@domain.co.uk',
            'user+tag@example.org'
        ]
        
        for email in valid_emails:
            user = User(
                email=email,
                role=UserRole.USER,
                created_at=datetime.now()
            )
            assert user.email == email
        
        # Invalid emails
        invalid_emails = ['invalid', '@example.com', 'user@']
        
        for email in invalid_emails:
            with pytest.raises(ValidationError):
                User(
                    email=email,
                    role=UserRole.USER,
                    created_at=datetime.now()
                )

@pytest.mark.performance
class TestModelPerformance:
    """Test model performance"""
    
    def test_bulk_model_creation(self, performance_monitor):
        """Test performance of creating many models"""
        performance_monitor.start()
        
        costs = []
        for i in range(1000):
            cost = Cost(
                date=date.today(),
                amount=Decimal(f'{100 + i}'),
                category='Operating',
                currency='USD'
            )
            costs.append(cost)
        
        performance_monitor.assert_max_duration(1.0)
        assert len(costs) == 1000
    
    def test_bulk_serialization(self, performance_monitor):
        """Test performance of serializing many models"""
        costs = [
            Cost(
                date=date.today(),
                amount=Decimal(f'{100 + i}'),
                category='Operating',
                currency='USD'
            )
            for i in range(100)
        ]
        
        performance_monitor.start()
        
        # Serialize all models
        serialized = [cost.json() for cost in costs]
        
        performance_monitor.assert_max_duration(0.5)
        assert len(serialized) == 100
