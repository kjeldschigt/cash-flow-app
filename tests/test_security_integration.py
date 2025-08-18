"""
Security Integration Tests
Tests for authentication, encryption, audit logging, and secrets management
"""

import pytest
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.security.auth import AuthManager, RoleBasedAccessControl
from src.security.encryption import DataEncryption, SecureStorage
from src.security.audit import AuditLogger, AuditAction, AuditLevel
from src.utils.secrets_manager import SecretsManager, SecretProvider
from src.models.user import User, UserRole
from src.repositories.base import DatabaseConnection

class TestAuthenticationSecurity:
    """Test authentication and authorization security"""
    
    @pytest.fixture
    def auth_manager(self):
        """Create test auth manager"""
        from src.config.settings import Settings
        user_service = Mock()
        settings = Settings()
        return AuthManager(user_service, settings)
    
    @pytest.fixture
    def rbac(self):
        """Create test RBAC instance"""
        return RoleBasedAccessControl()
    
    def test_authentication_security(self, auth_manager):
        """Test secure authentication"""
        # Create a test user
        from src.models.user import User
        test_user = User.create(
            email="test@example.com",
            password="TestPassword123!",
            role=UserRole.USER
        )
        
        # Mock the user service to return our test user
        auth_manager.user_service.authenticate_with_identifier.return_value = test_user
        
        # Test successful authentication
        result = auth_manager.authenticate_user("test@example.com", "TestPassword123!")
        assert result is not None
        assert result.email == "test@example.com"
        
        # Test failed authentication
        auth_manager.user_service.authenticate_with_identifier.return_value = None
        result = auth_manager.authenticate_user("test@example.com", "WrongPassword!")
        assert result is None
    
    def test_session_security(self, auth_manager):
        """Test session management security"""
        user = UserModel(
            id="test_user",
            email="test@example.com",
            role=UserRole.USER
        )
        
        # Create session
        session_token = auth_manager.create_session(user)
        
        # Verify session
        assert session_token is not None
        assert len(session_token) > 20  # Should be a secure token
        
        # Verify session validation
        session_user = auth_manager.validate_session(session_token)
        assert session_user is not None
        assert session_user.email == user.email
    
    def test_role_based_access(self, auth_manager, rbac):
        """Test role-based access control"""
        from src.models.user import UserRole
        
        # Test admin permissions
        assert rbac.has_permission(UserRole.ADMIN, "manage_users") is True
        assert rbac.has_permission(UserRole.ADMIN, "view_dashboard") is True
        
        # Test manager permissions
        assert rbac.has_permission(UserRole.MANAGER, "manage_users") is False
        assert rbac.has_permission(UserRole.MANAGER, "view_analytics") is True
        
        # Test user permissions
        assert rbac.has_permission(UserRole.USER, "view_dashboard") is True
        assert rbac.has_permission(UserRole.USER, "manage_integrations") is False
    
    def test_account_lockout_security(self, auth_manager):
        """Test account lockout after failed attempts"""
        email = "test@example.com"
        
        # Simulate multiple failed login attempts
        for _ in range(5):
            result = auth_manager.authenticate_user(email, "wrong_password")
            assert not result.success
        
        # Account should be locked
        assert auth_manager.is_account_locked(email)
        
        # Even correct password should fail when locked
        result = auth_manager.authenticate_user(email, "correct_password")
        assert not result.success
        assert "locked" in result.message.lower()

class TestDataEncryption:
    """Test data encryption and secure storage"""
    
    @pytest.fixture
    def encryption(self):
        """Create test encryption instance"""
        return DataEncryption("test_master_key_12345")
    
    @pytest.fixture
    def secure_storage(self, encryption):
        """Create test secure storage"""
        return SecureStorage(encryption)
    
    def test_string_encryption_decryption(self, encryption):
        """Test string encryption/decryption"""
        original_text = "Sensitive financial data: $50,000"
        
        # Encrypt
        encrypted = encryption.encrypt_string(original_text)
        assert encrypted != original_text
        assert len(encrypted) > len(original_text)
        
        # Decrypt
        decrypted = encryption.decrypt_string(encrypted)
        assert decrypted == original_text
    
    def test_dict_encryption_decryption(self, encryption):
        """Test dictionary encryption/decryption"""
        original_data = {
            "api_key": "sk_test_12345",
            "amount": 1000.50,
            "currency": "USD",
            "timestamp": datetime.now().isoformat()
        }
        
        # Encrypt
        encrypted = encryption.encrypt_dict(original_data)
        assert isinstance(encrypted, str)
        
        # Decrypt
        decrypted = encryption.decrypt_dict(encrypted)
        assert decrypted == original_data
    
    def test_api_key_encryption(self, encryption):
        """Test API key encryption with metadata"""
        api_key = "sk_live_sensitive_key_12345"
        
        # Encrypt with metadata
        encrypted = encryption.encrypt_api_key(api_key)
        
        # Decrypt and verify
        decrypted_key = encryption.decrypt_api_key(encrypted)
        assert decrypted_key == api_key
    
    def test_pii_masking(self, secure_storage):
        """Test PII masking in logs"""
        text_with_pii = "User email: john.doe@example.com, phone: 555-123-4567"
        
        masked = secure_storage.mask_pii_in_logs(text_with_pii)
        
        # Email should be masked
        assert "john.doe@example.com" not in masked
        assert "@example.com" in masked  # Domain preserved
        
        # Phone should be masked
        assert "555-123-4567" not in masked
        assert "XXX-XXX-XXXX" in masked
    
    def test_sensitive_data_storage(self, secure_storage):
        """Test secure sensitive data storage"""
        sensitive_data = {
            "credit_card": "4111-1111-1111-1111",
            "ssn": "123-45-6789",
            "api_secret": "very_secret_key"
        }
        
        # Store encrypted
        encrypted_data = secure_storage.store_sensitive_data("test_key", sensitive_data)
        
        # Retrieve and verify
        retrieved_data = secure_storage.retrieve_sensitive_data(encrypted_data, as_dict=True)
        assert retrieved_data == sensitive_data

class TestAuditLogging:
    """Test audit logging functionality"""
    
    @pytest.fixture
    def audit_logger(self):
        """Create test audit logger"""
        db_connection = Mock(spec=DatabaseConnection)
        return AuditLogger(db_connection)
    
    def test_financial_operation_logging(self, audit_logger):
        """Test financial operation audit logging"""
        # Mock database connection
        audit_logger.db.get_connection.return_value.__enter__ = Mock()
        audit_logger.db.get_connection.return_value.__exit__ = Mock()
        mock_conn = Mock()
        audit_logger.db.get_connection.return_value.__enter__.return_value = mock_conn
        
        # Log financial operation
        audit_logger.log_financial_operation(
            user_id="test@example.com",
            action=AuditAction.CREATE,
            entity_type="transaction",
            entity_id="txn_123",
            amount=1000.00,
            currency="USD",
            details={"category": "revenue"}
        )
        
        # Verify database call was made
        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args[0]
        assert "INSERT INTO audit_log" in call_args[0]
    
    def test_authentication_event_logging(self, audit_logger):
        """Test authentication event logging"""
        # Mock database connection
        audit_logger.db.get_connection.return_value.__enter__ = Mock()
        audit_logger.db.get_connection.return_value.__exit__ = Mock()
        mock_conn = Mock()
        audit_logger.db.get_connection.return_value.__enter__.return_value = mock_conn
        
        # Log authentication event
        audit_logger.log_authentication_event(
            user_email="test@example.com",
            action=AuditAction.LOGIN,
            success=True,
            details={"ip_address": "192.168.1.1"}
        )
        
        # Verify logging occurred
        mock_conn.execute.assert_called_once()
    
    def test_sensitive_data_detection(self, audit_logger):
        """Test sensitive data detection in audit logs"""
        sensitive_details = {
            "api_key": "sk_test_12345",
            "password": "secret123",
            "credit_card": "4111-1111-1111-1111"
        }
        
        # Should detect sensitive data
        assert audit_logger._contains_sensitive_data(sensitive_details)
        
        non_sensitive_details = {
            "category": "revenue",
            "amount": 1000.00,
            "currency": "USD"
        }
        
        # Should not detect sensitive data
        assert not audit_logger._contains_sensitive_data(non_sensitive_details)

class TestSecretsManager:
    """Test secrets management functionality"""
    
    @pytest.fixture
    def local_secrets_manager(self):
        """Create local secrets manager for testing"""
        return SecretsManager(SecretProvider.LOCAL_ENV)
    
    def test_local_secret_retrieval(self, local_secrets_manager):
        """Test local environment secret retrieval"""
        # Set test environment variable
        test_key = "TEST_SECRET_KEY"
        test_value = "test_secret_value_123"
        os.environ[test_key] = test_value
        
        try:
            # Retrieve secret
            retrieved = local_secrets_manager.get_secret(test_key)
            assert retrieved == test_value
        finally:
            # Clean up
            del os.environ[test_key]
    
    def test_secret_caching(self, local_secrets_manager):
        """Test secret caching mechanism"""
        test_key = "CACHED_SECRET"
        test_value = "cached_value_123"
        os.environ[test_key] = test_value
        
        try:
            # First retrieval
            first_retrieval = local_secrets_manager.get_secret(test_key)
            
            # Verify it's cached
            assert test_key + ":current" in local_secrets_manager.cache
            
            # Second retrieval should use cache
            second_retrieval = local_secrets_manager.get_secret(test_key)
            assert first_retrieval == second_retrieval
        finally:
            del os.environ[test_key]
    
    def test_secret_listing(self, local_secrets_manager):
        """Test listing secrets with patterns"""
        # Set test secrets
        secrets = {
            "API_KEY_STRIPE": "sk_test_123",
            "API_KEY_AIRTABLE": "key_456",
            "DATABASE_PASSWORD": "db_pass_789",
            "REGULAR_CONFIG": "not_secret"
        }
        
        for key, value in secrets.items():
            os.environ[key] = value
        
        try:
            # List secrets (should find API_KEY and PASSWORD patterns)
            secret_list = local_secrets_manager.list_secrets()
            
            assert "API_KEY_STRIPE" in secret_list
            assert "API_KEY_AIRTABLE" in secret_list
            assert "DATABASE_PASSWORD" in secret_list
            assert "REGULAR_CONFIG" not in secret_list  # Doesn't match secret patterns
        finally:
            for key in secrets:
                if key in os.environ:
                    del os.environ[key]

class TestSecurityIntegration:
    """Integration tests for security components"""
    
    def test_end_to_end_secure_workflow(self):
        """Test complete secure workflow"""
        # Initialize components
        encryption = DataEncryption("test_master_key")
        secure_storage = SecureStorage(encryption)
        
        # Simulate secure API key storage
        api_key = "sk_live_sensitive_production_key"
        
        # Encrypt and store
        encrypted_key = secure_storage.store_sensitive_data("stripe_api_key", api_key)
        
        # Retrieve and decrypt
        retrieved_key = secure_storage.retrieve_sensitive_data(encrypted_key)
        
        # Verify integrity
        assert retrieved_key == api_key
        
        # Verify PII masking works
        log_message = f"Processing payment with key: {api_key}"
        masked_message = secure_storage.mask_pii_in_logs(log_message)
        assert api_key not in masked_message
    
    @patch('src.security.audit.datetime')
    def test_audit_trail_integrity(self, mock_datetime):
        """Test audit trail maintains integrity"""
        # Mock datetime for consistent testing
        fixed_time = datetime(2024, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = fixed_time
        
        # Create audit logger with mocked DB
        db_connection = Mock(spec=DatabaseConnection)
        audit_logger = AuditLogger(db_connection)
        
        # Mock database operations
        mock_conn = Mock()
        db_connection.get_connection.return_value.__enter__.return_value = mock_conn
        
        # Log multiple operations
        operations = [
            {"action": AuditAction.LOGIN, "entity_type": "auth", "amount": None},
            {"action": AuditAction.CREATE, "entity_type": "transaction", "amount": 1000.00},
            {"action": AuditAction.UPDATE, "entity_type": "transaction", "amount": 1100.00},
        ]
        
        for op in operations:
            audit_logger.log_financial_operation(
                user_id="test@example.com",
                action=op["action"],
                entity_type=op["entity_type"],
                entity_id="test_entity",
                amount=op["amount"],
                currency="USD" if op["amount"] else None
            )
        
        # Verify all operations were logged
        assert mock_conn.execute.call_count == len(operations)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
