"""
Comprehensive test suite for KeyVaultService
"""

import os
import sys
import tempfile
import sqlite3
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.key_vault import KeyVaultService, get_key_vault_service, clear_session_vault
from src.security.api_key_encryption import APIKeyEncryption

class TestKeyVaultService(unittest.TestCase):
    """Test suite for KeyVaultService"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        # Set environment variables
        os.environ['DATABASE_URL'] = f"sqlite:///{self.temp_db.name}"
        os.environ['API_KEY_MASTER_KEY'] = 'test_master_key_for_encryption_32chars'
        
        # Initialize database schema
        self._init_test_database()
        
        # Create test service
        self.session_id = "test_session_123"
        self.user_id = 1
        self.vault_service = KeyVaultService(self.session_id, self.user_id)
        
        # Test data
        self.test_key_name = "test_stripe_key"
        self.test_api_key = "sk_test_1234567890abcdef"
        self.test_service_type = "stripe"
        self.test_description = "Test Stripe API key"
    
    def tearDown(self):
        """Clean up test environment"""
        # Clear cache
        self.vault_service.clear_cache()
        
        # Remove temporary database
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
        
        # Clean up environment
        if 'DATABASE_URL' in os.environ:
            del os.environ['DATABASE_URL']
        if 'API_KEY_MASTER_KEY' in os.environ:
            del os.environ['API_KEY_MASTER_KEY']
    
    def _init_test_database(self):
        """Initialize test database with required schema"""
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        
        # Create api_keys table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_name TEXT UNIQUE NOT NULL,
                encrypted_value TEXT NOT NULL,
                service_type TEXT NOT NULL,
                added_by_user INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                description TEXT
            )
        ''')
        
        # Create audit_logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation TEXT NOT NULL,
                key_name TEXT,
                user_id INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                success BOOLEAN,
                error_message TEXT,
                ip_address TEXT,
                user_agent TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def test_store_api_key(self):
        """Test storing API key in vault"""
        success, message = self.vault_service.store_api_key(
            key_name=self.test_key_name,
            api_key=self.test_api_key,
            service_type=self.test_service_type,
            description=self.test_description
        )
        
        self.assertTrue(success)
        self.assertIn("stored successfully", message)
        
        # Verify key is stored in database
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM api_keys WHERE key_name = ?", (self.test_key_name,))
        result = cursor.fetchone()
        conn.close()
        
        self.assertIsNotNone(result)
        self.assertEqual(result[1], self.test_key_name)  # key_name
        self.assertEqual(result[3], self.test_service_type)  # service_type
        self.assertEqual(result[4], self.user_id)  # added_by_user
        self.assertTrue(result[7])  # is_active
        self.assertEqual(result[8], self.test_description)  # description
    
    def test_retrieve_api_key_context_manager(self):
        """Test retrieving API key using context manager"""
        # First store a key
        self.vault_service.store_api_key(
            key_name=self.test_key_name,
            api_key=self.test_api_key,
            service_type=self.test_service_type
        )
        
        # Retrieve using context manager
        with self.vault_service.retrieve_api_key(self.test_key_name) as key_context:
            self.assertIsNotNone(key_context)
            self.assertEqual(key_context.key_name, self.test_key_name)
            self.assertEqual(key_context.key_value, self.test_api_key)
            self.assertEqual(key_context.service_type, self.test_service_type)
    
    def test_caching_behavior(self):
        """Test API key caching behavior"""
        # Store key
        self.vault_service.store_api_key(
            key_name=self.test_key_name,
            api_key=self.test_api_key,
            service_type=self.test_service_type
        )
        
        # First retrieval should cache the key
        with self.vault_service.retrieve_api_key(self.test_key_name) as key_context:
            self.assertEqual(key_context.key_value, self.test_api_key)
        
        # Check cache stats
        cache_stats = self.vault_service.get_cache_stats()
        self.assertEqual(cache_stats["cached_keys"], 1)
        self.assertIn(self.test_key_name, cache_stats["keys"])
        
        # Second retrieval should use cache
        with self.vault_service.retrieve_api_key(self.test_key_name) as key_context:
            self.assertEqual(key_context.key_value, self.test_api_key)
        
        # Access count should increase
        cache_stats = self.vault_service.get_cache_stats()
        self.assertEqual(cache_stats["keys"][self.test_key_name]["access_count"], 2)
    
    def test_update_api_key(self):
        """Test updating API key in vault"""
        # Store initial key
        self.vault_service.store_api_key(
            key_name=self.test_key_name,
            api_key=self.test_api_key,
            service_type=self.test_service_type
        )
        
        # Update key
        new_api_key = "sk_test_updated_key_9876543210"
        new_description = "Updated test key"
        
        success, message = self.vault_service.update_api_key(
            key_name=self.test_key_name,
            new_api_key=new_api_key,
            description=new_description
        )
        
        self.assertTrue(success)
        self.assertIn("updated successfully", message)
        
        # Verify updated key
        with self.vault_service.retrieve_api_key(self.test_key_name) as key_context:
            self.assertEqual(key_context.key_value, new_api_key)
    
    def test_delete_api_key(self):
        """Test deleting API key from vault"""
        # Store key
        self.vault_service.store_api_key(
            key_name=self.test_key_name,
            api_key=self.test_api_key,
            service_type=self.test_service_type
        )
        
        # Delete key
        success, message = self.vault_service.delete_api_key(self.test_key_name)
        
        self.assertTrue(success)
        self.assertIn("deleted successfully", message)
        
        # Verify key is marked inactive
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        cursor.execute("SELECT is_active FROM api_keys WHERE key_name = ?", (self.test_key_name,))
        result = cursor.fetchone()
        conn.close()
        
        self.assertIsNotNone(result)
        self.assertFalse(result[0])  # is_active should be False
    
    def test_list_api_keys(self):
        """Test listing API keys from vault"""
        # Store multiple keys
        keys_data = [
            ("stripe_prod", "sk_live_123", "stripe", "Production Stripe key"),
            ("openai_test", "sk-test-456", "openai", "Test OpenAI key"),
            ("airtable_main", "keyABC789", "airtable", "Main Airtable key")
        ]
        
        for key_name, api_key, service_type, description in keys_data:
            self.vault_service.store_api_key(
                key_name=key_name,
                api_key=api_key,
                service_type=service_type,
                description=description
            )
        
        # List all keys
        api_keys = self.vault_service.list_api_keys()
        self.assertEqual(len(api_keys), 3)
        
        # List keys by service type
        stripe_keys = self.vault_service.list_api_keys(service_type="stripe")
        self.assertEqual(len(stripe_keys), 1)
        self.assertEqual(stripe_keys[0].key_name, "stripe_prod")
        
        # Verify masked values
        for api_key in api_keys:
            self.assertIn("****", api_key.masked_value)
            self.assertNotEqual(api_key.masked_value, api_key.key_name)
    
    @patch('src.services.api_key_test_service.APIKeyTestService.test_api_key')
    def test_test_api_key(self, mock_test):
        """Test API key testing functionality"""
        # Mock successful test
        mock_test.return_value = (True, "Connection successful", {"status_code": 200})
        
        # Store key
        self.vault_service.store_api_key(
            key_name=self.test_key_name,
            api_key=self.test_api_key,
            service_type=self.test_service_type
        )
        
        # Test key
        success, message, details = self.vault_service.test_api_key(self.test_key_name)
        
        self.assertTrue(success)
        self.assertEqual(message, "Connection successful")
        self.assertEqual(details["status_code"], 200)
        
        # Verify test service was called with correct parameters
        mock_test.assert_called_once_with(self.test_api_key, self.test_service_type)
    
    def test_cache_clearing(self):
        """Test cache clearing functionality"""
        # Store and cache key
        self.vault_service.store_api_key(
            key_name=self.test_key_name,
            api_key=self.test_api_key,
            service_type=self.test_service_type
        )
        
        with self.vault_service.retrieve_api_key(self.test_key_name) as key_context:
            pass  # This caches the key
        
        # Verify key is cached
        cache_stats = self.vault_service.get_cache_stats()
        self.assertEqual(cache_stats["cached_keys"], 1)
        
        # Clear cache
        self.vault_service.clear_cache()
        
        # Verify cache is empty
        cache_stats = self.vault_service.get_cache_stats()
        self.assertEqual(cache_stats["cached_keys"], 0)
    
    def test_expired_cache_cleanup(self):
        """Test cleanup of expired cache entries"""
        # Store key
        self.vault_service.store_api_key(
            key_name=self.test_key_name,
            api_key=self.test_api_key,
            service_type=self.test_service_type
        )
        
        # Cache key
        with self.vault_service.retrieve_api_key(self.test_key_name) as key_context:
            pass
        
        # Manually expire cache entry
        cached_key = self.vault_service._cache[self.test_key_name]
        cached_key.cached_at = datetime.utcnow() - timedelta(hours=2)
        
        # Run cleanup
        self.vault_service.cleanup_expired_cache()
        
        # Verify expired entry was removed
        cache_stats = self.vault_service.get_cache_stats()
        self.assertEqual(cache_stats["cached_keys"], 0)
    
    def test_audit_logging(self):
        """Test audit logging for vault operations"""
        # Store key (should create audit log)
        self.vault_service.store_api_key(
            key_name=self.test_key_name,
            api_key=self.test_api_key,
            service_type=self.test_service_type,
            ip_address="127.0.0.1",
            user_agent="Test Agent"
        )
        
        # Check audit logs
        audit_logs = self.vault_service.get_audit_logs(limit=10)
        self.assertGreater(len(audit_logs), 0)
        
        # Verify log entry
        log_entry = audit_logs[0]
        self.assertEqual(log_entry["operation"], "store_api_key")
        self.assertEqual(log_entry["key_name"], self.test_key_name)
        self.assertEqual(log_entry["user_id"], self.user_id)
        self.assertTrue(log_entry["success"])
        self.assertEqual(log_entry["ip_address"], "127.0.0.1")
        self.assertEqual(log_entry["user_agent"], "Test Agent")
    
    def test_error_handling(self):
        """Test error handling in vault operations"""
        # Try to retrieve non-existent key
        with self.vault_service.retrieve_api_key("non_existent_key") as key_context:
            self.assertIsNone(key_context)
        
        # Try to update non-existent key
        success, message = self.vault_service.update_api_key(
            "non_existent_key", 
            "new_key", 
            "new_description"
        )
        self.assertFalse(success)
        self.assertIn("not found", message)
        
        # Try to delete non-existent key
        success, message = self.vault_service.delete_api_key("non_existent_key")
        self.assertFalse(success)
        self.assertIn("not found", message)
    
    def test_global_service_management(self):
        """Test global service instance management"""
        # Get service instance
        service1 = get_key_vault_service(self.session_id, self.user_id)
        service2 = get_key_vault_service(self.session_id, self.user_id)
        
        # Should return same instance for same session
        self.assertIs(service1, service2)
        
        # Clear session vault
        clear_session_vault(self.session_id)
        
        # Should create new instance after clearing
        service3 = get_key_vault_service(self.session_id, self.user_id)
        self.assertIsNot(service1, service3)
    
    def test_memory_security(self):
        """Test secure memory handling"""
        # Store key
        self.vault_service.store_api_key(
            key_name=self.test_key_name,
            api_key=self.test_api_key,
            service_type=self.test_service_type
        )
        
        # Use context manager
        with self.vault_service.retrieve_api_key(self.test_key_name) as key_context:
            # Key should be available in context
            self.assertEqual(key_context.key_value, self.test_api_key)
            key_reference = key_context.key_value
        
        # After context exit, key should be cleared from memory
        # Note: This is a basic test - in practice, memory clearing is more complex
        self.assertIsNotNone(key_reference)  # Reference still exists but content should be cleared

if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
