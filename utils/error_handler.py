import streamlit as st
import pandas as pd
import traceback
import logging
import functools
from typing import Optional, Any, Union, Dict, Callable
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

# Custom Exception Classes
class DataValidationError(Exception):
    """Raised when data validation fails"""
    def __init__(self, message: str, field_name: str = None, value: Any = None):
        self.field_name = field_name
        self.value = value
        super().__init__(message)

class ExternalAPIError(Exception):
    """Raised when external API calls fail"""
    def __init__(self, message: str, service_name: str = None, status_code: int = None):
        self.service_name = service_name
        self.status_code = status_code
        super().__init__(message)

class CalculationError(Exception):
    """Raised when financial calculations fail"""
    def __init__(self, message: str, operation: str = None, values: Dict = None):
        self.operation = operation
        self.values = values
        super().__init__(message)

class InsufficientDataError(Exception):
    """Raised when there's insufficient data for operations"""
    def __init__(self, message: str, required_count: int = None, actual_count: int = None):
        self.required_count = required_count
        self.actual_count = actual_count
        super().__init__(message)

# User-friendly error message mapping
ERROR_MESSAGES = {
    'DataValidationError': {
        'title': 'Data Validation Error',
        'message': 'The provided data is invalid or incomplete.',
        'suggestions': [
            'Check that all required fields are filled',
            'Verify data formats (dates, numbers, etc.)',
            'Ensure data is within acceptable ranges'
        ]
    },
    'ExternalAPIError': {
        'title': 'External Service Error',
        'message': 'Unable to connect to external service.',
        'suggestions': [
            'Check your internet connection',
            'Verify API keys and credentials',
            'Try again in a few minutes'
        ]
    },
    'CalculationError': {
        'title': 'Calculation Error',
        'message': 'An error occurred during financial calculations.',
        'suggestions': [
            'Check input values for validity',
            'Ensure no division by zero',
            'Verify data completeness'
        ]
    },
    'InsufficientDataError': {
        'title': 'Insufficient Data',
        'message': 'Not enough data available for this operation.',
        'suggestions': [
            'Add more data entries',
            'Expand the date range',
            'Check data filters'
        ]
    },
    'ValueError': {
        'title': 'Invalid Value',
        'message': 'The provided value is not in the correct format.',
        'suggestions': [
            'Check number formats',
            'Verify date formats',
            'Ensure text fields are not empty'
        ]
    },
    'KeyError': {
        'title': 'Missing Data Field',
        'message': 'Required data field is missing.',
        'suggestions': [
            'Check data source completeness',
            'Verify column names',
            'Update data import process'
        ]
    }
}

def get_user_friendly_message(exception: Exception) -> Dict[str, Any]:
    """Convert technical exception to user-friendly message"""
    exception_type = type(exception).__name__
    
    if exception_type in ERROR_MESSAGES:
        error_info = ERROR_MESSAGES[exception_type].copy()
        error_info['technical_details'] = str(exception)
        return error_info
    
    # Default fallback
    return {
        'title': 'Unexpected Error',
        'message': 'An unexpected error occurred.',
        'suggestions': [
            'Try refreshing the page',
            'Check your data inputs',
            'Contact support if the problem persists'
        ],
        'technical_details': str(exception)
    }

def global_error_handler(func: Callable) -> Callable:
    """Global error handler decorator with logging and user-friendly messages"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (DataValidationError, ExternalAPIError, CalculationError, InsufficientDataError) as e:
            # Log custom exceptions
            logger.error(f"Custom exception in {func.__name__}: {e}", exc_info=True)
            
            # Show user-friendly error
            error_info = get_user_friendly_message(e)
            show_user_friendly_error(error_info, e)
            
            return None
            
        except Exception as e:
            # Log unexpected exceptions
            logger.error(f"Unexpected exception in {func.__name__}: {e}", exc_info=True)
            
            # Show user-friendly error
            error_info = get_user_friendly_message(e)
            show_user_friendly_error(error_info, e)
            
            return None
    
    return wrapper

def show_user_friendly_error(error_info: Dict[str, Any], exception: Exception = None):
    """Display user-friendly error message with recovery suggestions"""
    st.error(f"**{error_info['title']}**")
    st.write(error_info['message'])
    
    if error_info.get('suggestions'):
        st.write("**Suggestions:**")
        for suggestion in error_info['suggestions']:
            st.write(f"• {suggestion}")
    
    # Show technical details in expander
    if error_info.get('technical_details'):
        with st.expander("Technical Details", expanded=False):
            st.code(error_info['technical_details'])
            
            if exception and hasattr(exception, '__dict__'):
                st.write("**Exception Attributes:**")
                for key, value in exception.__dict__.items():
                    st.write(f"• {key}: {value}")

def error_recovery_strategy(operation_type: str, fallback_data: Any = None) -> Any:
    """Implement error recovery strategies for common failures"""
    recovery_strategies = {
        'data_load': lambda: pd.DataFrame(),
        'calculation': lambda: {'result': 0, 'error': True},
        'api_call': lambda: {'data': [], 'success': False},
        'file_operation': lambda: None,
        'database_query': lambda: pd.DataFrame()
    }
    
    strategy = recovery_strategies.get(operation_type)
    if strategy:
        logger.info(f"Applying recovery strategy for {operation_type}")
        return strategy()
    
    return fallback_data

def validate_and_handle_data(data: Any, validation_func: Callable, 
                           error_message: str = "Data validation failed") -> bool:
    """Validate data and handle errors with user-friendly messages"""
    try:
        if validation_func(data):
            return True
        else:
            raise DataValidationError(error_message)
    except DataValidationError:
        raise
    except Exception as e:
        raise DataValidationError(f"{error_message}: {str(e)}")

def safe_api_call(api_func: Callable, service_name: str, 
                 fallback_data: Any = None, max_retries: int = 3) -> Any:
    """Safely execute API calls with retries and error handling"""
    for attempt in range(max_retries):
        try:
            result = api_func()
            logger.info(f"Successful API call to {service_name}")
            return result
            
        except Exception as e:
            logger.warning(f"API call to {service_name} failed (attempt {attempt + 1}): {e}")
            
            if attempt == max_retries - 1:
                # Final attempt failed
                raise ExternalAPIError(
                    f"Failed to connect to {service_name} after {max_retries} attempts",
                    service_name=service_name
                )
            
            # Wait before retry (exponential backoff)
            import time
            time.sleep(2 ** attempt)
    
    return fallback_data

def show_error(msg: str, details: Optional[Union[str, Exception]] = None, show_traceback: bool = False):
    """
    Display a user-friendly error message with optional details.
    
    Args:
        msg (str): Main error message to display
        details (Optional[Union[str, Exception]]): Additional error details or exception
        show_traceback (bool): Whether to show full traceback for debugging
    """
    st.error(msg)
    
    if details:
        with st.expander("Error Details", expanded=False):
            if isinstance(details, Exception):
                st.write(f"**Error Type:** {type(details).__name__}")
                st.write(f"**Error Message:** {str(details)}")
                
                if show_traceback:
                    st.code(traceback.format_exc(), language="python")
            else:
                st.write(str(details))


def handle_error(func):
    """
    Decorator to handle errors in Streamlit functions gracefully.
    
    Args:
        func: Function to wrap with error handling
        
    Returns:
        Wrapped function with error handling
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            show_error(
                f"An error occurred in {func.__name__}",
                details=e,
                show_traceback=True
            )
            return None
    return wrapper


def show_warning(msg: str, details: Optional[str] = None):
    """
    Display a warning message with optional details.
    
    Args:
        msg (str): Main warning message
        details (Optional[str]): Additional warning details
    """
    st.warning(msg)
    
    if details:
        with st.expander("Warning Details", expanded=False):
            st.write(details)


def show_info(msg: str, details: Optional[str] = None):
    """
    Display an info message with optional details.
    
    Args:
        msg (str): Main info message
        details (Optional[str]): Additional info details
    """
    st.info(msg)
    
    if details:
        with st.expander("Additional Information", expanded=False):
            st.write(details)


def safe_dataframe_operation(func, fallback_value=None, error_msg: str = "Data operation failed"):
    """
    Safely execute a DataFrame operation with fallback.
    
    Args:
        func: Function to execute
        fallback_value: Value to return if operation fails (default: empty DataFrame)
        error_msg: Error message to display
    
    Returns:
        Result of func() or fallback_value
    """
    try:
        result = func()
        return result
    except (ValueError, KeyError, TypeError, AttributeError) as e:
        show_error(error_msg, e)
        return fallback_value if fallback_value is not None else pd.DataFrame()
    except Exception as e:
        show_error(f"{error_msg} - Unexpected error", e)
        return fallback_value if fallback_value is not None else pd.DataFrame()


def validate_dataframe(df: pd.DataFrame, required_columns: Optional[list] = None, 
                      min_rows: int = 0, name: str = "DataFrame") -> bool:
    """
    Validate DataFrame structure and content.
    
    Args:
        df (pd.DataFrame): DataFrame to validate
        required_columns (Optional[list]): List of required column names
        min_rows (int): Minimum number of rows required
        name (str): Name of the DataFrame for error messages
    
    Returns:
        bool: True if valid, False otherwise
    """
    if df is None:
        show_error(f"{name} is None", "Expected a valid DataFrame")
        return False
    
    if df.empty:
        show_warning(f"{name} is empty", f"No data available in {name}")
        return False
    
    if len(df) < min_rows:
        show_warning(f"{name} has insufficient data", 
                    f"Expected at least {min_rows} rows, got {len(df)}")
        return False
    
    if required_columns:
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            show_error(f"{name} missing required columns", 
                      f"Missing columns: {missing_cols}")
            return False
    
    return True


def safe_numeric_operation(value: Any, operation: str = "conversion", 
                          fallback: float = 0.0) -> float:
    """
    Safely convert value to numeric with fallback.
    
    Args:
        value: Value to convert
        operation: Description of the operation
        fallback: Fallback value if conversion fails
    
    Returns:
        float: Converted value or fallback
    """
    try:
        if pd.isna(value) or value is None:
            return fallback
        return float(value)
    except (ValueError, TypeError) as e:
        show_warning(f"Numeric {operation} failed", 
                    f"Could not convert '{value}' to number, using {fallback}")
        return fallback


def safe_division(numerator: float, denominator: float, 
                 fallback: float = 0.0, operation: str = "division") -> float:
    """
    Safely perform division with zero-division protection.
    
    Args:
        numerator: Numerator value
        denominator: Denominator value
        fallback: Value to return if division by zero
        operation: Description of the operation
    
    Returns:
        float: Result of division or fallback
    """
    try:
        if denominator == 0:
            show_warning(f"Division by zero in {operation}", 
                        f"Using fallback value: {fallback}")
            return fallback
        return numerator / denominator
    except (TypeError, ValueError) as e:
        show_error(f"Error in {operation}", e)
        return fallback


def ensure_dataframe_columns(df: pd.DataFrame, required_columns: list, 
                           default_values: dict = None) -> pd.DataFrame:
    """
    Ensure DataFrame has required columns, adding missing ones with default values.
    
    Args:
        df (pd.DataFrame): Input DataFrame
        required_columns (list): List of required column names
        default_values (dict): Default values for missing columns
    
    Returns:
        pd.DataFrame: DataFrame with all required columns
    """
    if df.empty:
        # Create empty DataFrame with required columns
        return pd.DataFrame(columns=required_columns)
    
    df_copy = df.copy()
    default_values = default_values or {}
    
    for col in required_columns:
        if col not in df_copy.columns:
            default_val = default_values.get(col, 0 if col.endswith('_USD') or col.endswith('_CRC') else '')
            df_copy[col] = default_val
            show_info(f"Added missing column '{col}'", f"Using default value: {default_val}")
    
    return df_copy


def handle_api_error(error: Exception, service_name: str, fallback_data=None):
    """
    Handle API-related errors with service-specific messaging.
    
    Args:
        error (Exception): The API error
        service_name (str): Name of the service (e.g., 'Airtable', 'Stripe')
        fallback_data: Data to return if API fails
    
    Returns:
        Fallback data or empty DataFrame
    """
    error_details = f"Service: {service_name}\nError: {str(error)}"
    
    if "API key" in str(error).lower() or "unauthorized" in str(error).lower():
        show_error(f"{service_name} authentication failed", 
                  "Please check your API key configuration in the .env file")
    elif "network" in str(error).lower() or "connection" in str(error).lower():
        show_error(f"{service_name} connection failed", 
                  "Please check your internet connection and try again")
    else:
        show_error(f"{service_name} API error", error_details)
    
    return fallback_data if fallback_data is not None else pd.DataFrame()


def validate_number_input(value: float, field_name: str, min_val: float = None, 
                         max_val: float = None) -> bool:
    """
    Validate number input with min/max constraints.
    
    Args:
        value: The input value to validate
        field_name: Name of the field for error messages
        min_val: Minimum allowed value
        max_val: Maximum allowed value
    
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        if min_val is not None and value < min_val:
            show_error(f"Invalid {field_name}", f"Value must be at least {min_val}")
            return False
        
        if max_val is not None and value > max_val:
            show_error(f"Invalid {field_name}", f"Value must be at most {max_val}")
            return False
        
        return True
    except (TypeError, ValueError) as e:
        show_error(f"Invalid {field_name}", "Please enter a valid number")
        return False


def validate_date_range(start_date, end_date, field_name: str = "date range") -> bool:
    """
    Validate date range ensuring start <= end.
    
    Args:
        start_date: Start date
        end_date: End date
        field_name: Name of the field for error messages
    
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        if start_date and end_date and start_date > end_date:
            st.error(f"Invalid {field_name}: Start date must be before or equal to end date")
            return False
        return True
    except (TypeError, ValueError) as e:
        show_error(f"Invalid {field_name}", "Please enter valid dates")
        return False


def safe_form_input(form_function, error_msg: str = "Invalid input"):
    """
    Safely execute form input with error handling.
    
    Args:
        form_function: Function to execute
        error_msg: Error message to display
    
    Returns:
        Result of form_function or None if error
    """
    try:
        return form_function()
    except ValueError as e:
        st.warning(f"{error_msg} - use numbers only")
        return None
    except TypeError as e:
        st.warning(f"{error_msg} - invalid data type")
        return None
    except Exception as e:
        show_error(error_msg, e)
        return None
