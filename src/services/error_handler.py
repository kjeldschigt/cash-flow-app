"""
Error handling service for comprehensive error management.
"""

import traceback
import sys
from typing import Any, Dict, Optional, Type
from datetime import datetime
from .logging_service import get_logger


class ErrorHandler:
    """Centralized error handling service."""
    
    def __init__(self):
        self.logger = get_logger()
    
    def handle_exception(
        self,
        exception: Exception,
        context: Optional[str] = None,
        user_id: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle exception with logging and user-friendly error message."""
        error_id = self._generate_error_id()
        
        # Log the full exception details
        self.logger.error(
            f"Exception in {context or 'unknown context'} [ID: {error_id}]",
            exception=exception,
            user_id=user_id,
            error_id=error_id,
            additional_data=additional_data
        )
        
        # Return user-friendly error response
        return {
            'success': False,
            'error_id': error_id,
            'message': self._get_user_friendly_message(exception),
            'type': type(exception).__name__,
            'timestamp': datetime.now().isoformat()
        }
    
    def handle_validation_error(
        self,
        field: str,
        value: Any,
        message: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Handle validation errors."""
        error_id = self._generate_error_id()
        
        self.logger.warning(
            f"Validation error in {context or 'unknown context'} [ID: {error_id}]: {field} = {value} - {message}",
            field=field,
            value=str(value),
            error_id=error_id
        )
        
        return {
            'success': False,
            'error_id': error_id,
            'message': message,
            'field': field,
            'type': 'ValidationError',
            'timestamp': datetime.now().isoformat()
        }
    
    def handle_database_error(
        self,
        exception: Exception,
        operation: str,
        table: Optional[str] = None,
        query: Optional[str] = None
    ) -> Dict[str, Any]:
        """Handle database-specific errors."""
        error_id = self._generate_error_id()
        
        self.logger.error(
            f"Database error during {operation} [ID: {error_id}]",
            exception=exception,
            operation=operation,
            table=table,
            query=query,
            error_id=error_id
        )
        
        return {
            'success': False,
            'error_id': error_id,
            'message': "A database error occurred. Please try again later.",
            'type': 'DatabaseError',
            'operation': operation,
            'timestamp': datetime.now().isoformat()
        }
    
    def handle_api_error(
        self,
        exception: Exception,
        service: str,
        endpoint: str,
        status_code: Optional[int] = None
    ) -> Dict[str, Any]:
        """Handle external API errors."""
        error_id = self._generate_error_id()
        
        self.logger.error(
            f"API error with {service} at {endpoint} [ID: {error_id}]",
            exception=exception,
            service=service,
            endpoint=endpoint,
            status_code=status_code,
            error_id=error_id
        )
        
        return {
            'success': False,
            'error_id': error_id,
            'message': f"Error connecting to {service}. Please check your configuration.",
            'type': 'APIError',
            'service': service,
            'status_code': status_code,
            'timestamp': datetime.now().isoformat()
        }
    
    def handle_authentication_error(
        self,
        message: str,
        user_identifier: Optional[str] = None
    ) -> Dict[str, Any]:
        """Handle authentication errors."""
        error_id = self._generate_error_id()
        
        self.logger.warning(
            f"Authentication error [ID: {error_id}]: {message}",
            user_identifier=user_identifier,
            error_id=error_id
        )
        
        return {
            'success': False,
            'error_id': error_id,
            'message': message,
            'type': 'AuthenticationError',
            'timestamp': datetime.now().isoformat()
        }
    
    def handle_authorization_error(
        self,
        user_id: str,
        required_role: str,
        current_role: str,
        resource: Optional[str] = None
    ) -> Dict[str, Any]:
        """Handle authorization errors."""
        error_id = self._generate_error_id()
        
        self.logger.warning(
            f"Authorization error [ID: {error_id}]: User {user_id} with role {current_role} "
            f"attempted to access {resource or 'resource'} requiring {required_role}",
            user_id=user_id,
            required_role=required_role,
            current_role=current_role,
            resource=resource,
            error_id=error_id
        )
        
        return {
            'success': False,
            'error_id': error_id,
            'message': f"Access denied. {required_role.title()} role required.",
            'type': 'AuthorizationError',
            'required_role': required_role,
            'timestamp': datetime.now().isoformat()
        }
    
    def _generate_error_id(self) -> str:
        """Generate unique error ID for tracking."""
        import uuid
        return str(uuid.uuid4())[:8]
    
    def _get_user_friendly_message(self, exception: Exception) -> str:
        """Convert exception to user-friendly message."""
        exception_messages = {
            'ValueError': 'Invalid input provided. Please check your data and try again.',
            'KeyError': 'Required information is missing. Please ensure all fields are filled.',
            'FileNotFoundError': 'Required file not found. Please check the file path.',
            'PermissionError': 'Permission denied. Please check your access rights.',
            'ConnectionError': 'Connection error. Please check your internet connection.',
            'TimeoutError': 'Operation timed out. Please try again later.',
            'sqlite3.IntegrityError': 'Data integrity error. This record may already exist.',
            'sqlite3.OperationalError': 'Database operation failed. Please try again.',
        }
        
        exception_type = type(exception).__name__
        return exception_messages.get(
            exception_type,
            'An unexpected error occurred. Please try again or contact support.'
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
