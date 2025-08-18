"""
Secure API key encryption service using Fernet encryption.
"""

import os
import base64
import hashlib
from typing import Optional, Tuple
from cryptography.fernet import Fernet
import logging

logger = logging.getLogger(__name__)

class APIKeyEncryption:
    """Handles encryption and decryption of API keys using Fernet"""
    
    def __init__(self, master_key: Optional[str] = None):
        """Initialize with master key from environment or parameter"""
        self.master_key = master_key or os.getenv('API_KEY_MASTER_KEY')
        if not self.master_key:
            raise ValueError("API_KEY_MASTER_KEY environment variable is required")
        
        if len(self.master_key) < 32:
            raise ValueError("Master key must be at least 32 characters long")
        
        self._fernet = self._create_fernet_instance()
        logger.info("API key encryption service initialized",
                   operation="encryption_init")
    
    def _create_fernet_instance(self) -> Fernet:
        """Create Fernet instance with derived key"""
        # Derive a consistent key from the master key
        key_material = hashlib.pbkdf2_hmac(
            'sha256',
            self.master_key.encode(),
            b'api_key_encryption_salt',
            100000,
            32  # 32 bytes for Fernet
        )
        # Convert to URL-safe base64 for Fernet
        fernet_key = base64.urlsafe_b64encode(key_material)
        return Fernet(fernet_key)
    
    def encrypt_api_key(self, api_key: str) -> str:
        """
        Encrypt an API key and return base64 encoded result
        
        Args:
            api_key: The plain text API key to encrypt
            
        Returns:
            Base64 encoded encrypted API key
        """
        try:
            if not api_key or not api_key.strip():
                raise ValueError("API key cannot be empty")
            
            encrypted_bytes = self._fernet.encrypt(api_key.encode())
            encrypted_b64 = base64.urlsafe_b64encode(encrypted_bytes).decode()
            
            logger.info("API key encrypted successfully",
                       operation="encrypt_api_key",
                       key_length=len(api_key))
            
            return encrypted_b64
            
        except Exception as e:
            logger.error("Failed to encrypt API key",
                        error=str(e),
                        operation="encrypt_api_key")
            raise
    
    def decrypt_api_key(self, encrypted_api_key: str) -> str:
        """
        Decrypt an API key from base64 encoded encrypted data
        
        Args:
            encrypted_api_key: Base64 encoded encrypted API key
            
        Returns:
            Plain text API key
        """
        try:
            if not encrypted_api_key or not encrypted_api_key.strip():
                raise ValueError("Encrypted API key cannot be empty")
            
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_api_key.encode())
            decrypted_bytes = self._fernet.decrypt(encrypted_bytes)
            api_key = decrypted_bytes.decode()
            
            logger.info("API key decrypted successfully",
                       operation="decrypt_api_key")
            
            return api_key
            
        except Exception as e:
            logger.error("Failed to decrypt API key",
                        error=str(e),
                        operation="decrypt_api_key")
            raise
    
    def mask_api_key(self, api_key: str, show_chars: int = 4) -> str:
        """
        Create a masked version of an API key for display
        
        Args:
            api_key: The plain text API key
            show_chars: Number of characters to show at the end
            
        Returns:
            Masked API key (e.g., "sk_live_****6789")
        """
        if not api_key or len(api_key) <= show_chars:
            return "*" * 8
        
        # Handle common API key prefixes
        prefixes = ['sk_live_', 'sk_test_', 'pk_live_', 'pk_test_', 'rk_live_', 'rk_test_']
        prefix = ""
        key_part = api_key
        
        for p in prefixes:
            if api_key.startswith(p):
                prefix = p
                key_part = api_key[len(p):]
                break
        
        if len(key_part) <= show_chars:
            return prefix + "*" * 8
        
        masked_middle = "*" * min(8, len(key_part) - show_chars)
        visible_end = key_part[-show_chars:]
        
        return f"{prefix}{masked_middle}{visible_end}"
    
    def validate_api_key_format(self, api_key: str, service_type: str) -> Tuple[bool, str]:
        """
        Validate API key format for specific services
        
        Args:
            api_key: The API key to validate
            service_type: Type of service (stripe, openai, etc.)
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not api_key or not api_key.strip():
            return False, "API key cannot be empty"
        
        api_key = api_key.strip()
        
        # Service-specific validation
        if service_type.lower() == 'stripe':
            if not (api_key.startswith('sk_live_') or api_key.startswith('sk_test_')):
                return False, "Stripe API keys must start with 'sk_live_' or 'sk_test_'"
            if len(api_key) < 20:
                return False, "Stripe API key appears to be too short"
                
        elif service_type.lower() == 'openai':
            if not api_key.startswith('sk-'):
                return False, "OpenAI API keys must start with 'sk-'"
            if len(api_key) < 20:
                return False, "OpenAI API key appears to be too short"
                
        elif service_type.lower() == 'airtable':
            if not api_key.startswith('key'):
                return False, "Airtable API keys must start with 'key'"
            if len(api_key) < 15:
                return False, "Airtable API key appears to be too short"
        
        # General validation
        if len(api_key) < 10:
            return False, "API key appears to be too short"
        
        if len(api_key) > 200:
            return False, "API key appears to be too long"
        
        # Check for suspicious characters
        if any(char in api_key for char in [' ', '\n', '\t', '\r']):
            return False, "API key contains invalid whitespace characters"
        
        return True, ""

# Global instance
_api_key_encryption = None

def get_api_key_encryption() -> APIKeyEncryption:
    """Get global API key encryption instance"""
    global _api_key_encryption
    if _api_key_encryption is None:
        _api_key_encryption = APIKeyEncryption()
    return _api_key_encryption
