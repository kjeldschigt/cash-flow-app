import streamlit as st
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from utils.error_handler import show_error, show_warning, validate_dataframe, ensure_dataframe_columns, Any

# Database path
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'cashflow.db')

@st.cache_data
def load_table(table_name: str) -> pd.DataFrame:
    """Load table from SQLite database with caching"""
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Error loading table {table_name}: {e}")
        return pd.DataFrame()

@st.cache_data
def load_combined_data():
    """Load and combine data from all sources with fallback handling"""
    try:
        from services.airtable import get_combined_data
        df = get_combined_data()
        
        # Ensure required columns exist
        required_cols = ['Date', 'Sales_USD', 'Costs_USD']
        df = ensure_dataframe_columns(df, required_cols, {
            'Sales_USD': 0.0,
            'Costs_USD': 0.0,
            'Date': datetime.now()
        })
        
        return df
    except ImportError as e:
        show_error("Missing required modules for data loading", e)
        return pd.DataFrame(columns=['Date', 'Sales_USD', 'Costs_USD'])
    except ConnectionError as e:
        show_error("Database connection failed", e)
        return pd.DataFrame(columns=['Date', 'Sales_USD', 'Costs_USD'])
    except Exception as e:
        show_error("Error loading combined data", e)
        return pd.DataFrame(columns=['Date', 'Sales_USD', 'Costs_USD'])

@st.cache_data
def load_costs_data() -> pd.DataFrame:
    """Load costs data with caching"""
    return load_table('costs')

@st.cache_data
def load_sales_data() -> pd.DataFrame:
    """Load sales data with caching"""
    return load_table('sales')

@st.cache_data
def load_settings() -> Dict[str, Any]:
    """Load settings from database with caching"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM settings")
        settings = dict(cursor.fetchall())
        conn.close()
        return settings
    except Exception:
        return {}

def get_filtered_data(df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
    """Apply filters to dataframe using session state to avoid reruns"""
    if df.empty:
        return df
    
    filtered_df = df.copy()
    
    # Date range filtering
    if 'start_date' in filters and 'end_date' in filters and 'Date' in df.columns:
        try:
            filtered_df['Date'] = pd.to_datetime(filtered_df['Date'])
            filtered_df = filtered_df[
                (filtered_df['Date'] >= pd.to_datetime(filters['start_date'])) &
                (filtered_df['Date'] <= pd.to_datetime(filters['end_date']))
            ]
        except Exception:
            pass
    
    # Category filtering
    if 'category' in filters and filters['category'] and 'Category' in df.columns:
        filtered_df = filtered_df[filtered_df['Category'] == filters['category']]
    
    # Status filtering
    if 'status' in filters and filters['status'] and 'Status' in df.columns:
        filtered_df = filtered_df[filtered_df['Status'] == filters['status']]
    
    return filtered_df

def init_session_filters():
    """Initialize session state filters if not present"""
    if 'data_filters' not in st.session_state:
        st.session_state.data_filters = {
            'start_date': pd.Timestamp.now() - pd.Timedelta(days=30),
            'end_date': pd.Timestamp.now(),
            'category': None,
            'status': None
        }

def update_session_filter(key: str, value: Any):
    """Update a specific filter in session state"""
    if 'data_filters' not in st.session_state:
        init_session_filters()
    st.session_state.data_filters[key] = value

def get_session_filter(key: str, default: Any = None) -> Any:
    """Get a filter value from session state"""
    if 'data_filters' not in st.session_state:
        init_session_filters()
    return st.session_state.data_filters.get(key, default)

def clear_cache():
    """Clear all cached data"""
    st.cache_data.clear()

def refresh_data():
    """Refresh all cached data"""
    clear_cache()
    # Reload main data tables
    load_combined_data()
    load_costs_data()
    load_sales_data()
    load_settings()
