"""
Error handling service for comprehensive error management.
"""

import logging
import uuid
# Streamlit is optional for non-UI contexts (e.g., CLI smoke tests)
try:
    import streamlit as st  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    st = None  # type: ignore
from typing import Optional, Any, Dict
from datetime import datetime
from enum import Enum

from ..security.pii_protection import get_structured_logger

# Use structured logger with PII protection
logger = get_structured_logger().get_logger(__name__)


class ErrorHandler:
    """Centralized error handling service."""

    def __init__(self):
        self.logger = logger

    def handle_exception(
        self,
        exception: Exception,
        context: Optional[str] = None,
        user_id: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Handle exception with logging and user-friendly error message."""
        error_id = self._generate_error_id()

        # Log the exception with structured logging
        self.logger.error(
            "Exception occurred",
            error_id=error_id,
            error_type=type(exception).__name__,
            context=context or "unknown context",
            user_id=user_id,
            operation="handle_exception",
        )
        # Return user-friendly error response
        return {
            "success": False,
            "error_id": error_id,
            "message": self._get_user_friendly_message(exception),
            "type": type(exception).__name__,
            "timestamp": datetime.now().isoformat(),
        }

    def handle_validation_error(
        self, field: str, value: Any, message: str, context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Handle validation errors."""
        error_id = self._generate_error_id()

        self.logger.warning(
            "Validation error",
            error_id=error_id,
            field=field,
            message=message,
            context=context or "unknown context",
            operation="handle_validation_error",
        )
        return {
            "success": False,
            "error_id": error_id,
            "message": message,
            "field": field,
            "type": "ValidationError",
            "timestamp": datetime.now().isoformat(),
        }

    def handle_database_error(
        self,
        exception: Exception,
        operation: str,
        affected_table: Optional[str] = None,
        query_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Handle database-specific errors."""
        error_id = self._generate_error_id()

        self.logger.error(
            "Database error",
            error_id=error_id,
            error_type=type(exception).__name__,
            operation=operation,
            affected_table=affected_table,
            query_type=query_type,
        )

        return {
            "success": False,
            "error_id": error_id,
            "message": "A database error occurred. Please try again later.",
            "type": "DatabaseError",
            "operation": operation,
            "timestamp": datetime.now().isoformat(),
        }

    def handle_api_error(
        self,
        exception: Exception,
        service: str,
        endpoint: str,
        status_code: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Handle external API errors."""
        error_id = self._generate_error_id()

        self.logger.error(
            "API error",
            error_id=error_id,
            error_type=type(exception).__name__,
            service=service,
            endpoint=endpoint,
            status_code=status_code,
            operation="handle_api_error",
        )

        return {
            "success": False,
            "error_id": error_id,
            "message": f"Error connecting to {service}. Please check your configuration.",
            "type": "APIError",
            "service": service,
            "status_code": status_code,
            "timestamp": datetime.now().isoformat(),
        }

    def handle_authentication_error(
        self, message: str, user_identifier: Optional[str] = None
    ) -> Dict[str, Any]:
        """Handle authentication errors."""
        error_id = self._generate_error_id()

        self.logger.warning(
            "Authentication error",
            error_id=error_id,
            message=message,
            operation="handle_auth_error",
        )

        return {
            "success": False,
            "error_id": error_id,
            "message": message,
            "type": "AuthenticationError",
            "timestamp": datetime.now().isoformat(),
        }

    def handle_authorization_error(
        self,
        user_id: str,
        required_role: str,
        current_role: str,
        resource: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Handle authorization errors."""
        error_id = self._generate_error_id()

        self.logger.warning(
            "Authorization error",
            error_id=error_id,
            user_id=user_id,
            current_role=current_role,
            required_role=required_role,
            resource=resource or "resource",
            operation="handle_authorization_error",
        )

        return {
            "success": False,
            "error_id": error_id,
            "message": f"Access denied. {required_role.title()} role required.",
            "type": "AuthorizationError",
            "required_role": required_role,
            "timestamp": datetime.now().isoformat(),
        }

    def _generate_error_id(self) -> str:
        """Generate unique error ID for tracking."""
        import uuid

        return str(uuid.uuid4())[:8]

    def _get_user_friendly_message(self, exception: Exception) -> str:
        """Convert exception to user-friendly message."""
        exception_messages = {
            "ValueError": "Invalid input provided. Please check your data and try again.",
            "KeyError": "Required information is missing. Please ensure all fields are filled.",
            "FileNotFoundError": "Required file not found. Please check the file path.",
            "PermissionError": "Permission denied. Please check your access rights.",
            "ConnectionError": "Connection error. Please check your internet connection.",
            "TimeoutError": "Operation timed out. Please try again later.",
            "sqlite3.IntegrityError": "Data integrity error. This record may already exist.",
            "sqlite3.OperationalError": "Database operation failed. Please try again.",
        }

        exception_type = type(exception).__name__
        return exception_messages.get(
            exception_type,
            "An unexpected error occurred. Please try again or contact support.",
        )


def with_error_handling(context: str):
    """Decorator for automatic error handling."""

    def decorator(func):
        def wrapper(*args, **kwargs):
            error_handler = ErrorHandler()
            try:
                return func(*args, **kwargs)
            except Exception as e:
                return error_handler.handle_exception(e, context)

        return wrapper

    return decorator


# Global error handler instance
_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance."""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler


def handle_error(exception: Exception, message: str = None, context: str = None):
    """
    Handle errors with logging and user feedback.

    Args:
        exception: The exception that occurred
        message: Custom error message
        context: Context where error occurred
    """
    import uuid
    import logging

    # Generate unique error ID
    error_id = str(uuid.uuid4())[:8]

    # Log the error with full details
    logger = logging.getLogger(__name__)
    error_msg = f"Error {error_id}: {message or str(exception)}"
    if context:
        error_msg += f" (Context: {context})"

    # Use structured logger for consistent PII protection
    structured_logger = get_structured_logger().get_logger("error_handler")
    structured_logger.error(
        "Unhandled exception",
        error_type=type(exception).__name__,
        context=context,
        operation="handle_error",
    )

    # Show user-friendly message in Streamlit if available; else print to stdout
    user_message = message or "An unexpected error occurred"
    if st is not None:
        st.error(f"❌ {user_message} (Error ID: {error_id})")
    else:
        print(f"❌ {user_message} (Error ID: {error_id})")

    # In development, show more details
    import os

    if os.getenv("ENVIRONMENT", "development") == "development":
        if st is not None:
            with st.expander("🔍 Error Details (Development Mode)"):
                st.code(f"Exception: {type(exception).__name__}: {str(exception)}")
                if context:
                    st.code(f"Context: {context}")
                st.code(f"Error ID: {error_id}")
        else:
            print(f"Exception: {type(exception).__name__}: {str(exception)}")
            if context:
                print(f"Context: {context}")
            print(f"Error ID: {error_id}")

    return error_id


def error_handler_decorator(custom_message: str = None, context: str = None):
    """
    Decorator to handle errors in functions.

    Args:
        custom_message: Custom error message to display
        context: Context information for debugging
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                handle_error(e, custom_message, context or func.__name__)
                return None

        return wrapper

    return decorator


def show_error(message: str, exception: Exception = None):
    """
    Show error message in Streamlit - compatibility function.

    Args:
        message: Error message to display
        exception: Optional exception object
    """
    if exception:
        handle_error(exception, message)
    else:
        if st is not None:
            st.error(f"❌ {message}")
        else:
            print(f"❌ {message}")
