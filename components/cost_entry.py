import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any

def insert_monthly_cost(month: str, category: str, amount: float) -> None:
    """Insert or update a monthly cost entry in the database."""
    with sqlite3.connect('cashflow.db') as conn:
        cursor = conn.cursor()
        
        # Create costs_monthly table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS costs_monthly (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                month TEXT NOT NULL,
                category TEXT NOT NULL,
                amount REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Insert or replace the cost entry
        cursor.execute('''
            INSERT OR REPLACE INTO costs_monthly (month, category, amount)
            VALUES (?, ?, ?)
        ''', (month, category, amount))
        
        conn.commit()

def cost_entry_form(month: Optional[str] = None, category: Optional[str] = None, form_key: str = "default") -> bool:
    """
    Reusable cost entry form component.
    
    Args:
        month: Pre-selected month (YYYY-MM format)
        category: Pre-selected category
        form_key: Unique key for form elements
        
    Returns:
        bool: True if entry was successfully saved
    """
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if month:
            # Parse month string to date
            try:
                month_date = datetime.strptime(month, '%Y-%m').replace(day=1)
            except:
                month_date = pd.Timestamp.now().replace(day=1)
        else:
            month_date = pd.Timestamp.now().replace(day=1)
            
        entry_date = st.date_input(
            "Entry Date", 
            value=month_date, 
            key=f"{form_key}_cost_entry_date"
        )
    
    with col2:
        cost_categories = [
            "Costa Rica USD", 
            "Costa Rica CRC", 
            "Hong Kong USD", 
            "Stripe Fee %", 
            "Huub Principal", 
            "Huub Interest", 
            "Google Ads"
        ]
        
        default_index = 0
        if category and category in cost_categories:
            default_index = cost_categories.index(category)
            
        cost_category = st.selectbox(
            "Cost Category", 
            cost_categories,
            index=default_index,
            key=f"{form_key}_cost_entry_category"
        )
    
    with col3:
        cost_amount = st.number_input(
            "Amount", 
            min_value=0.0, 
            step=100.0, 
            key=f"{form_key}_cost_entry_amount"
        )
    
    if st.button("Add Cost Entry", key=f"{form_key}_add_cost_entry_btn"):
        try:
            month_str = entry_date.strftime('%Y-%m')
            insert_monthly_cost(month_str, cost_category, cost_amount)
            st.success(f"Added {cost_category}: ${cost_amount:,.2f} for {month_str}")
            st.session_state.cost_entry_updated = True
            return True
        except Exception as e:
            st.error(f"Error adding cost entry: {str(e)}")
            return False
    
    return False

def monthly_cost_form(month: Optional[str] = None, form_key: str = "monthly") -> bool:
    """
    Monthly cost entry form for all categories at once.
    
    Args:
        month: Pre-selected month (YYYY-MM format)
        form_key: Unique key for form elements
        
    Returns:
        bool: True if entries were successfully saved
    """
    col1, col2 = st.columns([1, 2])
    
    with col1:
        if month:
            try:
                month_date = datetime.strptime(month, '%Y-%m').replace(day=1)
            except:
                month_date = pd.Timestamp.now().replace(day=1)
        else:
            month_date = pd.Timestamp.now().replace(day=1)
            
        selected_month = st.date_input(
            "Month", 
            value=month_date,
            key=f"{form_key}_month_selector"
        )
    
    with col2:
        st.write(f"**Enter costs for {selected_month.strftime('%Y-%m')}:**")
    
    # Cost category inputs for the selected month
    col1, col2 = st.columns(2)
    
    with col1:
        costa_usd_monthly = st.number_input(
            f"Costa Rica USD for {selected_month.strftime('%Y-%m')}", 
            value=19000.0, 
            key=f"{form_key}_costa_usd_monthly"
        )
        costa_crc_monthly = st.number_input(
            f"Costa Rica CRC for {selected_month.strftime('%Y-%m')}", 
            value=38000000.0, 
            key=f"{form_key}_costa_crc_monthly"
        )
        hk_usd_monthly = st.number_input(
            f"Hong Kong USD for {selected_month.strftime('%Y-%m')}", 
            value=40000.0, 
            key=f"{form_key}_hk_usd_monthly"
        )
    
    with col2:
        stripe_fee_monthly = st.number_input(
            f"Stripe % for {selected_month.strftime('%Y-%m')}", 
            value=4.2, 
            key=f"{form_key}_stripe_fee_monthly"
        )
        huub_principal_monthly = st.number_input(
            f"Huub Principal for {selected_month.strftime('%Y-%m')}", 
            value=1250000.0, 
            key=f"{form_key}_huub_principal_monthly"
        )
        huub_interest_monthly = st.number_input(
            f"Huub Interest for {selected_month.strftime('%Y-%m')}", 
            value=18750.0, 
            key=f"{form_key}_huub_interest_monthly"
        )
    
    google_ads_monthly = st.number_input(
        f"Google Ads for {selected_month.strftime('%Y-%m')}", 
        value=27500.0, 
        key=f"{form_key}_google_ads_monthly"
    )
    
    # Save monthly costs to database
    if st.button("Save Month Costs", key=f"{form_key}_save_month_costs"):
        try:
            month_str = selected_month.strftime('%Y-%m')
            cost_entries = [
                (month_str, 'Costa Rica USD', costa_usd_monthly),
                (month_str, 'Costa Rica CRC', costa_crc_monthly),
                (month_str, 'Hong Kong USD', hk_usd_monthly),
                (month_str, 'Stripe Fee %', stripe_fee_monthly),
                (month_str, 'Huub Principal', huub_principal_monthly),
                (month_str, 'Huub Interest', huub_interest_monthly),
                (month_str, 'Google Ads', google_ads_monthly)
            ]
            
            for month_val, category, amount in cost_entries:
                insert_monthly_cost(month_val, category, amount)
            
            st.success(f"Monthly costs saved for {month_str}!")
            st.session_state.monthly_costs_updated = True
            return True
            
        except Exception as e:
            st.error(f"Error saving monthly costs: {str(e)}")
            return False
    
    return False

def bulk_cost_entry_form(form_key: str = "bulk") -> bool:
    """
    Bulk cost entry form for CSV uploads.
    
    Args:
        form_key: Unique key for form elements
        
    Returns:
        bool: True if bulk upload was successful
    """
    st.write("**Upload CSV with columns: Date, Category, Amount**")
    uploaded_file = st.file_uploader(
        "Choose CSV file", 
        type="csv", 
        key=f"{form_key}_bulk_cost_upload"
    )
    
    if uploaded_file is not None:
        try:
            bulk_df = pd.read_csv(uploaded_file)
            st.dataframe(bulk_df.head(), use_container_width=True)
            
            if st.button("Process Bulk Upload", key=f"{form_key}_process_bulk_costs"):
                # Process each row
                success_count = 0
                for _, row in bulk_df.iterrows():
                    try:
                        date_str = pd.to_datetime(row['Date']).strftime('%Y-%m')
                        insert_monthly_cost(date_str, row['Category'], float(row['Amount']))
                        success_count += 1
                    except Exception as e:
                        st.error(f"Error processing row: {e}")
                
                st.success(f"Successfully processed {success_count} cost entries")
                st.session_state.bulk_costs_updated = True
                return True
        except Exception as e:
            st.error(f"Error processing file: {e}")
            return False
    
    return False

def display_recent_costs(limit: int = 10) -> None:
    """Display recent cost entries from the database."""
    try:
        with sqlite3.connect('cashflow.db') as conn:
            recent_costs_df = pd.read_sql_query('''
                SELECT month, category, amount, created_at
                FROM costs_monthly 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', conn, params=[limit])
        
        if not recent_costs_df.empty:
            st.dataframe(recent_costs_df, use_container_width=True)
        else:
            st.info("No recent cost entries found")
    except Exception as e:
        st.error(f"Error loading recent entries: {e}")

def display_monthly_costs_table() -> None:
    """Display monthly costs from database in pivot table format."""
    try:
        with sqlite3.connect('cashflow.db') as conn:
            monthly_costs_df = pd.read_sql_query('''
                SELECT month, category, amount, created_at
                FROM costs_monthly 
                ORDER BY month DESC, category
            ''', conn)
        
        if not monthly_costs_df.empty:
            # Create pivot table for better display
            pivot_df = monthly_costs_df.pivot(index='month', columns='category', values='amount')
            pivot_df = pivot_df.fillna(0)
            
            # Add total column
            if len(pivot_df.columns) > 0:
                # Calculate total excluding percentage-based fees
                numeric_columns = [col for col in pivot_df.columns if 'Fee %' not in col]
                if numeric_columns:
                    pivot_df['Total (USD)'] = pivot_df[numeric_columns].sum(axis=1)
            
            st.dataframe(pivot_df, use_container_width=True)
            
            # Show detailed records
            with st.expander("View Detailed Records"):
                st.dataframe(monthly_costs_df, use_container_width=True)
        else:
            st.info("No monthly cost records found. Use the form above to add monthly costs.")
            
    except Exception as e:
        st.error(f"Error loading monthly costs: {e}")
