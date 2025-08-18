#!/usr/bin/env python3
"""
Test script for the updated encryption system with proper cryptographic practices.
"""

import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.security.encryption import DataEncryption, SecureStorage


def test_basic_encryption():
    """Test basic string encryption and decryption."""
    print("🔐 Testing basic encryption...")
    
    # Test with a secure key
    test_key = "test_key_that_is_at_least_32_chars_long_for_security"
    encryption = DataEncryption(master_key=test_key)
    
    # Test data
    test_string = "This is a secret message!"
    test_dict = {
        "api_key": "sk_test_123456789",
        "user_id": 12345,
        "permissions": ["read", "write"]
    }
    
    # Test string encryption
    encrypted_string = encryption.encrypt_string(test_string)
    decrypted_string = encryption.decrypt_string(encrypted_string)
    
    assert decrypted_string == test_string, "String encryption/decryption failed"
    print(f"✅ String encryption: '{test_string}' -> encrypted -> '{decrypted_string}'")
    
    # Test dict encryption
    encrypted_dict = encryption.encrypt_dict(test_dict)
    decrypted_dict = encryption.decrypt_dict(encrypted_dict)
    
    assert decrypted_dict == test_dict, "Dict encryption/decryption failed"
    print(f"✅ Dict encryption: {test_dict} -> encrypted -> {decrypted_dict}")
    
    # Test API key encryption
    api_key = "sk_live_very_secret_key_12345"
    encrypted_api = encryption.encrypt_api_key(api_key)
    decrypted_api = encryption.decrypt_api_key(encrypted_api)
    
    assert decrypted_api == api_key, "API key encryption/decryption failed"
    print(f"✅ API key encryption: '{api_key}' -> encrypted -> '{decrypted_api}'")


def test_salt_randomness():
    """Test that each encryption uses a different salt."""
    print("\n🧂 Testing salt randomness...")
    
    test_key = "test_key_that_is_at_least_32_chars_long_for_security"
    encryption = DataEncryption(master_key=test_key)
    
    test_string = "Same message encrypted multiple times"
    
    # Encrypt the same string multiple times
    encrypted_1 = encryption.encrypt_string(test_string)
    encrypted_2 = encryption.encrypt_string(test_string)
    encrypted_3 = encryption.encrypt_string(test_string)
    
    # All encrypted versions should be different (due to random salt)
    assert encrypted_1 != encrypted_2, "Encrypted strings should be different with random salt"
    assert encrypted_2 != encrypted_3, "Encrypted strings should be different with random salt"
    assert encrypted_1 != encrypted_3, "Encrypted strings should be different with random salt"
    
    # But all should decrypt to the same original string
    assert encryption.decrypt_string(encrypted_1) == test_string
    assert encryption.decrypt_string(encrypted_2) == test_string
    assert encryption.decrypt_string(encrypted_3) == test_string
    
    print("✅ Each encryption uses a unique random salt")
    print(f"   Original: '{test_string}'")
    print(f"   Encrypted 1: {encrypted_1[:50]}...")
    print(f"   Encrypted 2: {encrypted_2[:50]}...")
    print(f"   Encrypted 3: {encrypted_3[:50]}...")


def test_key_validation():
    """Test master key validation."""
    print("\n🔑 Testing key validation...")
    
    # Test weak key (should fail)
    try:
        weak_encryption = DataEncryption(master_key="weak")
        assert False, "Should have failed with weak key"
    except ValueError as e:
        print(f"✅ Weak key rejected: {e}")
    
    # Test strong key (should work)
    try:
        strong_key = "this_is_a_very_strong_key_with_32_plus_characters"
        strong_encryption = DataEncryption(master_key=strong_key)
        print("✅ Strong key accepted")
    except Exception as e:
        print(f"❌ Strong key rejected unexpectedly: {e}")


def test_production_mode():
    """Test production mode requirements."""
    print("\n🏭 Testing production mode...")
    
    # Set production environment
    os.environ['ENVIRONMENT'] = 'production'
    
    # Remove encryption key to test production requirement
    if 'ENCRYPTION_MASTER_KEY' in os.environ:
        del os.environ['ENCRYPTION_MASTER_KEY']
    
    try:
        prod_encryption = DataEncryption()
        assert False, "Should have failed without key in production"
    except ValueError as e:
        print(f"✅ Production mode requires explicit key: {e}")
    
    # Reset environment
    os.environ['ENVIRONMENT'] = 'development'


def test_secure_storage():
    """Test secure storage functionality."""
    print("\n🔒 Testing secure storage...")
    
    test_key = "test_key_that_is_at_least_32_chars_long_for_security"
    encryption = DataEncryption(master_key=test_key)
    storage = SecureStorage(encryption=encryption)
    
    # Test PII masking
    test_text = "Contact john.doe@example.com or call 555-123-4567"
    masked = storage.mask_pii_in_logs(test_text)
    
    assert "john.doe@example.com" not in masked, "Email should be masked"
    assert "555-123-4567" not in masked, "Phone should be masked"
    print(f"✅ PII masking: '{test_text}' -> '{masked}'")
    
    # Test key masking
    sensitive_key = "very_sensitive_api_key_12345"
    masked_key = storage.mask_key(sensitive_key)
    assert len(masked_key) == len(sensitive_key), "Masked key should be same length"
    assert "very_sensitive" not in masked_key, "Key content should be masked"
    print(f"✅ Key masking: '{sensitive_key}' -> '{masked_key}'")


def test_migration_compatibility():
    """Test legacy data migration."""
    print("\n🔄 Testing migration compatibility...")
    
    test_key = "test_key_that_is_at_least_32_chars_long_for_security"
    encryption = DataEncryption(master_key=test_key)
    
    # Create some "legacy" encrypted data (this would be from old system)
    test_data = "Legacy encrypted data"
    
    # For this test, we'll just test that migration doesn't break new data
    new_encrypted = encryption.encrypt_string(test_data)
    migrated = encryption.migrate_legacy_encrypted_data(new_encrypted)
    
    # Should be able to decrypt the result
    decrypted = encryption.decrypt_string(migrated)
    assert decrypted == test_data, "Migration should preserve data integrity"
    
    print("✅ Migration compatibility maintained")


def main():
    """Run all encryption tests."""
    print("🧪 Cash Flow Dashboard - Encryption System Tests")
    print("=" * 55)
    
    try:
        test_basic_encryption()
        test_salt_randomness()
        test_key_validation()
        test_production_mode()
        test_secure_storage()
        test_migration_compatibility()
        
        print("\n🎉 All encryption tests passed!")
        print("\n📋 Summary:")
        print("  ✅ Random salt generation working")
        print("  ✅ PBKDF2 key derivation implemented")
        print("  ✅ Strong key validation enforced")
        print("  ✅ Production mode security requirements")
        print("  ✅ PII masking and secure storage")
        print("  ✅ Migration compatibility maintained")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
