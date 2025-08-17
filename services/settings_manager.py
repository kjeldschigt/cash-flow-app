import streamlit as st
import sqlite3
import os
from typing import Any, Union

# Database path
DB_PATH = "cashflow.db"

@st.cache_data
def load_from_db(key: str, default: Any = None) -> Any:
    """Load a setting from the database with caching."""
    try:
        if not os.path.exists(DB_PATH):
            return default
            
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create settings table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        # Get the setting
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        result = cursor.fetchone()
        
        conn.close()
        
        if result:
            # Try to convert back to appropriate type
            value = result[0]
            # Handle common types
            if value.lower() in ('true', 'false'):
                return value.lower() == 'true'
            try:
                # Try int first
                if '.' not in value:
                    return int(value)
                else:
                    return float(value)
            except ValueError:
                return value  # Return as string
        
        return default
        
    except Exception as e:
        st.error(f"Error loading setting {key}: {e}")
        return default

def save_to_db(key: str, value: Any) -> None:
    """Save a setting to the database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create settings table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        # Convert value to string for storage
        str_value = str(value)
        
        # Insert or update the setting
        cursor.execute('''
            INSERT OR REPLACE INTO settings (key, value) 
            VALUES (?, ?)
        ''', (key, str_value))
        
        conn.commit()
        conn.close()
        
        # Clear cache for this key
        load_from_db.clear()
        
    except Exception as e:
        st.error(f"Error saving setting {key}: {e}")

def validate_setting(key: str, value: Any) -> None:
    """Validate setting values based on key."""
    if key == 'occupancy' and value < 0:
        raise ValueError("Occupancy rate cannot be negative")
    
    if key == 'rent_per_sqft' and value < 0:
        raise ValueError("Rent per square foot cannot be negative")
    
    if key == 'square_feet' and value <= 0:
        raise ValueError("Square feet must be positive")
    
    if key in ['costa_usd_cr', 'google_ads', 'stripe_fees'] and value < 0:
        raise ValueError(f"{key} cannot be negative")
    
    if key == 'theme' and value not in ['light', 'dark']:
        raise ValueError("Theme must be 'light' or 'dark'")
    
    if key in ['start_date', 'end_date'] and not isinstance(value, (str, type(None))):
        raise ValueError(f"{key} must be a string or None")

def get_setting(key: str, default: Any = None) -> Any:
    """
    Get a setting value from session state or database.
    
    Args:
        key: Setting key
        default: Default value if not found
        
    Returns:
        Setting value
    """
    # First check session state
    if key in st.session_state:
        return st.session_state[key]
    
    # Then check database
    value = load_from_db(key, default)
    
    # Store in session state for faster access
    st.session_state[key] = value
    
    return value

def save_setting(key: str, value: Any) -> None:
    """
    Save a setting to both session state and database.
    
    Args:
        key: Setting key
        value: Setting value
        
    Raises:
        ValueError: If validation fails
    """
    # Validate the setting
    validate_setting(key, value)
    
    # Save to session state
    st.session_state[key] = value
    
    # Save to database
    save_to_db(key, value)

def get_all_settings() -> dict:
    """Get all settings from the database."""
    try:
        if not os.path.exists(DB_PATH):
            return {}
            
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT key, value FROM settings")
        results = cursor.fetchall()
        
        conn.close()
        
        settings = {}
        for key, value in results:
            # Try to convert back to appropriate type
            if value.lower() in ('true', 'false'):
                settings[key] = value.lower() == 'true'
            else:
                try:
                    if '.' not in value:
                        settings[key] = int(value)
                    else:
                        settings[key] = float(value)
                except ValueError:
                    settings[key] = value
        
        return settings
        
    except Exception as e:
        st.error(f"Error loading all settings: {e}")
        return {}

def reset_setting(key: str) -> None:
    """Reset a setting by removing it from session state and database."""
    try:
        # Remove from session state
        if key in st.session_state:
            del st.session_state[key]
        
        # Remove from database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM settings WHERE key = ?", (key,))
        conn.commit()
        conn.close()
        
        # Clear cache
        load_from_db.clear()
        
    except Exception as e:
        st.error(f"Error resetting setting {key}: {e}")
