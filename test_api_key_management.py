"""
Test suite for API Key Management System
"""

import os
import tempfile
import sqlite3
from datetime import datetime
from src.security.api_key_encryption import APIKeyEncryption
from src.services.api_key_service import APIKeyService
from src.services.api_key_test_service import APIKeyTestService

def test_api_key_encryption():
    """Test API key encryption and decryption"""
    print("🔍 Testing API Key Encryption")
    
    # Set test environment variable
    os.environ['API_KEY_MASTER_KEY'] = 'test-master-key-for-encryption-32-chars'
    
    try:
        encryption = APIKeyEncryption()
        
        # Test encryption/decryption
        test_key = "sk_test_1234567890abcdef"
        encrypted = encryption.encrypt_api_key(test_key)
        decrypted = encryption.decrypt_api_key(encrypted)
        
        if decrypted == test_key:
            print("✅ Encryption/decryption working correctly")
        else:
            print("❌ Encryption/decryption failed")
            return False
        
        # Test masking
        masked = encryption.mask_api_key(test_key)
        if masked.startswith("sk_test_") and masked.endswith("cdef") and "*" in masked:
            print(f"✅ API key masking working: {masked}")
        else:
            print(f"❌ API key masking failed: {masked}")
            return False
        
        # Test validation
        is_valid, error = encryption.validate_api_key_format(test_key, "stripe")
        if is_valid:
            print("✅ API key validation working")
        else:
            print(f"❌ API key validation failed: {error}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Encryption test failed: {e}")
        return False

def test_api_key_service():
    """Test API key service operations"""
    print("\n🔍 Testing API Key Service")
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
        db_path = tmp_db.name
    
    try:
        # Create test database with api_keys table
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_name TEXT NOT NULL UNIQUE,
                encrypted_value TEXT NOT NULL,
                service_type TEXT NOT NULL,
                added_by_user TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                description TEXT
            )
        ''')
        conn.commit()
        conn.close()
        
        # Mock the database connection
        original_db_path = os.environ.get('DATABASE_URL', '')
        os.environ['DATABASE_URL'] = f'sqlite:///{db_path}'
        
        # Test service operations
        service = APIKeyService()
        
        # Test adding API key
        success, message = service.add_api_key(
            key_name="test_stripe_key",
            api_key="sk_test_1234567890abcdef",
            service_type="stripe",
            added_by_user="test_user",
            description="Test Stripe key"
        )
        
        if success:
            print("✅ API key added successfully")
        else:
            print(f"❌ Failed to add API key: {message}")
            return False
        
        # Test retrieving API keys
        api_keys = service.get_api_keys()
        if len(api_keys) == 1 and api_keys[0].key_name == "test_stripe_key":
            print("✅ API key retrieved successfully")
            print(f"   Masked value: {api_keys[0].masked_value}")
        else:
            print("❌ Failed to retrieve API key")
            return False
        
        # Test getting API key value
        key_value = service.get_api_key_value("test_stripe_key")
        if key_value == "sk_test_1234567890abcdef":
            print("✅ API key value retrieved successfully")
        else:
            print("❌ Failed to retrieve API key value")
            return False
        
        # Test updating API key
        success, message = service.update_api_key(
            "test_stripe_key",
            "sk_test_new_key_value",
            "Updated test key"
        )
        
        if success:
            print("✅ API key updated successfully")
        else:
            print(f"❌ Failed to update API key: {message}")
            return False
        
        # Test deleting API key
        success, message = service.delete_api_key("test_stripe_key")
        if success:
            print("✅ API key deleted successfully")
        else:
            print(f"❌ Failed to delete API key: {message}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Service test failed: {e}")
        return False
    finally:
        # Cleanup
        if 'DATABASE_URL' in os.environ:
            if original_db_path:
                os.environ['DATABASE_URL'] = original_db_path
            else:
                del os.environ['DATABASE_URL']
        try:
            os.unlink(db_path)
        except:
            pass

def test_api_key_test_service():
    """Test API key testing service"""
    print("\n🔍 Testing API Key Test Service")
    
    try:
        test_service = APIKeyTestService()
        
        # Test generic validation (no actual API calls)
        success, message, details = test_service.test_generic_key(
            "test_key_1234567890",
            "custom_service"
        )
        
        if success and details.get('validation_only'):
            print("✅ Generic API key validation working")
        else:
            print(f"❌ Generic validation failed: {message}")
            return False
        
        # Test invalid key format
        success, message, details = test_service.test_generic_key(
            "short",
            "custom_service"
        )
        
        if not success and "too short" in message:
            print("✅ Invalid key format detection working")
        else:
            print(f"❌ Invalid format detection failed: {message}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Test service failed: {e}")
        return False

def run_all_tests():
    """Run all API key management tests"""
    print("🧪 API Key Management Test Suite")
    print("=" * 60)
    
    tests = [
        test_api_key_encryption,
        test_api_key_service,
        test_api_key_test_service
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            failed += 1
    
    print("\n🎯 Test Results")
    print("=" * 60)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Total: {passed + failed}")
    
    if failed == 0:
        print("\n🎉 All API key management tests passed!")
        print("\n📋 System Ready:")
        print("  ✅ API key encryption/decryption")
        print("  ✅ Secure API key storage")
        print("  ✅ API key masking for display")
        print("  ✅ CRUD operations")
        print("  ✅ Service validation")
        return True
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please review the issues above.")
        return False

if __name__ == "__main__":
    run_all_tests()
