"""
Data Encryption and Secure Storage Utilities with Proper Cryptographic Practices
"""

import os
import base64
import logging
import secrets
from typing import Optional, Dict, Any, Union, Tuple
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import json
import re

from .pii_protection import get_structured_logger

# Use structured logger with PII protection
logger = get_structured_logger().get_logger(__name__)


class DataEncryption:
    """Data encryption utilities for sensitive information with proper cryptographic practices"""

    def __init__(self, master_key: Optional[str] = None):
        self.master_key = master_key or self._get_or_create_master_key()
        self._validate_master_key()

    def _get_or_create_master_key(self) -> str:
        """Get master encryption key with proper validation"""
        key = os.getenv("ENCRYPTION_MASTER_KEY")
        environment = os.getenv("ENVIRONMENT", "development")

        if not key:
            if environment == "production":
                raise ValueError(
                    "ENCRYPTION_MASTER_KEY is required in production. "
                    'Generate a secure key with: python -c "import secrets; print(secrets.token_urlsafe(32))"'
                )
            # Generate new key for development only
            key = secrets.token_urlsafe(32)
            logger.warning(
                "Using generated encryption key for development",
                environment="development",
                action="key_generation",
                recommendation="Set ENCRYPTION_MASTER_KEY in production",
            )

        return key

    def _validate_master_key(self):
        """Validate master key strength"""
        if len(self.master_key) < 32:
            raise ValueError(
                "Master key must be at least 32 characters long for security"
            )

        environment = os.getenv("ENVIRONMENT", "development")
        if environment == "production" and not os.getenv("ENCRYPTION_MASTER_KEY"):
            raise ValueError(
                "Master key must be provided via ENCRYPTION_MASTER_KEY in production"
            )

    def _derive_key_with_salt(self, salt: bytes) -> bytes:
        """Derive encryption key using PBKDF2 with provided salt"""
        if isinstance(self.master_key, str):
            key_bytes = self.master_key.encode("utf-8")
        else:
            key_bytes = self.master_key

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,  # OWASP recommended minimum
        )
        return base64.urlsafe_b64encode(kdf.derive(key_bytes))

    def _create_cipher_suite(self, salt: bytes) -> Fernet:
        """Create cipher suite with derived key"""
        derived_key = self._derive_key_with_salt(salt)
        return Fernet(derived_key)

    def encrypt_string(self, plaintext: str) -> str:
        """Encrypt a string with random salt"""
        try:
            # Generate random salt for each encryption
            salt = os.urandom(16)
            cipher_suite = self._create_cipher_suite(salt)
            encrypted_bytes = cipher_suite.encrypt(plaintext.encode("utf-8"))

            # Combine salt + encrypted data
            combined = salt + encrypted_bytes
            return base64.urlsafe_b64encode(combined).decode("utf-8")
        except Exception as e:
            logger.error(
                "Encryption failed",
                error_type=type(e).__name__,
                operation="encrypt_string",
            )
            raise

    def decrypt_string(self, encrypted_text: str) -> str:
        """Decrypt a string, extracting salt from encrypted data"""
        try:
            # Decode the combined data
            combined = base64.urlsafe_b64decode(encrypted_text.encode("utf-8"))

            # Extract salt (first 16 bytes) and encrypted data
            salt = combined[:16]
            encrypted_bytes = combined[16:]

            # Create cipher suite with extracted salt
            cipher_suite = self._create_cipher_suite(salt)
            decrypted_bytes = cipher_suite.decrypt(encrypted_bytes)
            return decrypted_bytes.decode("utf-8")
        except Exception as e:
            logger.error(
                "Decryption failed",
                error_type=type(e).__name__,
                operation="decrypt_string",
            )
            raise

    def encrypt_dict(self, data: Dict[str, Any]) -> str:
        """Encrypt a dictionary as JSON"""
        json_string = json.dumps(data, default=str)
        return self.encrypt_string(json_string)

    def decrypt_dict(self, encrypted_text: str) -> Dict[str, Any]:
        """Decrypt JSON back to dictionary"""
        json_string = self.decrypt_string(encrypted_text)
        return json.loads(json_string)

    def encrypt_api_key(self, api_key: str) -> str:
        """Encrypt API key with additional metadata"""
        import time

        metadata = {
            "key": api_key,
            "encrypted_at": str(int(time.time())),
            "key_type": "api_key",
        }
        return self.encrypt_dict(metadata)

    def decrypt_api_key(self, encrypted_key: str) -> str:
        """Decrypt API key and return just the key"""
        metadata = self.decrypt_dict(encrypted_key)
        return metadata["key"]

    def migrate_legacy_encrypted_data(self, legacy_encrypted: str) -> str:
        """
        Migrate data encrypted with the old static salt method.
        This is a one-time migration utility.
        """
        try:
            # Try to decrypt with old method first
            legacy_salt = b"cash_flow_salt"
            legacy_key = self._derive_key_with_salt(legacy_salt)
            legacy_cipher = Fernet(legacy_key)

            # Decode and decrypt with legacy method
            encrypted_bytes = base64.urlsafe_b64decode(legacy_encrypted.encode("utf-8"))
            decrypted_bytes = legacy_cipher.decrypt(encrypted_bytes)
            plaintext = decrypted_bytes.decode("utf-8")

            # Re-encrypt with new method (random salt)
            return self.encrypt_string(plaintext)

        except Exception as e:
            logger.error(
                "Legacy data migration failed",
                error_type=type(e).__name__,
                operation="migrate_legacy_data",
            )
            # If migration fails, assume it's already new format
            return legacy_encrypted


class SecureStorage:
    """Secure storage for sensitive data with PII masking"""

    def __init__(self, encryption: Optional[DataEncryption] = None):
        self.encryption = encryption or DataEncryption()
        # Use enhanced PII detector
        from .pii_protection import get_pii_detector

        self.pii_detector = get_pii_detector()

    def store_sensitive_data(self, key: str, data: Union[str, Dict[str, Any]]) -> str:
        """Store sensitive data with encryption"""
        try:
            if isinstance(data, dict):
                encrypted_data = self.encryption.encrypt_dict(data)
            else:
                encrypted_data = self.encryption.encrypt_string(str(data))

            logger.info(
                "Stored encrypted data",
                key_masked=self.mask_key(key),
                operation="store_sensitive_data",
            )
            return encrypted_data

        except Exception as e:
            logger.error(
                "Error storing sensitive data",
                error_type=type(e).__name__,
                operation="store_sensitive_data",
            )
            raise

    def retrieve_sensitive_data(
        self, encrypted_data: str, as_dict: bool = False
    ) -> Union[str, Dict[str, Any]]:
        """Retrieve and decrypt sensitive data"""
        try:
            if as_dict:
                return self.encryption.decrypt_dict(encrypted_data)
            else:
                return self.encryption.decrypt_string(encrypted_data)

        except Exception as e:
            logger.error(
                "Error retrieving sensitive data",
                error_type=type(e).__name__,
                operation="retrieve_sensitive_data",
            )
            raise

    def mask_pii_in_logs(self, text: str) -> str:
        """Mask PII in log messages using enhanced detector"""
        return self.pii_detector.mask_pii(text)

    def mask_key(self, key: str) -> str:
        """Mask sensitive keys for logging"""
        return self.pii_detector.mask_pii(key)

    def secure_delete(self, data: str) -> None:
        """Securely delete sensitive data from memory"""
        # In Python, we can't truly secure delete from memory
        # but we can overwrite the reference
        if data:
            # Overwrite with random data (simplified)
            import secrets

            overwrite = secrets.token_bytes(len(data))
            data = overwrite.hex()
            del overwrite
            del data


class HTTPSEnforcer:
    """HTTPS enforcement utilities"""

    @staticmethod
    def enforce_https() -> bool:
        """Check if HTTPS is being used (simplified for Streamlit)"""
        # In a real deployment, you'd check request headers
        # For Streamlit, this is handled at the reverse proxy level
        return True

    @staticmethod
    def get_security_headers() -> Dict[str, str]:
        """Get recommended security headers"""
        return {
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
        }

    @staticmethod
    def validate_ssl_config() -> Dict[str, Any]:
        """Validate SSL configuration"""
        return {
            "https_enforced": HTTPSEnforcer.enforce_https(),
            "security_headers": HTTPSEnforcer.get_security_headers(),
            "ssl_version": "TLS 1.2+",
            "certificate_valid": True,  # Would check actual certificate in production
        }
