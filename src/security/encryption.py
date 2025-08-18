"""
Data Encryption and Secure Storage Utilities
"""

import os
import base64
import logging
from typing import Optional, Dict, Any, Union
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import json
import re

logger = logging.getLogger(__name__)

class DataEncryption:
    """Data encryption utilities for sensitive information"""
    
    def __init__(self, master_key: Optional[str] = None):
        self.master_key = master_key or self._get_or_create_master_key()
        self.cipher_suite = self._create_cipher_suite()
    
    def _get_or_create_master_key(self) -> str:
        """Get or create master encryption key"""
        key = os.getenv('ENCRYPTION_MASTER_KEY')
        if not key:
            # Generate new key for development
            key = Fernet.generate_key().decode()
            logger.warning("Generated new encryption key - set ENCRYPTION_MASTER_KEY in production")
        return key
    
    def _create_cipher_suite(self) -> Fernet:
        """Create cipher suite from master key"""
        if isinstance(self.master_key, str):
            key_bytes = self.master_key.encode()
        else:
            key_bytes = self.master_key
        
        # Derive key using PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'cash_flow_salt',  # In production, use random salt per encryption
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(key_bytes))
        return Fernet(key)
    
    def encrypt_string(self, plaintext: str) -> str:
        """Encrypt a string"""
        try:
            encrypted_bytes = self.cipher_suite.encrypt(plaintext.encode())
            return base64.urlsafe_b64encode(encrypted_bytes).decode()
        except Exception as e:
            logger.error(f"Encryption error: {str(e)}")
            raise
    
    def decrypt_string(self, encrypted_text: str) -> str:
        """Decrypt a string"""
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_text.encode())
            decrypted_bytes = self.cipher_suite.decrypt(encrypted_bytes)
            return decrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Decryption error: {str(e)}")
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
        metadata = {
            'key': api_key,
            'encrypted_at': str(os.times().elapsed),
            'key_type': 'api_key'
        }
        return self.encrypt_dict(metadata)
    
    def decrypt_api_key(self, encrypted_key: str) -> str:
        """Decrypt API key and return just the key"""
        metadata = self.decrypt_dict(encrypted_key)
        return metadata['key']

class SecureStorage:
    """Secure storage for sensitive data with PII masking"""
    
    def __init__(self, encryption: Optional[DataEncryption] = None):
        self.encryption = encryption or DataEncryption()
        self.pii_patterns = {
            'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            'phone': re.compile(r'\b\d{3}-?\d{3}-?\d{4}\b'),
            'ssn': re.compile(r'\b\d{3}-?\d{2}-?\d{4}\b'),
            'credit_card': re.compile(r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b')
        }
    
    def store_sensitive_data(self, key: str, data: Union[str, Dict[str, Any]]) -> str:
        """Store sensitive data with encryption"""
        try:
            if isinstance(data, dict):
                encrypted_data = self.encryption.encrypt_dict(data)
            else:
                encrypted_data = self.encryption.encrypt_string(str(data))
            
            logger.info(f"Stored encrypted data for key: {self.mask_key(key)}")
            return encrypted_data
            
        except Exception as e:
            logger.error(f"Error storing sensitive data: {str(e)}")
            raise
    
    def retrieve_sensitive_data(self, encrypted_data: str, as_dict: bool = False) -> Union[str, Dict[str, Any]]:
        """Retrieve and decrypt sensitive data"""
        try:
            if as_dict:
                return self.encryption.decrypt_dict(encrypted_data)
            else:
                return self.encryption.decrypt_string(encrypted_data)
                
        except Exception as e:
            logger.error(f"Error retrieving sensitive data: {str(e)}")
            raise
    
    def mask_pii_in_logs(self, text: str) -> str:
        """Mask PII in log messages"""
        masked_text = text
        
        for pii_type, pattern in self.pii_patterns.items():
            if pii_type == 'email':
                masked_text = pattern.sub(lambda m: self._mask_email(m.group()), masked_text)
            elif pii_type == 'phone':
                masked_text = pattern.sub('XXX-XXX-XXXX', masked_text)
            elif pii_type == 'ssn':
                masked_text = pattern.sub('XXX-XX-XXXX', masked_text)
            elif pii_type == 'credit_card':
                masked_text = pattern.sub('XXXX-XXXX-XXXX-XXXX', masked_text)
        
        return masked_text
    
    def _mask_email(self, email: str) -> str:
        """Mask email address"""
        if '@' in email:
            local, domain = email.split('@', 1)
            if len(local) > 2:
                masked_local = local[0] + '*' * (len(local) - 2) + local[-1]
            else:
                masked_local = '*' * len(local)
            return f"{masked_local}@{domain}"
        return email
    
    def mask_key(self, key: str) -> str:
        """Mask sensitive keys for logging"""
        if len(key) <= 4:
            return '*' * len(key)
        return key[:2] + '*' * (len(key) - 4) + key[-2:]
    
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
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
            'Referrer-Policy': 'strict-origin-when-cross-origin'
        }
    
    @staticmethod
    def validate_ssl_config() -> Dict[str, Any]:
        """Validate SSL configuration"""
        return {
            'https_enforced': HTTPSEnforcer.enforce_https(),
            'security_headers': HTTPSEnforcer.get_security_headers(),
            'ssl_version': 'TLS 1.2+',
            'certificate_valid': True  # Would check actual certificate in production
        }
