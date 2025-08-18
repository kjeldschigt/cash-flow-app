import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime, timedelta, date
from typing import Dict, Any
try:
    from .error_handler import show_error, show_warning, validate_dataframe, ensure_dataframe_columns
except ImportError:
    # Fallback for when imported directly
    from error_handler import show_error, show_warning, validate_dataframe, ensure_dataframe_columns

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
        # Load data from sample files or database
        try:
            # Try to load from sample data files first
            import os
            data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
            
            sales_file = os.path.join(data_dir, 'sample_sales_orders.csv')
            costs_file = os.path.join(data_dir, 'sample_cash_out.csv')
            
            df_sales = pd.DataFrame()
            df_costs = pd.DataFrame()
            
            if os.path.exists(sales_file):
                df_sales = pd.read_csv(sales_file)
                if 'Date' not in df_sales.columns and 'date' in df_sales.columns:
                    df_sales = df_sales.rename(columns={'date': 'Date'})
                if 'Amount' in df_sales.columns:
                    df_sales = df_sales.rename(columns={'Amount': 'Sales_USD'})
                df_sales['Costs_USD'] = 0
            
            if os.path.exists(costs_file):
                df_costs = pd.read_csv(costs_file)
                if 'Date' not in df_costs.columns and 'date' in df_costs.columns:
                    df_costs = df_costs.rename(columns={'date': 'Date'})
                if 'Amount' in df_costs.columns:
                    df_costs = df_costs.rename(columns={'Amount': 'Costs_USD'})
                df_costs['Sales_USD'] = 0
            
            # Combine dataframes
            df = pd.concat([df_sales, df_costs], ignore_index=True)
            
        except Exception:
            # Fallback to empty dataframe
            df = pd.DataFrame()
        
        # Ensure required columns exist
        required_cols = ['Date', 'Sales_USD', 'Costs_USD']
        df = ensure_dataframe_columns(df, required_cols, {
            'Sales_USD': 0.0,
            'Costs_USD': 0.0,
            'Date': datetime.now()
        })
        
        # Clean and standardize Date column
        if not df.empty and 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df = df.dropna(subset=['Date'])
            df = df.sort_values('Date')
        
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

def filter_data_by_range(df: pd.DataFrame, range_label: str) -> pd.DataFrame:
    """Filter dataframe by date range based on label"""
    if df.empty or 'Date' not in df.columns:
        return df
    
    # Ensure Date column is datetime
    df = df.copy()
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date'])
    
    # Calculate date range
    end_date = datetime.now()
    
    if range_label == "Last 30 Days":
        start_date = end_date - timedelta(days=30)
    elif range_label == "Last 60 Days":
        start_date = end_date - timedelta(days=60)
    elif range_label == "Last 90 Days":
        start_date = end_date - timedelta(days=90)
    elif range_label == "Year to Date":
        start_date = datetime(end_date.year, 1, 1)
    elif range_label == "All Time":
        return df
    else:
        # Default to last 30 days
        start_date = end_date - timedelta(days=30)
    
    # Filter dataframe
    filtered_df = df[
        (df['Date'] >= start_date) & 
        (df['Date'] <= end_date)
    ]
    
    return filtered_df

def get_daily_aggregates(df: pd.DataFrame) -> pd.DataFrame:
    """Get daily aggregated data with Net calculation"""
    if df.empty or 'Date' not in df.columns:
        return pd.DataFrame(columns=['Date', 'Sales_USD', 'Costs_USD', 'Net'])
    
    # Ensure Date column is datetime
    df = df.copy()
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date'])
    
    # Group by date and sum
    daily_agg = df.groupby(df['Date'].dt.date).agg({
        'Sales_USD': 'sum',
        'Costs_USD': 'sum'
    }).reset_index()
    
    # Convert date back to datetime
    daily_agg['Date'] = pd.to_datetime(daily_agg['Date'])
    
    # Calculate Net = Sales - Costs
    daily_agg['Net'] = daily_agg['Sales_USD'] - daily_agg['Costs_USD']
    
    return daily_agg.sort_values('Date')

def generate_due_costs():
    """Generate due costs from recurring costs and insert into costs table."""
    from src.services.storage_service import get_recurring_costs, get_db_connection
    from datetime import datetime, timedelta
    import uuid
    
    try:
        recurring_costs_df = get_recurring_costs()
        if recurring_costs_df.empty:
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        today = datetime.now().date()
        
        for _, row in recurring_costs_df.iterrows():
            if not row.get('active', True):
                continue
                
            next_due_str = row.get('next_due_date')
            if not next_due_str:
                continue
                
            try:
                next_due_date = datetime.strptime(next_due_str, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                continue
                
            if next_due_date <= today:
                # Insert cost entry
                cost_id = str(uuid.uuid4())
                cursor.execute('''
                    INSERT INTO costs (id, date, category, amount_expected, comment, paid, actual_amount)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (cost_id, next_due_str, row['category'], row['amount_expected'], 
                      row.get('comment', ''), False, None))
                
                # Calculate next due date based on recurrence
                recurrence = row.get('recurrence', '').lower()
                if recurrence == 'weekly':
                    new_due_date = next_due_date + timedelta(days=7)
                elif recurrence == 'bi-weekly' or recurrence == 'biweekly':
                    new_due_date = next_due_date + timedelta(days=14)
                elif recurrence == 'monthly':
                    # Add 1 month (approximate)
                    if next_due_date.month == 12:
                        new_due_date = next_due_date.replace(year=next_due_date.year + 1, month=1)
                    else:
                        new_due_date = next_due_date.replace(month=next_due_date.month + 1)
                elif recurrence == 'every 2 months':
                    # Add 2 months
                    month = next_due_date.month + 2
                    year = next_due_date.year
                    if month > 12:
                        month -= 12
                        year += 1
                    new_due_date = next_due_date.replace(year=year, month=month)
                elif recurrence == 'quarterly':
                    # Add 3 months
                    month = next_due_date.month + 3
                    year = next_due_date.year
                    if month > 12:
                        month -= 12
                        year += 1
                    new_due_date = next_due_date.replace(year=year, month=month)
                elif recurrence == 'semiannual':
                    # Add 6 months
                    month = next_due_date.month + 6
                    year = next_due_date.year
                    if month > 12:
                        month -= 12
                        year += 1
                    new_due_date = next_due_date.replace(year=year, month=month)
                elif recurrence == 'annual' or recurrence == 'yearly':
                    new_due_date = next_due_date.replace(year=next_due_date.year + 1)
                else:
                    continue  # Unknown recurrence, skip
                
                # Update next_due_date in recurring_costs
                cursor.execute('''
                    UPDATE recurring_costs 
                    SET next_due_date = ?
                    WHERE id = ?
                ''', (new_due_date.strftime('%Y-%m-%d'), row['id']))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        st.error(f"Error generating due costs: {str(e)}")
        if 'conn' in locals():
            conn.close()

def calculate_metrics(costs_df: pd.DataFrame, sales_df: pd.DataFrame) -> Dict[str, Any]:
    """Calculate financial metrics from costs and sales data"""
    metrics = {
        "total_costs": 0,
        "total_sales": 0,
        "net_profit": 0,
        "profit_margin": 0,
        "avg_daily_costs": 0,
        "avg_daily_sales": 0
    }
    
    try:
        if not costs_df.empty and 'amount' in costs_df.columns:
            metrics["total_costs"] = float(costs_df['amount'].sum())
            if len(costs_df) > 0:
                metrics["avg_daily_costs"] = metrics["total_costs"] / len(costs_df)
        
        if not sales_df.empty and 'amount' in sales_df.columns:
            metrics["total_sales"] = float(sales_df['amount'].sum())
            if len(sales_df) > 0:
                metrics["avg_daily_sales"] = metrics["total_sales"] / len(sales_df)
        
        metrics["net_profit"] = metrics["total_sales"] - metrics["total_costs"]
        
        if metrics["total_sales"] > 0:
            metrics["profit_margin"] = (metrics["net_profit"] / metrics["total_sales"]) * 100
        
    except Exception as e:
        st.error(f"Error calculating metrics: {e}")
    
    return metrics

def get_date_range_data(start_date: date, end_date: date) -> Dict[str, pd.DataFrame]:
    """Fetch data within a specified date range and return DataFrames"""
    try:
        conn = sqlite3.connect('cashflow.db')
        
        # Convert dates to strings for SQL query
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        # Fetch costs data within date range
        costs_query = """
        SELECT * FROM costs 
        WHERE date BETWEEN ? AND ?
        ORDER BY date DESC
        """
        costs_df = pd.read_sql_query(costs_query, conn, params=(start_str, end_str))
        
        # Fetch sales orders data within date range
        sales_query = """
        SELECT * FROM sales_orders 
        WHERE date BETWEEN ? AND ?
        ORDER BY date DESC
        """
        sales_df = pd.read_sql_query(sales_query, conn, params=(start_str, end_str))
        
        # Fetch cash out data within date range
        cash_out_query = """
        SELECT * FROM cash_out 
        WHERE date BETWEEN ? AND ?
        ORDER BY date DESC
        """
        cash_out_df = pd.read_sql_query(cash_out_query, conn, params=(start_str, end_str))
        
        # Fetch FX rates data within date range
        fx_query = """
        SELECT * FROM fx_rates 
        WHERE date BETWEEN ? AND ?
        ORDER BY date DESC
        """
        fx_df = pd.read_sql_query(fx_query, conn, params=(start_str, end_str))
        
        # Fetch loan payments data within date range
        loan_query = """
        SELECT * FROM loan_payments 
        WHERE date BETWEEN ? AND ?
        ORDER BY date DESC
        """
        loan_df = pd.read_sql_query(loan_query, conn, params=(start_str, end_str))
        
        conn.close()
        
        return {
            'costs': costs_df,
            'sales': sales_df,
            'cash_out': cash_out_df,
            'fx_rates': fx_df,
            'loan_payments': loan_df
        }
        
    except Exception as e:
        st.error(f"Error fetching date range data: {str(e)}")
        if 'conn' in locals():
            conn.close()
        return {
            'costs': pd.DataFrame(),
            'sales': pd.DataFrame(),
            'cash_out': pd.DataFrame(),
            'fx_rates': pd.DataFrame(),
            'loan_payments': pd.DataFrame()
        }

def refresh_data():
    """Refresh all cached data"""
    clear_cache()
    # Reload main data tables
    load_combined_data()
    load_costs_data()
    load_sales_data()
    load_settings()
