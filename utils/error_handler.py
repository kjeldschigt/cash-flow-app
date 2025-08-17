import streamlit as st
import pandas as pd
import traceback
from typing import Optional, Any, Union


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
