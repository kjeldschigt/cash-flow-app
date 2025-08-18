"""
Application-wide secure logging configuration and utilities.
Integrates enhanced PII protection with existing logging infrastructure.
"""

import os
import logging
from typing import Dict, Any, Optional

from ..security.pii_protection import (
    get_structured_logger,
    SecureLoggingFilter,
    get_pii_detector,
)


def setup_application_logging():
    """Setup secure logging for the entire application"""

    # Get environment
    environment = os.getenv("ENVIRONMENT", "development")

    # Configure root logger level based on environment
    log_level = logging.INFO if environment == "production" else logging.DEBUG
    logging.basicConfig(
        level=log_level,
        format="%(message)s",  # Structured logging handles formatting
        handlers=[],  # Will be configured by structured logger
    )

    # Initialize structured logger (this sets up the global configuration)
    structured_logger = get_structured_logger()

    # Add PII filter to all existing handlers
    pii_filter = SecureLoggingFilter()

    # Apply filter to root logger and all handlers
    root_logger = logging.getLogger()
    root_logger.addFilter(pii_filter)

    for handler in root_logger.handlers:
        handler.addFilter(pii_filter)

    # Configure specific loggers for different components
    component_loggers = [
        "src.services",
        "src.security",
        "src.repositories",
        "src.models",
        "src.ui",
        "streamlit",
        "requests",
        "urllib3",
    ]

    for logger_name in component_loggers:
        logger = logging.getLogger(logger_name)
        logger.addFilter(pii_filter)

        # Set appropriate levels
        if logger_name in ["requests", "urllib3"]:
            logger.setLevel(logging.WARNING)  # Reduce noise from HTTP libraries
        elif logger_name == "streamlit":
            logger.setLevel(logging.WARNING)  # Reduce Streamlit noise

    return structured_logger.get_logger("application")


def get_secure_logger(name: str) -> logging.Logger:
    """Get a logger with PII protection enabled"""
    structured_logger = get_structured_logger()
    return structured_logger.get_logger(name)


def log_security_event(
    event_type: str,
    details: Dict[str, Any],
    severity: str = "INFO",
    logger_name: str = "security",
):
    """Convenience function to log security events"""
    structured_logger = get_structured_logger()
    structured_logger.log_security_event(event_type, details, severity)


def mask_sensitive_log_data(data: Any) -> Any:
    """Mask sensitive data before logging"""
    pii_detector = get_pii_detector()

    if isinstance(data, str):
        return pii_detector.mask_pii(data)
    elif isinstance(data, dict):
        masked_dict = {}
        for key, value in data.items():
            if pii_detector.is_sensitive_field(key):
                masked_dict[key] = "{{REDACTED}}"
            elif isinstance(value, str):
                masked_dict[key] = pii_detector.mask_pii(value)
            elif isinstance(value, (dict, list)):
                masked_dict[key] = mask_sensitive_log_data(value)
            else:
                masked_dict[key] = value
        return masked_dict
    elif isinstance(data, list):
        return [mask_sensitive_log_data(item) for item in data]
    else:
        return data


def log_user_action(
    action: str,
    user_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    logger_name: str = "user_actions",
):
    """Log user actions with PII protection"""
    logger = get_secure_logger(logger_name)

    log_data = {
        "action": action,
        "user_id": user_id,
        "details": mask_sensitive_log_data(details) if details else None,
    }

    logger.info("User action", **log_data)


def log_api_call(
    service: str,
    endpoint: str,
    method: str = "GET",
    status_code: Optional[int] = None,
    duration_ms: Optional[float] = None,
    logger_name: str = "api_calls",
):
    """Log API calls with PII protection"""
    logger = get_secure_logger(logger_name)

    # Mask sensitive parts of endpoint
    masked_endpoint = get_pii_detector().mask_pii(endpoint)

    log_data = {
        "service": service,
        "endpoint": masked_endpoint,
        "method": method,
        "status_code": status_code,
        "duration_ms": duration_ms,
    }

    if status_code and status_code >= 400:
        logger.warning("API call failed", **log_data)
    else:
        logger.info("API call", **log_data)


def log_database_operation(
    operation: str,
    table: Optional[str] = None,
    duration_ms: Optional[float] = None,
    affected_rows: Optional[int] = None,
    logger_name: str = "database",
):
    """Log database operations with PII protection"""
    logger = get_secure_logger(logger_name)

    log_data = {
        "operation": operation,
        "table": table,
        "duration_ms": duration_ms,
        "affected_rows": affected_rows,
    }

    logger.info("Database operation", **log_data)


def log_performance_metric(
    metric_name: str,
    value: float,
    unit: str = "ms",
    context: Optional[Dict[str, Any]] = None,
    logger_name: str = "performance",
):
    """Log performance metrics"""
    logger = get_secure_logger(logger_name)

    log_data = {
        "metric": metric_name,
        "value": value,
        "unit": unit,
        "context": mask_sensitive_log_data(context) if context else None,
    }

    logger.info("Performance metric", **log_data)


# Initialize application logging when module is imported
_app_logger = None


def get_app_logger():
    """Get the main application logger"""
    global _app_logger
    if _app_logger is None:
        _app_logger = setup_application_logging()
    return _app_logger
