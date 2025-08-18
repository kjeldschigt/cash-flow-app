"""
Integration tests for Stripe service with mocked responses
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from datetime import datetime, date
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from src.services.payment_service import StripeService
from models.cost import Cost
from models.user import User, UserRole

@pytest.mark.integration
class TestStripeIntegration:
    """Test Stripe service integration with mocked API responses"""
    
    @pytest.fixture
    def stripe_service(self):
        """Create StripeService instance with test configuration"""
        return StripeService(api_key="sk_test_fake_key")
    
    @pytest.fixture
    def mock_stripe_customer(self):
        """Mock Stripe customer object"""
        customer = Mock()
        customer.id = "cus_test123"
        customer.email = "test@example.com"
        customer.created = 1692288000  # Unix timestamp
        customer.metadata = {}
        return customer
    
    @pytest.fixture
    def mock_stripe_payment_intent(self):
        """Mock Stripe payment intent object"""
        payment_intent = Mock()
        payment_intent.id = "pi_test123"
        payment_intent.amount = 2000  # $20.00 in cents
        payment_intent.currency = "usd"
        payment_intent.status = "succeeded"
        payment_intent.created = 1692288000
        payment_intent.metadata = {"cost_id": "123"}
        return payment_intent
    
    @pytest.fixture
    def mock_stripe_charge(self):
        """Mock Stripe charge object"""
        charge = Mock()
        charge.id = "ch_test123"
        charge.amount = 1500  # $15.00 in cents
        charge.currency = "usd"
        charge.status = "succeeded"
        charge.created = 1692288000
        charge.description = "Test charge"
        charge.metadata = {}
        return charge
    
    def test_create_customer_success(self, stripe_service, mock_stripe_customer):
        """Test successful customer creation"""
        with patch('stripe.Customer.create') as mock_create:
            mock_create.return_value = mock_stripe_customer
            
            customer = stripe_service.create_customer(
                email="test@example.com",
                name="Test User"
            )
            
            assert customer.id == "cus_test123"
            assert customer.email == "test@example.com"
            mock_create.assert_called_once()
    
    def test_create_customer_failure(self, stripe_service):
        """Test customer creation failure"""
        with patch('stripe.Customer.create') as mock_create:
            mock_create.side_effect = Exception("API Error")
            
            with pytest.raises(Exception, match="API Error"):
                stripe_service.create_customer(
                    email="test@example.com",
                    name="Test User"
                )
    
    def test_retrieve_customer_success(self, stripe_service, mock_stripe_customer):
        """Test successful customer retrieval"""
        with patch('stripe.Customer.retrieve') as mock_retrieve:
            mock_retrieve.return_value = mock_stripe_customer
            
            customer = stripe_service.retrieve_customer("cus_test123")
            
            assert customer.id == "cus_test123"
            mock_retrieve.assert_called_once_with("cus_test123")
    
    def test_retrieve_customer_not_found(self, stripe_service):
        """Test customer retrieval when not found"""
        with patch('stripe.Customer.retrieve') as mock_retrieve:
            mock_retrieve.side_effect = Exception("No such customer")
            
            with pytest.raises(Exception, match="No such customer"):
                stripe_service.retrieve_customer("cus_invalid")
    
    def test_create_payment_intent_success(self, stripe_service, mock_stripe_payment_intent):
        """Test successful payment intent creation"""
        with patch('stripe.PaymentIntent.create') as mock_create:
            mock_create.return_value = mock_stripe_payment_intent
            
            payment_intent = stripe_service.create_payment_intent(
                amount=2000,
                currency="usd",
                customer_id="cus_test123"
            )
            
            assert payment_intent.id == "pi_test123"
            assert payment_intent.amount == 2000
            assert payment_intent.currency == "usd"
            mock_create.assert_called_once()
    
    def test_create_payment_intent_with_metadata(self, stripe_service, mock_stripe_payment_intent):
        """Test payment intent creation with metadata"""
        with patch('stripe.PaymentIntent.create') as mock_create:
            mock_create.return_value = mock_stripe_payment_intent
            
            metadata = {"cost_id": "123", "category": "Operating"}
            
            payment_intent = stripe_service.create_payment_intent(
                amount=2000,
                currency="usd",
                customer_id="cus_test123",
                metadata=metadata
            )
            
            # Verify metadata was passed to Stripe
            call_args = mock_create.call_args
            assert call_args[1]['metadata'] == metadata
    
    def test_confirm_payment_intent_success(self, stripe_service, mock_stripe_payment_intent):
        """Test successful payment intent confirmation"""
        mock_stripe_payment_intent.status = "succeeded"
        
        with patch('stripe.PaymentIntent.confirm') as mock_confirm:
            mock_confirm.return_value = mock_stripe_payment_intent
            
            confirmed_intent = stripe_service.confirm_payment_intent("pi_test123")
            
            assert confirmed_intent.status == "succeeded"
            mock_confirm.assert_called_once_with("pi_test123")
    
    def test_list_charges_success(self, stripe_service, mock_stripe_charge):
        """Test successful charges listing"""
        mock_charges_list = Mock()
        mock_charges_list.data = [mock_stripe_charge]
        mock_charges_list.has_more = False
        
        with patch('stripe.Charge.list') as mock_list:
            mock_list.return_value = mock_charges_list
            
            charges = stripe_service.list_charges(limit=10)
            
            assert len(charges.data) == 1
            assert charges.data[0].id == "ch_test123"
            mock_list.assert_called_once()
    
    def test_list_charges_with_filters(self, stripe_service, mock_stripe_charge):
        """Test charges listing with date filters"""
        mock_charges_list = Mock()
        mock_charges_list.data = [mock_stripe_charge]
        
        with patch('stripe.Charge.list') as mock_list:
            mock_list.return_value = mock_charges_list
            
            start_date = datetime(2024, 1, 1)
            end_date = datetime(2024, 8, 17)
            
            charges = stripe_service.list_charges(
                created_after=start_date,
                created_before=end_date,
                customer="cus_test123"
            )
            
            # Verify filters were applied
            call_args = mock_list.call_args[1]
            assert 'created' in call_args
            assert 'customer' in call_args
    
    def test_webhook_validation_success(self, stripe_service):
        """Test successful webhook signature validation"""
        payload = '{"id": "evt_test123", "type": "payment_intent.succeeded"}'
        signature = "t=1692288000,v1=test_signature"
        
        with patch('stripe.Webhook.construct_event') as mock_construct:
            mock_event = Mock()
            mock_event.type = "payment_intent.succeeded"
            mock_construct.return_value = mock_event
            
            event = stripe_service.validate_webhook(payload, signature, "whsec_test")
            
            assert event.type == "payment_intent.succeeded"
            mock_construct.assert_called_once()
    
    def test_webhook_validation_failure(self, stripe_service):
        """Test webhook signature validation failure"""
        payload = '{"id": "evt_test123"}'
        signature = "invalid_signature"
        
        with patch('stripe.Webhook.construct_event') as mock_construct:
            mock_construct.side_effect = ValueError("Invalid signature")
            
            with pytest.raises(ValueError, match="Invalid signature"):
                stripe_service.validate_webhook(payload, signature, "whsec_test")
    
    def test_refund_payment_success(self, stripe_service):
        """Test successful payment refund"""
        mock_refund = Mock()
        mock_refund.id = "re_test123"
        mock_refund.amount = 1000
        mock_refund.status = "succeeded"
        
        with patch('stripe.Refund.create') as mock_create:
            mock_create.return_value = mock_refund
            
            refund = stripe_service.refund_payment("ch_test123", amount=1000)
            
            assert refund.id == "re_test123"
            assert refund.amount == 1000
            mock_create.assert_called_once()
    
    def test_sync_charges_to_costs(self, stripe_service, mock_stripe_charge, populated_test_db):
        """Test syncing Stripe charges to cost entries"""
        mock_charges_list = Mock()
        mock_charges_list.data = [mock_stripe_charge]
        
        with patch('stripe.Charge.list') as mock_list:
            mock_list.return_value = mock_charges_list
            
            # Mock database operations
            with patch('services.storage.add_cost') as mock_add_cost:
                synced_count = stripe_service.sync_charges_to_costs()
                
                assert synced_count == 1
                mock_add_cost.assert_called_once()
    
    def test_create_subscription_success(self, stripe_service):
        """Test successful subscription creation"""
        mock_subscription = Mock()
        mock_subscription.id = "sub_test123"
        mock_subscription.status = "active"
        mock_subscription.current_period_start = 1692288000
        mock_subscription.current_period_end = 1694966400
        
        with patch('stripe.Subscription.create') as mock_create:
            mock_create.return_value = mock_subscription
            
            subscription = stripe_service.create_subscription(
                customer="cus_test123",
                price="price_test123"
            )
            
            assert subscription.id == "sub_test123"
            assert subscription.status == "active"
            mock_create.assert_called_once()
    
    def test_cancel_subscription_success(self, stripe_service):
        """Test successful subscription cancellation"""
        mock_subscription = Mock()
        mock_subscription.id = "sub_test123"
        mock_subscription.status = "canceled"
        
        with patch('stripe.Subscription.delete') as mock_delete:
            mock_delete.return_value = mock_subscription
            
            canceled_sub = stripe_service.cancel_subscription("sub_test123")
            
            assert canceled_sub.status == "canceled"
            mock_delete.assert_called_once_with("sub_test123")

@pytest.mark.integration
class TestStripeWebhookHandling:
    """Test Stripe webhook event handling"""
    
    @pytest.fixture
    def stripe_service(self):
        return StripeService(api_key="sk_test_fake_key")
    
    def test_handle_payment_succeeded_webhook(self, stripe_service):
        """Test handling payment succeeded webhook"""
        mock_event = Mock()
        mock_event.type = "payment_intent.succeeded"
        mock_event.data.object.id = "pi_test123"
        mock_event.data.object.amount = 2000
        mock_event.data.object.currency = "usd"
        mock_event.data.object.metadata = {"cost_id": "123"}
        
        with patch('services.storage.update_cost') as mock_update:
            result = stripe_service.handle_webhook_event(mock_event)
            
            assert result == True
            mock_update.assert_called_once()
    
    def test_handle_payment_failed_webhook(self, stripe_service):
        """Test handling payment failed webhook"""
        mock_event = Mock()
        mock_event.type = "payment_intent.payment_failed"
        mock_event.data.object.id = "pi_test123"
        mock_event.data.object.last_payment_error.message = "Card declined"
        
        with patch('services.storage.update_cost') as mock_update:
            result = stripe_service.handle_webhook_event(mock_event)
            
            assert result == True
            # Should update cost with failed status
            mock_update.assert_called_once()
    
    def test_handle_customer_created_webhook(self, stripe_service):
        """Test handling customer created webhook"""
        mock_event = Mock()
        mock_event.type = "customer.created"
        mock_event.data.object.id = "cus_test123"
        mock_event.data.object.email = "test@example.com"
        
        with patch('services.storage.add_customer') as mock_add:
            result = stripe_service.handle_webhook_event(mock_event)
            
            assert result == True
            mock_add.assert_called_once()
    
    def test_handle_unknown_webhook_type(self, stripe_service):
        """Test handling unknown webhook event type"""
        mock_event = Mock()
        mock_event.type = "unknown.event.type"
        
        result = stripe_service.handle_webhook_event(mock_event)
        
        # Should return False for unknown event types
        assert result == False

@pytest.mark.integration
class TestStripeErrorHandling:
    """Test Stripe service error handling"""
    
    @pytest.fixture
    def stripe_service(self):
        return StripeService(api_key="sk_test_fake_key")
    
    def test_handle_card_declined_error(self, stripe_service):
        """Test handling card declined error"""
        with patch('stripe.PaymentIntent.create') as mock_create:
            mock_create.side_effect = Exception("Your card was declined")
            
            with pytest.raises(Exception, match="Your card was declined"):
                stripe_service.create_payment_intent(
                    amount=2000,
                    currency="usd"
                )
    
    def test_handle_insufficient_funds_error(self, stripe_service):
        """Test handling insufficient funds error"""
        with patch('stripe.PaymentIntent.create') as mock_create:
            mock_create.side_effect = Exception("Insufficient funds")
            
            with pytest.raises(Exception, match="Insufficient funds"):
                stripe_service.create_payment_intent(
                    amount=2000,
                    currency="usd"
                )
    
    def test_handle_api_connection_error(self, stripe_service):
        """Test handling API connection error"""
        with patch('stripe.Customer.create') as mock_create:
            mock_create.side_effect = ConnectionError("Network error")
            
            with pytest.raises(ConnectionError, match="Network error"):
                stripe_service.create_customer(
                    email="test@example.com"
                )
    
    def test_handle_rate_limit_error(self, stripe_service):
        """Test handling rate limit error"""
        with patch('stripe.Charge.list') as mock_list:
            mock_list.side_effect = Exception("Rate limit exceeded")
            
            with pytest.raises(Exception, match="Rate limit exceeded"):
                stripe_service.list_charges()
    
    def test_retry_mechanism(self, stripe_service):
        """Test retry mechanism for transient errors"""
        with patch('stripe.Customer.create') as mock_create:
            # First call fails, second succeeds
            mock_customer = Mock()
            mock_customer.id = "cus_test123"
            mock_create.side_effect = [ConnectionError("Temporary error"), mock_customer]
            
            # Should retry and succeed
            customer = stripe_service.create_customer_with_retry(
                email="test@example.com",
                max_retries=2
            )
            
            assert customer.id == "cus_test123"
            assert mock_create.call_count == 2

@pytest.mark.integration
@pytest.mark.performance
class TestStripePerformance:
    """Test Stripe service performance"""
    
    @pytest.fixture
    def stripe_service(self):
        return StripeService(api_key="sk_test_fake_key")
    
    def test_bulk_customer_creation_performance(self, stripe_service, performance_monitor):
        """Test performance of creating multiple customers"""
        mock_customer = Mock()
        mock_customer.id = "cus_test123"
        
        with patch('stripe.Customer.create') as mock_create:
            mock_create.return_value = mock_customer
            
            performance_monitor.start()
            
            customers = []
            for i in range(100):
                customer = stripe_service.create_customer(
                    email=f"test{i}@example.com"
                )
                customers.append(customer)
            
            performance_monitor.assert_max_duration(2.0)
            assert len(customers) == 100
    
    def test_bulk_charge_listing_performance(self, stripe_service, performance_monitor):
        """Test performance of listing many charges"""
        mock_charges_list = Mock()
        mock_charges_list.data = [Mock() for _ in range(100)]
        mock_charges_list.has_more = False
        
        with patch('stripe.Charge.list') as mock_list:
            mock_list.return_value = mock_charges_list
            
            performance_monitor.start()
            
            charges = stripe_service.list_charges(limit=100)
            
            performance_monitor.assert_max_duration(1.0)
            assert len(charges.data) == 100
