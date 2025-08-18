"""
Enhanced Error Handling with Custom Exceptions and Recovery Strategies
"""

import logging
import traceback
import functools
from typing import Any, Dict, Optional, Type, Union, Callable
from datetime import datetime
from enum import Enum
import streamlit as st

# Custom Exception Classes
class CashFlowError(Exception):
    """Base exception for cash flow application errors"""
    def __init__(self, message: str, error_code: str = None, details: Dict = None):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        self.timestamp = datetime.now()
        super().__init__(self.message)

class DataValidationError(CashFlowError):
    """Raised when data validation fails"""
    pass

class ExternalAPIError(CashFlowError):
    """Raised when external API calls fail"""
    def __init__(self, message: str, service_name: str, status_code: int = None, **kwargs):
        self.service_name = service_name
        self.status_code = status_code
        super().__init__(message, **kwargs)

class CalculationError(CashFlowError):
    """Raised when financial calculations fail"""
    pass

class InsufficientDataError(CashFlowError):
    """Raised when insufficient data is available for operations"""
    pass

class DatabaseError(CashFlowError):
    """Raised when database operations fail"""
    pass

class AuthenticationError(CashFlowError):
    """Raised when authentication fails"""
    pass

class PermissionError(CashFlowError):
    """Raised when user lacks required permissions"""
    pass

# Error Severity Levels
class ErrorSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

# Error Recovery Strategies
class RecoveryStrategy(str, Enum):
    RETRY = "retry"
    FALLBACK = "fallback"
    SKIP = "skip"
    ABORT = "abort"
    USER_INPUT = "user_input"

class EnhancedErrorHandler:
    """Enhanced error handler with recovery strategies and user-friendly messages"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.error_counts = {}
        self.recovery_strategies = self._setup_recovery_strategies()
        self.user_messages = self._setup_user_messages()
    
    def _setup_recovery_strategies(self) -> Dict[Type[Exception], RecoveryStrategy]:
        """Setup default recovery strategies for different error types"""
        return {
            DataValidationError: RecoveryStrategy.USER_INPUT,
            ExternalAPIError: RecoveryStrategy.RETRY,
            CalculationError: RecoveryStrategy.FALLBACK,
            InsufficientDataError: RecoveryStrategy.SKIP,
            DatabaseError: RecoveryStrategy.RETRY,
            AuthenticationError: RecoveryStrategy.ABORT,
            PermissionError: RecoveryStrategy.ABORT,
            ConnectionError: RecoveryStrategy.RETRY,
            TimeoutError: RecoveryStrategy.RETRY,
            ValueError: RecoveryStrategy.FALLBACK,
            KeyError: RecoveryStrategy.FALLBACK,
        }
    
    def _setup_user_messages(self) -> Dict[Type[Exception], str]:
        """Setup user-friendly error messages"""
        return {
            DataValidationError: "The data you entered doesn't meet our requirements. Please check and try again.",
            ExternalAPIError: "We're having trouble connecting to an external service. Please try again in a moment.",
            CalculationError: "We encountered an issue with the financial calculations. Using fallback values.",
            InsufficientDataError: "There isn't enough data available for this operation. Please add more data first.",
            DatabaseError: "We're experiencing database issues. Please try again shortly.",
            AuthenticationError: "Authentication failed. Please log in again.",
            PermissionError: "You don't have permission to perform this action.",
            ConnectionError: "Network connection issue. Please check your internet connection.",
            TimeoutError: "The operation timed out. Please try again.",
            ValueError: "Invalid data format detected. Using default values.",
            KeyError: "Required data field is missing. Using fallback approach.",
        }
    
    def get_error_severity(self, error: Exception) -> ErrorSeverity:
        """Determine error severity based on error type and context"""
        if isinstance(error, (AuthenticationError, PermissionError, DatabaseError)):
            return ErrorSeverity.CRITICAL
        elif isinstance(error, (ExternalAPIError, CalculationError)):
            return ErrorSeverity.HIGH
        elif isinstance(error, (DataValidationError, InsufficientDataError)):
            return ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.LOW
    
    def log_error(self, error: Exception, context: Dict = None, user_id: str = None):
        """Log error with context and user information"""
        severity = self.get_error_severity(error)
        
        error_info = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'severity': severity.value,
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'context': context or {},
            'traceback': traceback.format_exc() if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL] else None
        }
        
        # Log based on severity
        if severity == ErrorSeverity.CRITICAL:
            self.logger.critical(f"Critical error: {error_info}")
        elif severity == ErrorSeverity.HIGH:
            self.logger.error(f"High severity error: {error_info}")
        elif severity == ErrorSeverity.MEDIUM:
            self.logger.warning(f"Medium severity error: {error_info}")
        else:
            self.logger.info(f"Low severity error: {error_info}")
        
        # Track error counts for monitoring
        error_key = f"{type(error).__name__}:{user_id or 'anonymous'}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
    
    def display_user_error(self, error: Exception, show_details: bool = False):
        """Display user-friendly error message in Streamlit"""
        severity = self.get_error_severity(error)
        user_message = self.user_messages.get(type(error), "An unexpected error occurred. Please try again.")
        
        # Choose Streamlit display method based on severity
        if severity == ErrorSeverity.CRITICAL:
            st.error(f"🚨 Critical Error: {user_message}")
        elif severity == ErrorSeverity.HIGH:
            st.error(f"⚠️ Error: {user_message}")
        elif severity == ErrorSeverity.MEDIUM:
            st.warning(f"⚠️ Warning: {user_message}")
        else:
            st.info(f"ℹ️ Notice: {user_message}")
        
        # Show technical details if requested and appropriate
        if show_details and severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            with st.expander("Technical Details", expanded=False):
                st.code(f"Error Type: {type(error).__name__}")
                st.code(f"Error Message: {str(error)}")
                if hasattr(error, 'error_code'):
                    st.code(f"Error Code: {error.error_code}")
                if hasattr(error, 'details'):
                    st.json(error.details)
    
    def handle_error(self, error: Exception, context: Dict = None, user_id: str = None, 
                    show_to_user: bool = True, fallback_value: Any = None) -> Any:
        """Comprehensive error handling with logging and user display"""
        # Log the error
        self.log_error(error, context, user_id)
        
        # Display to user if requested
        if show_to_user:
            self.display_user_error(error)
        
        # Apply recovery strategy
        recovery_strategy = self.recovery_strategies.get(type(error), RecoveryStrategy.FALLBACK)
        
        if recovery_strategy == RecoveryStrategy.FALLBACK:
            return fallback_value
        elif recovery_strategy == RecoveryStrategy.SKIP:
            return None
        elif recovery_strategy == RecoveryStrategy.ABORT:
            st.stop()
        else:
            return fallback_value

def error_handler(fallback_value: Any = None, show_to_user: bool = True, 
                 context: Dict = None, retry_count: int = 0):
    """Decorator for automatic error handling"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            handler = EnhancedErrorHandler()
            user_id = getattr(st.session_state, 'user', {}).get('email', 'anonymous')
            
            for attempt in range(retry_count + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == retry_count:  # Last attempt
                        func_context = {
                            'function': func.__name__,
                            'args': str(args)[:100],  # Truncate for logging
                            'kwargs': str(kwargs)[:100],
                            'attempt': attempt + 1,
                            **(context or {})
                        }
                        return handler.handle_error(
                            e, func_context, user_id, show_to_user, fallback_value
                        )
                    else:
                        # Wait before retry (simple exponential backoff)
                        import time
                        time.sleep(2 ** attempt)
            
            return fallback_value
        return wrapper
    return decorator

def validate_and_handle(validation_func: Callable, error_message: str = None):
    """Decorator for validation with error handling"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                # Run validation
                if not validation_func(*args, **kwargs):
                    raise DataValidationError(
                        error_message or f"Validation failed for {func.__name__}"
                    )
                return func(*args, **kwargs)
            except Exception as e:
                handler = EnhancedErrorHandler()
                user_id = getattr(st.session_state, 'user', {}).get('email', 'anonymous')
                return handler.handle_error(e, {'function': func.__name__}, user_id)
        return wrapper
    return decorator

# Convenience functions for common error scenarios
def handle_api_error(func: Callable, service_name: str, fallback_data: Any = None):
    """Handle API errors with service-specific context"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            api_error = ExternalAPIError(
                f"Failed to connect to {service_name}: {str(e)}",
                service_name=service_name,
                details={'original_error': str(e)}
            )
            handler = EnhancedErrorHandler()
            user_id = getattr(st.session_state, 'user', {}).get('email', 'anonymous')
            return handler.handle_error(api_error, {'service': service_name}, user_id, fallback_value=fallback_data)
    return wrapper

def handle_calculation_error(func: Callable, calculation_name: str, fallback_value: float = 0.0):
    """Handle calculation errors with mathematical context"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (ZeroDivisionError, ValueError, TypeError, OverflowError) as e:
            calc_error = CalculationError(
                f"Calculation '{calculation_name}' failed: {str(e)}",
                details={'calculation': calculation_name, 'inputs': str(args)[:100]}
            )
            handler = EnhancedErrorHandler()
            user_id = getattr(st.session_state, 'user', {}).get('email', 'anonymous')
            return handler.handle_error(calc_error, {'calculation': calculation_name}, user_id, fallback_value=fallback_value)
    return wrapper

def safe_execute(func: Callable, *args, fallback_value: Any = None, error_context: str = None, **kwargs):
    """Safely execute any function with error handling"""
    handler = EnhancedErrorHandler()
    user_id = getattr(st.session_state, 'user', {}).get('email', 'anonymous')
    
    try:
        return func(*args, **kwargs)
    except Exception as e:
        context = {'function': func.__name__, 'context': error_context} if error_context else {'function': func.__name__}
        return handler.handle_error(e, context, user_id, fallback_value=fallback_value)

# Global error handler instance
global_error_handler = EnhancedErrorHandler()

# Backward compatibility with existing error_handler.py
def handle_error(error: Exception, message: str = None, show_details: bool = False):
    """Backward compatibility function"""
    user_id = getattr(st.session_state, 'user', {}).get('email', 'anonymous')
    context = {'message': message} if message else None
    global_error_handler.handle_error(error, context, user_id, show_to_user=True)
