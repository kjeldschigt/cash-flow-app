import streamlit as st

def apply_theme(theme: str = "light"):
    """Apply the light theme to the Streamlit app."""
    # Always apply light theme regardless of parameter
    st.markdown('''
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
    ''', unsafe_allow_html=True)
    
    # Update session state
    st.session_state['theme'] = theme

def get_current_theme():
    """Return the current theme from session state or default to light."""
    return st.session_state.get('theme', 'light')

def set_theme(theme: str):
    """Set and persist the theme, triggering a re-render."""
    apply_theme(theme)
    from services.settings_manager import update_setting
    update_setting('theme', theme)  # Persist to DB
    st.rerun()  # Refresh the app

def apply_current_theme():
    """Apply the current theme from settings"""
    from services.settings_manager import get_setting
    theme = get_setting('theme', 'light')
    apply_theme(theme)
