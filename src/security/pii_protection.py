"""
Enhanced PII Protection and Logging Security
Comprehensive PII detection and redaction using Microsoft Presidio with custom patterns.
"""

import os
import re
import logging
import structlog
from typing import Dict, List, Optional, Set, Any, Union
from dataclasses import dataclass
from enum import Enum

try:
    from presidio_analyzer import AnalyzerEngine
    from presidio_anonymizer import AnonymizerEngine
    from presidio_analyzer.nlp_engine import NlpEngineProvider

    PRESIDIO_AVAILABLE = True
except ImportError:
    PRESIDIO_AVAILABLE = False
    logging.warning("Presidio not available. Using fallback PII detection.")


class SensitivityLevel(str, Enum):
    """Sensitivity levels for different types of data"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PIIPattern:
    """PII pattern definition"""

    name: str
    pattern: str
    replacement: str
    sensitivity: SensitivityLevel
    description: str


class EnhancedPIIDetector:
    """Enhanced PII detection using Presidio with custom patterns"""

    def __init__(self):
        self.presidio_available = PRESIDIO_AVAILABLE
        self.analyzer = None
        self.anonymizer = None

        if self.presidio_available:
            try:
                # Initialize Presidio engines
                self.analyzer = AnalyzerEngine()
                self.anonymizer = AnonymizerEngine()
            except Exception as e:
                logging.warning(f"Failed to initialize Presidio: {e}")
                self.presidio_available = False

        # Custom PII patterns for fallback and enhancement
        self.custom_patterns = self._initialize_custom_patterns()

        # Compiled regex patterns for performance
        self._compiled_patterns = {}
        self._compile_patterns()

    def _initialize_custom_patterns(self) -> List[PIIPattern]:
        """Initialize comprehensive PII patterns"""
        return [
            # Enhanced phone number patterns (international)
            PIIPattern(
                name="PHONE_INTERNATIONAL",
                pattern=r"(?:\+?1[-.\s]?)?(?:\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4})|(?:\+[1-9]\d{1,14})",
                replacement="{{PHONE}}",
                sensitivity=SensitivityLevel.MEDIUM,
                description="International phone numbers including US format",
            ),
            # Credit card patterns (with and without delimiters)
            PIIPattern(
                name="CREDIT_CARD_NO_DELIM",
                pattern=r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3[0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b",
                replacement="{{CREDIT_CARD}}",
                sensitivity=SensitivityLevel.HIGH,
                description="Credit card numbers without delimiters",
            ),
            PIIPattern(
                name="CREDIT_CARD_WITH_DELIM",
                pattern=r"\b(?:4[0-9]{3}[-\s]?[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{4}|5[1-5][0-9]{2}[-\s]?[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{4})\b",
                replacement="{{CREDIT_CARD}}",
                sensitivity=SensitivityLevel.HIGH,
                description="Credit card numbers with delimiters",
            ),
            # Enhanced email patterns
            PIIPattern(
                name="EMAIL_ENHANCED",
                pattern=r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                replacement="{{EMAIL}}",
                sensitivity=SensitivityLevel.MEDIUM,
                description="Email addresses",
            ),
            # SSN patterns (various formats)
            PIIPattern(
                name="SSN_FLEXIBLE",
                pattern=r"\b(?:\d{3}[-.\s]?\d{2}[-.\s]?\d{4}|\d{9})\b",
                replacement="{{SSN}}",
                sensitivity=SensitivityLevel.HIGH,
                description="Social Security Numbers (flexible format)",
            ),
            # API Keys and tokens
            PIIPattern(
                name="API_KEY_GENERIC",
                pattern=r'\b(?:api[_-]?key|access[_-]?token|secret[_-]?key|bearer[_-]?token)[\s=:]+["\']?([A-Za-z0-9+/=_-]{20,})["\']?',
                replacement="{{API_KEY}}",
                sensitivity=SensitivityLevel.CRITICAL,
                description="Generic API keys and tokens",
            ),
            # Stripe keys
            PIIPattern(
                name="STRIPE_KEY",
                pattern=r"\b(?:sk|pk|rk)_(?:test|live)_[A-Za-z0-9]{24,}\b",
                replacement="{{STRIPE_KEY}}",
                sensitivity=SensitivityLevel.CRITICAL,
                description="Stripe API keys",
            ),
            # AWS keys
            PIIPattern(
                name="AWS_ACCESS_KEY",
                pattern=r"\bAKIA[0-9A-Z]{16}\b",
                replacement="{{AWS_KEY}}",
                sensitivity=SensitivityLevel.CRITICAL,
                description="AWS Access Keys",
            ),
            # JWT tokens
            PIIPattern(
                name="JWT_TOKEN",
                pattern=r"\beyJ[A-Za-z0-9+/=]+\.[A-Za-z0-9+/=]+\.[A-Za-z0-9+/=_-]+\b",
                replacement="{{JWT_TOKEN}}",
                sensitivity=SensitivityLevel.CRITICAL,
                description="JWT tokens",
            ),
            # Password patterns in logs
            PIIPattern(
                name="PASSWORD_FIELD",
                pattern=r'(?i)(?:password|passwd|pwd)[\s=:]+["\']?([^\s"\']{6,})["\']?',
                replacement="{{PASSWORD}}",
                sensitivity=SensitivityLevel.CRITICAL,
                description="Password fields",
            ),
            # Encryption keys
            PIIPattern(
                name="ENCRYPTION_KEY",
                pattern=r"\b(?:-----BEGIN[A-Z\s]+KEY-----|[A-Za-z0-9+/=]{32,}(?:==|=)?)\b",
                replacement="{{ENCRYPTION_KEY}}",
                sensitivity=SensitivityLevel.CRITICAL,
                description="Encryption keys and certificates",
            ),
            # IP Addresses
            PIIPattern(
                name="IP_ADDRESS",
                pattern=r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b",
                replacement="{{IP_ADDRESS}}",
                sensitivity=SensitivityLevel.MEDIUM,
                description="IPv4 addresses",
            ),
            # MAC Addresses
            PIIPattern(
                name="MAC_ADDRESS",
                pattern=r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b",
                replacement="{{MAC_ADDRESS}}",
                sensitivity=SensitivityLevel.MEDIUM,
                description="MAC addresses",
            ),
            # IBAN (International Bank Account Number)
            PIIPattern(
                name="IBAN",
                pattern=r"\b[A-Z]{2}[0-9]{2}[A-Z0-9]{4}[0-9]{7}([A-Z0-9]?){0,16}\b",
                replacement="{{IBAN}}",
                sensitivity=SensitivityLevel.HIGH,
                description="International Bank Account Numbers",
            ),
            # Driver's License (US format)
            PIIPattern(
                name="DRIVERS_LICENSE",
                pattern=r"\b[A-Z]{1,2}[0-9]{6,8}\b",
                replacement="{{DRIVERS_LICENSE}}",
                sensitivity=SensitivityLevel.HIGH,
                description="US Driver's License numbers",
            ),
        ]

    def _compile_patterns(self):
        """Compile regex patterns for better performance"""
        for pattern in self.custom_patterns:
            try:
                self._compiled_patterns[pattern.name] = re.compile(
                    pattern.pattern, re.IGNORECASE | re.MULTILINE
                )
            except re.error as e:
                logging.warning(f"Failed to compile pattern {pattern.name}: {e}")

    def detect_pii(self, text: str, language: str = "en") -> List[Dict[str, Any]]:
        """Detect PII in text using Presidio and custom patterns"""
        results = []

        # Use Presidio if available
        if self.presidio_available and self.analyzer:
            try:
                presidio_results = self.analyzer.analyze(
                    text=text, language=language, entities=None  # Detect all entities
                )

                for result in presidio_results:
                    results.append(
                        {
                            "entity_type": result.entity_type,
                            "start": result.start,
                            "end": result.end,
                            "score": result.score,
                            "source": "presidio",
                        }
                    )
            except Exception as e:
                logging.warning(f"Presidio analysis failed: {e}")

        # Add custom pattern detection
        for pattern in self.custom_patterns:
            if pattern.name in self._compiled_patterns:
                regex = self._compiled_patterns[pattern.name]
                for match in regex.finditer(text):
                    results.append(
                        {
                            "entity_type": pattern.name,
                            "start": match.start(),
                            "end": match.end(),
                            "score": 1.0,
                            "source": "custom",
                            "sensitivity": pattern.sensitivity.value,
                        }
                    )

        return results

    def mask_pii(self, text: str, language: str = "en") -> str:
        """Mask PII in text"""
        if not text:
            return text

        masked_text = text

        # Use Presidio anonymizer if available
        if self.presidio_available and self.anonymizer and self.analyzer:
            try:
                analyzer_results = self.analyzer.analyze(text=text, language=language)

                if analyzer_results:
                    anonymized_result = self.anonymizer.anonymize(
                        text=text, analyzer_results=analyzer_results
                    )
                    masked_text = anonymized_result.text
            except Exception as e:
                logging.warning(f"Presidio anonymization failed: {e}")

        # Apply custom pattern masking
        for pattern in self.custom_patterns:
            if pattern.name in self._compiled_patterns:
                regex = self._compiled_patterns[pattern.name]
                masked_text = regex.sub(pattern.replacement, masked_text)

        return masked_text

    def is_sensitive_field(self, field_name: str) -> bool:
        """Check if a field name indicates sensitive data"""
        sensitive_fields = {
            "password",
            "passwd",
            "pwd",
            "secret",
            "token",
            "key",
            "api_key",
            "access_token",
            "refresh_token",
            "bearer_token",
            "auth_token",
            "session_id",
            "csrf_token",
            "encryption_key",
            "private_key",
            "credit_card",
            "ccn",
            "card_number",
            "ssn",
            "social_security",
            "phone",
            "telephone",
            "mobile",
            "email",
            "address",
            "location",
            "ip_address",
            "mac_address",
            "iban",
            "account_number",
            "routing_number",
        }

        field_lower = field_name.lower()
        return any(sensitive in field_lower for sensitive in sensitive_fields)


class SecureLoggingFilter(logging.Filter):
    """Logging filter that automatically redacts PII and sensitive data"""

    def __init__(self, pii_detector: Optional[EnhancedPIIDetector] = None):
        super().__init__()
        self.pii_detector = pii_detector or EnhancedPIIDetector()
        self.environment = os.getenv("ENVIRONMENT", "development")

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter and redact sensitive information from log records"""
        try:
            # Redact the main message
            if hasattr(record, "msg") and record.msg:
                record.msg = self.pii_detector.mask_pii(str(record.msg))

            # Redact arguments
            if hasattr(record, "args") and record.args:
                cleaned_args = []
                for arg in record.args:
                    if isinstance(arg, str):
                        cleaned_args.append(self.pii_detector.mask_pii(arg))
                    elif isinstance(arg, dict):
                        cleaned_args.append(self._clean_dict(arg))
                    else:
                        cleaned_args.append(arg)
                record.args = tuple(cleaned_args)

            # In production, never log full tracebacks for exceptions
            if self.environment == "production" and record.exc_info:
                # Keep exception type and message, but remove traceback
                exc_type, exc_value, exc_traceback = record.exc_info
                if exc_value:
                    record.msg = f"{record.msg} | Exception: {exc_type.__name__}: {str(exc_value)}"
                record.exc_info = None
                record.exc_text = None

        except Exception as e:
            # If filtering fails, log the error but don't break logging
            print(f"Logging filter error: {e}")

        return True

    def _clean_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean sensitive data from dictionary"""
        if not isinstance(data, dict):
            return data

        cleaned = {}
        for key, value in data.items():
            if self.pii_detector.is_sensitive_field(key):
                cleaned[key] = "{{REDACTED}}"
            elif isinstance(value, str):
                cleaned[key] = self.pii_detector.mask_pii(value)
            elif isinstance(value, dict):
                cleaned[key] = self._clean_dict(value)
            elif isinstance(value, list):
                cleaned[key] = [
                    (
                        self.pii_detector.mask_pii(item)
                        if isinstance(item, str)
                        else self._clean_dict(item) if isinstance(item, dict) else item
                    )
                    for item in value
                ]
            else:
                cleaned[key] = value

        return cleaned


class StructuredLogger:
    """Structured logging setup with PII protection"""

    def __init__(self, service_name: str = "cash_flow_dashboard"):
        self.service_name = service_name
        self.pii_detector = EnhancedPIIDetector()
        self.environment = os.getenv("ENVIRONMENT", "development")
        self._setup_logging()

    def _setup_logging(self):
        """Setup structured logging with PII protection"""
        # Configure structlog
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer(),
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

        # Setup standard logging with PII filter
        logging.basicConfig(
            level=logging.INFO if self.environment == "production" else logging.DEBUG,
            format="%(message)s",
        )

        # Add PII filter to all handlers
        pii_filter = SecureLoggingFilter(self.pii_detector)
        for handler in logging.root.handlers:
            handler.addFilter(pii_filter)

    def get_logger(self, name: str = None) -> structlog.stdlib.BoundLogger:
        """Get a structured logger instance"""
        logger_name = name or self.service_name
        return structlog.get_logger(logger_name)

    def log_security_event(
        self, event_type: str, details: Dict[str, Any], severity: str = "INFO"
    ) -> None:
        """Log security events with proper structure"""
        logger = self.get_logger("security")

        # Clean sensitive data from details
        pii_filter = SecureLoggingFilter(self.pii_detector)
        cleaned_details = pii_filter._clean_dict(details)

        log_data = {
            "event_type": event_type,
            "severity": severity,
            "environment": self.environment,
            "service": self.service_name,
            "details": cleaned_details,
        }

        if severity.upper() == "ERROR":
            logger.error("Security event", **log_data)
        elif severity.upper() == "WARNING":
            logger.warning("Security event", **log_data)
        else:
            logger.info("Security event", **log_data)


# Global instances
_pii_detector = None
_structured_logger = None


def get_pii_detector() -> EnhancedPIIDetector:
    """Get global PII detector instance"""
    global _pii_detector
    if _pii_detector is None:
        _pii_detector = EnhancedPIIDetector()
    return _pii_detector


def get_structured_logger() -> StructuredLogger:
    """Get global structured logger instance"""
    global _structured_logger
    if _structured_logger is None:
        _structured_logger = StructuredLogger()
    return _structured_logger


def mask_sensitive_data(text: str) -> str:
    """Convenience function to mask PII in text"""
    detector = get_pii_detector()
    return detector.mask_pii(text)


def setup_secure_logging():
    """Setup secure logging for the application"""
    logger_instance = get_structured_logger()
    return logger_instance.get_logger()
