"""Data manager utilities for the application."""

import logging
import os
import sqlite3
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, date, timedelta
import pandas as pd
import streamlit as st

logger = logging.getLogger(__name__)

# Database path
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'cash_flow.db')

def calculate_metrics(data: Union[List[Dict[str, Any]], pd.DataFrame]) -> Dict[str, Any]:
    """Calculate financial metrics from data.
    
    Args:
        data: Either a list of dictionaries or a pandas DataFrame
        
    Returns:
        Dictionary with calculated metrics
    """
    try:
        if data is None or (isinstance(data, list) and len(data) == 0) or (isinstance(data, pd.DataFrame) and data.empty):
            return {
                'total_sales': 0.0,
                'total_costs': 0.0,
                'net_cash_flow': 0.0,
                'count': 0,
                'avg_transaction': 0.0,
                'max_transaction': 0.0,
                'min_transaction': 0.0
            }
        
        # Convert to DataFrame if it's a list
        if isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = data.copy()
        
        if df.empty:
            return {
                'total_sales': 0.0,
                'total_costs': 0.0,
                'net_cash_flow': 0.0,
                'count': 0,
                'avg_transaction': 0.0,
                'max_transaction': 0.0,
                'min_transaction': 0.0
            }
        
        # Standardize column names
        column_mapping = {
            'sales': 'Sales_USD',
            'costs': 'Costs_USD',
            'amount': 'Sales_USD',
            'cost': 'Costs_USD',
            'revenue': 'Sales_USD',
            'expense': 'Costs_USD'
        }
        
        for old_col, new_col in column_mapping.items():
            if old_col in df.columns and new_col not in df.columns:
                df[new_col] = df[old_col]
        
        # Calculate metrics
        total_sales = df.get('Sales_USD', pd.Series([0])).fillna(0).sum()
        total_costs = df.get('Costs_USD', pd.Series([0])).fillna(0).sum()
        net_cash_flow = total_sales - total_costs
        
        # Additional metrics
        transactions = df.get('Sales_USD', pd.Series([0])).fillna(0)
        non_zero_transactions = transactions[transactions > 0]
        
        avg_transaction = non_zero_transactions.mean() if len(non_zero_transactions) > 0 else 0.0
        max_transaction = transactions.max() if len(transactions) > 0 else 0.0
        min_transaction = transactions.min() if len(transactions) > 0 else 0.0
        
        return {
            'total_sales': float(total_sales),
            'total_costs': float(total_costs),
            'net_cash_flow': float(net_cash_flow),
            'count': len(df),
            'avg_transaction': float(avg_transaction) if not pd.isna(avg_transaction) else 0.0,
            'max_transaction': float(max_transaction) if not pd.isna(max_transaction) else 0.0,
            'min_transaction': float(min_transaction) if not pd.isna(min_transaction) else 0.0
        }
        
    except Exception as e:
        logger.error(f"Error calculating metrics: {str(e)}")
        return {
            'total_sales': 0.0,
            'total_costs': 0.0,
            'net_cash_flow': 0.0,
            'count': 0,
            'avg_transaction': 0.0,
            'max_transaction': 0.0,
            'min_transaction': 0.0
        }

def get_date_range_data(data: Union[List[Dict[str, Any]], pd.DataFrame], start_date: date, end_date: date, date_field: str = 'date') -> Union[List[Dict[str, Any]], pd.DataFrame]:
    """Filter data by date range.
    
    Args:
        data: Data to filter (list of dicts or DataFrame)
        start_date: Start date for filtering
        end_date: End date for filtering
        date_field: Name of the date field to filter on
        
    Returns:
        Filtered data in the same format as input
    """
    try:
        if data is None or (isinstance(data, list) and len(data) == 0) or (isinstance(data, pd.DataFrame) and data.empty):
            return data if isinstance(data, pd.DataFrame) else []
        
        if isinstance(data, list):
            filtered_data = []
            for item in data:
                item_date = item.get(date_field)
                if item_date:
                    if isinstance(item_date, str):
                        try:
                            item_date = datetime.fromisoformat(item_date.replace('Z', '+00:00')).date()
                        except ValueError:
                            try:
                                item_date = datetime.strptime(item_date, '%Y-%m-%d').date()
                            except ValueError:
                                continue
                    elif isinstance(item_date, datetime):
                        item_date = item_date.date()
                    
                    if start_date <= item_date <= end_date:
                        filtered_data.append(item)
            return filtered_data
        
        elif isinstance(data, pd.DataFrame):
            df = data.copy()
            if date_field not in df.columns:
                # Try common date column names
                date_columns = ['Date', 'date', 'created_at', 'timestamp', 'order_date']
                for col in date_columns:
                    if col in df.columns:
                        date_field = col
                        break
                else:
                    return df  # No date column found, return original
            
            # Convert date column to datetime
            df[date_field] = pd.to_datetime(df[date_field], errors='coerce')
            df = df.dropna(subset=[date_field])
            
            # Filter by date range
            mask = (df[date_field].dt.date >= start_date) & (df[date_field].dt.date <= end_date)
            return df[mask]
        
        return data
        
    except Exception as e:
        logger.error(f"Error filtering data by date range: {str(e)}")
        return data if isinstance(data, pd.DataFrame) else []

def filter_data_by_range(df: pd.DataFrame, range_label: str) -> pd.DataFrame:
    """Filter DataFrame by date range based on label.
    
    Args:
        df: DataFrame to filter
        range_label: Range label like 'Last 30 Days', 'Last 3 Months', etc.
        
    Returns:
        Filtered DataFrame
    """
    try:
        if df.empty:
            return df
        
        # Find date column
        date_column = None
        date_columns = ['Date', 'date', 'created_at', 'timestamp', 'order_date']
        for col in date_columns:
            if col in df.columns:
                date_column = col
                break
        
        if not date_column:
            return df  # No date column found
        
        # Convert to datetime
        df_filtered = df.copy()
        df_filtered[date_column] = pd.to_datetime(df_filtered[date_column], errors='coerce')
        df_filtered = df_filtered.dropna(subset=[date_column])
        
        # Calculate date range
        today = datetime.now().date()
        
        if range_label == "Last 7 Days":
            start_date = today - timedelta(days=7)
        elif range_label == "Last 30 Days":
            start_date = today - timedelta(days=30)
        elif range_label == "Last 3 Months":
            start_date = today - timedelta(days=90)
        elif range_label == "Last 6 Months":
            start_date = today - timedelta(days=180)
        elif range_label == "Last 12 Months":
            start_date = today - timedelta(days=365)
        elif range_label == "YTD":
            start_date = datetime(today.year, 1, 1).date()
        else:
            return df_filtered  # Unknown range, return all data
        
        # Filter data
        mask = df_filtered[date_column].dt.date >= start_date
        return df_filtered[mask]
        
    except Exception as e:
        logger.error(f"Error filtering data by range {range_label}: {str(e)}")
        return df

def get_daily_aggregates(df: pd.DataFrame) -> pd.DataFrame:
    """Get daily aggregated data with Net calculation.
    
    Args:
        df: DataFrame to aggregate
        
    Returns:
        DataFrame with daily aggregates
    """
    try:
        if df.empty:
            return pd.DataFrame(columns=['Date', 'Sales_USD', 'Costs_USD', 'Net'])
        
        # Find date column
        date_column = None
        date_columns = ['Date', 'date', 'created_at', 'timestamp', 'order_date']
        for col in date_columns:
            if col in df.columns:
                date_column = col
                break
        
        if not date_column:
            return pd.DataFrame(columns=['Date', 'Sales_USD', 'Costs_USD', 'Net'])
        
        df_agg = df.copy()
        df_agg[date_column] = pd.to_datetime(df_agg[date_column], errors='coerce')
        df_agg = df_agg.dropna(subset=[date_column])
        
        # Extract date only
        df_agg['Date'] = df_agg[date_column].dt.date
        
        # Ensure numeric columns exist
        if 'Sales_USD' not in df_agg.columns:
            df_agg['Sales_USD'] = 0
        if 'Costs_USD' not in df_agg.columns:
            df_agg['Costs_USD'] = 0
        
        # Convert to numeric
        df_agg['Sales_USD'] = pd.to_numeric(df_agg['Sales_USD'], errors='coerce').fillna(0)
        df_agg['Costs_USD'] = pd.to_numeric(df_agg['Costs_USD'], errors='coerce').fillna(0)
        
        # Group by date and sum
        daily_agg = df_agg.groupby('Date').agg({
            'Sales_USD': 'sum',
            'Costs_USD': 'sum'
        }).reset_index()
        
        # Calculate net
        daily_agg['Net'] = daily_agg['Sales_USD'] - daily_agg['Costs_USD']
        
        return daily_agg
        
    except Exception as e:
        logger.error(f"Error getting daily aggregates: {str(e)}")
        return pd.DataFrame(columns=['Date', 'Sales_USD', 'Costs_USD', 'Net'])

@st.cache_data
def load_combined_data() -> Dict[str, Any]:
    """Load combined data from various sources.
    
    Returns:
        Dictionary containing combined data from all sources
    """
    try:
        # Initialize empty data structure
        combined_data = {
            'sales_orders': [],
            'costs': [],
            'fx_rates': [],
            'loan_payments': []
        }
        
        # Try to load from sample data files
        try:
            data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
            
            # Load sales orders
            sales_file = os.path.join(data_dir, 'sample_sales_orders.csv')
            if os.path.exists(sales_file):
                df_sales = pd.read_csv(sales_file)
                combined_data['sales_orders'] = df_sales.to_dict('records')
            
            # Load costs
            costs_file = os.path.join(data_dir, 'sample_cash_out.csv')
            if os.path.exists(costs_file):
                df_costs = pd.read_csv(costs_file)
                combined_data['costs'] = df_costs.to_dict('records')
            
            # Load FX rates
            fx_file = os.path.join(data_dir, 'sample_fx_rates.csv')
            if os.path.exists(fx_file):
                df_fx = pd.read_csv(fx_file)
                combined_data['fx_rates'] = df_fx.to_dict('records')
                
        except Exception as e:
            logger.warning(f"Could not load sample data files: {str(e)}")
        
        # Try to load from database
        try:
            if os.path.exists(DB_PATH):
                conn = sqlite3.connect(DB_PATH)
                
                # Load sales orders
                try:
                    df_sales = pd.read_sql("SELECT * FROM sales_orders", conn)
                    if not df_sales.empty:
                        combined_data['sales_orders'] = df_sales.to_dict('records')
                except:
                    pass
                
                # Load costs
                try:
                    df_costs = pd.read_sql("SELECT * FROM costs", conn)
                    if not df_costs.empty:
                        combined_data['costs'] = df_costs.to_dict('records')
                except:
                    pass
                
                # Load FX rates
                try:
                    df_fx = pd.read_sql("SELECT * FROM fx_rates", conn)
                    if not df_fx.empty:
                        combined_data['fx_rates'] = df_fx.to_dict('records')
                except:
                    pass
                
                conn.close()
                
        except Exception as e:
            logger.warning(f"Could not load from database: {str(e)}")
        
        return combined_data
        
    except Exception as e:
        logger.error(f"Error loading combined data: {str(e)}")
        return {
            'sales_orders': [],
            'costs': [],
            'fx_rates': [],
            'loan_payments': []
        }

def init_session_filters():
    """Initialize session state filters."""
    try:
        if 'date_range' not in st.session_state:
            st.session_state.date_range = 'Last 30 Days'
        
        if 'currency_filter' not in st.session_state:
            st.session_state.currency_filter = 'All'
        
        if 'category_filter' not in st.session_state:
            st.session_state.category_filter = 'All'
            
        if 'data_filters' not in st.session_state:
            st.session_state.data_filters = {
                'date_range': 'Last 30 Days',
                'currency': 'All',
                'category': 'All'
            }
            
    except Exception as e:
        logger.error(f"Error initializing session filters: {str(e)}")

def update_session_filter(key: str, value: Any):
    """Update a specific filter in session state."""
    try:
        if 'data_filters' not in st.session_state:
            init_session_filters()
        st.session_state.data_filters[key] = value
        st.session_state[key] = value  # Also update direct session state
    except Exception as e:
        logger.error(f"Error updating session filter {key}: {str(e)}")

def get_session_filter(key: str, default: Any = None) -> Any:
    """Get a filter value from session state."""
    try:
        if 'data_filters' not in st.session_state:
            init_session_filters()
        return st.session_state.data_filters.get(key, default)
    except Exception as e:
        logger.error(f"Error getting session filter {key}: {str(e)}")
        return default
