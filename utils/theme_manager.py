import streamlit as st

def get_setting(key, default=None):
    """Get setting from session_state, fallback to DB, then default"""
    if key in st.session_state:
        return st.session_state[key]
    
    try:
        from services.storage import load_settings
        db_settings = load_settings()
        if key in db_settings:
            value = db_settings[key]
            # Convert string values to appropriate types
            if isinstance(default, float):
                return float(value)
            elif isinstance(default, int):
                return int(value)
            return value
    except:
        pass
    
    return default

def apply_theme(theme="light"):
    """Apply theme CSS styles based on theme selection"""
    if theme == "light":
        return '''
        <style>
        .stApp {
            background-color: #FAFAFA;
            color: #333;
        }
        .stSidebar {
            background-color: #F0F2F6;
        }
        .stMetric {
            color: #000 !important;
        }
        .stAlert {
            background-color: #EEE;
        }
        .stSelectbox label, .stNumberInput label, .stTextInput label {
            color: #000 !important;
        }
        .stDataFrame {
            background-color: #FFF;
        }
        </style>
        '''
    else:  # dark theme
        return '''
        <style>
        .stApp {
            background-color: #0E1117;
            color: #FAFAFA;
        }
        .stSidebar {
            background-color: #262730;
        }
        .stMetric {
            color: #FAFAFA !important;
        }
        .stAlert {
            background-color: #1E1E1E;
        }
        .stSelectbox label, .stNumberInput label, .stTextInput label {
            color: #FAFAFA !important;
        }
        .stDataFrame {
            background-color: #1E1E1E;
        }
        </style>
        '''
