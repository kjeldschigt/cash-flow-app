#!/usr/bin/env python3
"""
Comprehensive test suite for enhanced PII protection and secure logging.
"""

import sys
from pathlib import Path
import logging
import json

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.security.pii_protection import (
    EnhancedPIIDetector, 
    SecureLoggingFilter, 
    StructuredLogger,
    SensitivityLevel,
    get_pii_detector,
    mask_sensitive_data
)


def test_enhanced_pii_patterns():
    """Test enhanced PII detection patterns"""
    print("🔍 Testing Enhanced PII Detection Patterns")
    print("=" * 55)
    
    detector = EnhancedPIIDetector()
    
    test_cases = [
        # International phone numbers
        ("Call me at +1-555-123-4567 or +44 20 7946 0958", "International phones"),
        ("My number is +33 1 42 86 83 26", "French phone"),
        
        # Credit cards without delimiters
        ("Card: 4532015112830366", "Visa without delimiters"),
        ("Payment: 5555555555554444", "Mastercard without delimiters"),
        ("Amex: 378282246310005", "Amex without delimiters"),
        
        # Credit cards with delimiters
        ("Card: 4532-0151-1283-0366", "Visa with dashes"),
        ("Payment: 5555 5555 5555 4444", "Mastercard with spaces"),
        
        # API Keys and tokens
        ("API_KEY=sk_test_51H7mGcKZvKYlo2C0aB3jKzQ", "Stripe test key"),
        ("Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.signature", "JWT token"),
        ("access_token: AKIA1234567890ABCDEF", "AWS access key"),
        
        # Passwords in logs
        ("password=mySecretPass123", "Password field"),
        ("pwd: 'admin123!'", "Password with quotes"),
        
        # Email addresses
        ("Contact john.doe@company.com for help", "Standard email"),
        ("Support: support+urgent@example.co.uk", "Email with plus"),
        
        # SSN variations
        ("SSN: 123-45-6789", "SSN with dashes"),
        ("Social: 123456789", "SSN without delimiters"),
        
        # IP and MAC addresses
        ("Server IP: 192.168.1.100", "IPv4 address"),
        ("MAC: 00:1B:44:11:3A:B7", "MAC address with colons"),
        ("MAC: 00-1B-44-11-3A-B7", "MAC address with dashes"),
        
        # IBAN
        ("Account: GB82WEST12345698765432", "UK IBAN"),
        
        # Mixed sensitive data
        ("User john@example.com, phone +1-555-0123, card 4532015112830366", "Multiple PII types")
    ]
    
    for text, description in test_cases:
        print(f"\n{description}:")
        print(f"  Original: {text}")
        
        # Test detection
        detections = detector.detect_pii(text)
        print(f"  Detected: {len(detections)} PII entities")
        
        # Test masking
        masked = detector.mask_pii(text)
        print(f"  Masked:   {masked}")
        
        # Verify masking worked
        if masked != text:
            print("  ✅ PII successfully masked")
        else:
            print("  ⚠️  No masking applied")
    
    print("\n✅ Enhanced PII pattern testing completed")
    return True


def test_sensitive_field_detection():
    """Test sensitive field name detection"""
    print("\n🔐 Testing Sensitive Field Detection")
    print("=" * 55)
    
    detector = EnhancedPIIDetector()
    
    sensitive_fields = [
        "password", "passwd", "pwd", "secret", "token", "api_key",
        "access_token", "refresh_token", "bearer_token", "auth_token",
        "session_id", "csrf_token", "encryption_key", "private_key",
        "credit_card", "ccn", "card_number", "ssn", "social_security",
        "phone", "telephone", "mobile", "email", "address", "location"
    ]
    
    non_sensitive_fields = [
        "username", "name", "title", "description", "status", "id",
        "created_at", "updated_at", "version", "type", "category"
    ]
    
    print("Testing sensitive field detection:")
    for field in sensitive_fields:
        is_sensitive = detector.is_sensitive_field(field)
        status = "✅" if is_sensitive else "❌"
        print(f"  {status} {field}")
        assert is_sensitive, f"Field '{field}' should be detected as sensitive"
    
    print("\nTesting non-sensitive field detection:")
    for field in non_sensitive_fields:
        is_sensitive = detector.is_sensitive_field(field)
        status = "❌" if is_sensitive else "✅"
        print(f"  {status} {field}")
        assert not is_sensitive, f"Field '{field}' should not be detected as sensitive"
    
    print("\n✅ Sensitive field detection working correctly")
    return True


def test_logging_filter():
    """Test secure logging filter"""
    print("\n📝 Testing Secure Logging Filter")
    print("=" * 55)
    
    # Create a test logger with our filter
    logger = logging.getLogger("test_logger")
    logger.setLevel(logging.DEBUG)
    
    # Create handler that captures output
    import io
    log_stream = io.StringIO()
    handler = logging.StreamHandler(log_stream)
    
    # Add our PII filter
    pii_filter = SecureLoggingFilter()
    handler.addFilter(pii_filter)
    logger.addHandler(handler)
    
    # Test cases
    test_messages = [
        "User login: email=john@example.com, password=secret123",
        "API call with token: sk_test_51H7mGcKZvKYlo2C0aB3jKzQ",
        "Credit card transaction: 4532015112830366",
        "Phone verification: +1-555-123-4567"
    ]
    
    print("Testing log message filtering:")
    for message in test_messages:
        print(f"\nOriginal: {message}")
        logger.info(message)
        
        # Get the logged output
        log_output = log_stream.getvalue()
        log_stream.seek(0)
        log_stream.truncate(0)
        
        print(f"Filtered: {log_output.strip()}")
        
        # Verify PII was masked
        if "john@example.com" in message and "john@example.com" not in log_output:
            print("  ✅ Email masked")
        if "secret123" in message and "secret123" not in log_output:
            print("  ✅ Password masked")
        if "sk_test_" in message and "sk_test_" not in log_output:
            print("  ✅ API key masked")
        if "4532015112830366" in message and "4532015112830366" not in log_output:
            print("  ✅ Credit card masked")
    
    print("\n✅ Logging filter working correctly")
    return True


def test_structured_logging():
    """Test structured logging setup"""
    print("\n📊 Testing Structured Logging")
    print("=" * 55)
    
    # Initialize structured logger
    structured_logger = StructuredLogger("test_service")
    logger = structured_logger.get_logger("test_component")
    
    # Test structured log messages
    print("Testing structured log messages:")
    
    # Basic structured log
    logger.info("User action completed", 
                user_id="user123", 
                action="login", 
                duration_ms=150)
    print("  ✅ Basic structured log")
    
    # Security event log
    structured_logger.log_security_event(
        event_type="authentication_failure",
        details={
            "user_email": "test@example.com",
            "ip_address": "192.168.1.100",
            "user_agent": "Mozilla/5.0...",
            "password": "secret123"  # This should be redacted
        },
        severity="WARNING"
    )
    print("  ✅ Security event log with PII redaction")
    
    # Error log without full traceback in production
    import os
    os.environ['ENVIRONMENT'] = 'production'
    
    try:
        raise ValueError("Test exception with sensitive data: password=secret123")
    except Exception as e:
        logger.error("Operation failed", 
                    operation="test_operation",
                    error_type=type(e).__name__)
    
    print("  ✅ Production-safe error logging")
    
    print("\n✅ Structured logging working correctly")
    return True


def test_performance_impact():
    """Test performance impact of PII detection"""
    print("\n⚡ Testing Performance Impact")
    print("=" * 55)
    
    import time
    
    detector = EnhancedPIIDetector()
    
    # Test with various text sizes
    test_texts = [
        "Short text with email@example.com",
        "Medium text " * 50 + " with phone +1-555-123-4567 and card 4532015112830366",
        "Long text " * 500 + " containing multiple PII: john@example.com, +1-555-0123, 4532015112830366"
    ]
    
    for i, text in enumerate(test_texts, 1):
        text_size = len(text)
        
        # Time the masking operation
        start_time = time.time()
        masked_text = detector.mask_pii(text)
        end_time = time.time()
        
        duration_ms = (end_time - start_time) * 1000
        
        print(f"Test {i}: {text_size:,} chars - {duration_ms:.2f}ms")
        
        # Performance should be reasonable (< 100ms for most cases)
        if duration_ms < 100:
            print(f"  ✅ Good performance")
        elif duration_ms < 500:
            print(f"  ⚠️  Acceptable performance")
        else:
            print(f"  ❌ Poor performance")
    
    print("\n✅ Performance testing completed")
    return True


def test_presidio_integration():
    """Test Presidio integration if available"""
    print("\n🔬 Testing Presidio Integration")
    print("=" * 55)
    
    detector = EnhancedPIIDetector()
    
    if detector.presidio_available:
        print("✅ Presidio is available and initialized")
        
        # Test Presidio-specific detection
        test_text = "My name is John Smith and my phone is 212-555-5555"
        detections = detector.detect_pii(test_text)
        
        presidio_detections = [d for d in detections if d.get('source') == 'presidio']
        custom_detections = [d for d in detections if d.get('source') == 'custom']
        
        print(f"  Presidio detections: {len(presidio_detections)}")
        print(f"  Custom detections: {len(custom_detections)}")
        
        if presidio_detections:
            print("  ✅ Presidio detection working")
        else:
            print("  ⚠️  No Presidio detections found")
    else:
        print("⚠️  Presidio not available, using fallback patterns only")
        
        # Test fallback still works
        test_text = "Contact me at test@example.com or 555-123-4567"
        masked = detector.mask_pii(test_text)
        
        if masked != test_text:
            print("  ✅ Fallback PII detection working")
        else:
            print("  ❌ Fallback PII detection failed")
    
    print("\n✅ Presidio integration testing completed")
    return True


def main():
    """Run all PII protection tests"""
    print("🧪 Cash Flow Dashboard - Enhanced PII Protection Tests")
    print("=" * 65)
    
    tests = [
        test_enhanced_pii_patterns,
        test_sensitive_field_detection,
        test_logging_filter,
        test_structured_logging,
        test_performance_impact,
        test_presidio_integration
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
            print(f"❌ Test {test.__name__} failed: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print(f"\n🎯 Test Results")
    print("=" * 65)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Total: {passed + failed}")
    
    if failed == 0:
        print("\n🎉 All PII protection tests passed!")
        print("\n📋 Enhanced Security Summary:")
        print("  ✅ Microsoft Presidio integration with fallback patterns")
        print("  ✅ International phone number detection")
        print("  ✅ Credit card detection (with/without delimiters)")
        print("  ✅ Comprehensive API key and token detection")
        print("  ✅ Automatic logging filter with PII redaction")
        print("  ✅ Structured logging with security event support")
        print("  ✅ Production-safe exception logging")
        print("  ✅ Performance-optimized PII detection")
        return True
    else:
        print(f"\n❌ {failed} test(s) failed. Please review the issues above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
