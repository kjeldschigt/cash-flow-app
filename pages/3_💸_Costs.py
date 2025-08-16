import streamlit as st
import warnings
import numpy as np

# Suppress sklearn warnings
warnings.filterwarnings("ignore", category=UserWarning, module="sklearn.utils.validation")

# Load settings from session_state with DB fallback
def get_setting(key, default_value):
    """Get setting from session_state, fallback to DB, then default"""
    if key in st.session_state:
        return st.session_state[key]
    
    try:
        db_settings = load_settings()
        if key in db_settings:
            value = db_settings[key]
            # Convert string values to appropriate types
            if isinstance(default_value, float):
                return float(value)
            elif isinstance(default_value, int):
                return int(value)
            return value
    except:
        pass
    
    return default_value

# Apply theme from session_state with DB fallback
theme = get_setting('theme', 'light')
if theme == "light":
    st.markdown('''
    <style>
    .stApp { background-color: #FAFAFA; color: #333; }
    .stSidebar { background-color: #F0F2F6; }
    </style>
    ''', unsafe_allow_html=True)
else:
    st.markdown('''
    <style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    .stSidebar { background-color: #262730; }
    </style>
    ''', unsafe_allow_html=True)
import sys
import os
import pandas as pd

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.storage import load_costs_data, get_combined_data, load_table, upsert_from_csv, load_settings
from services.fx import apply_fx_conversion, get_rate_scenarios, get_monthly_rate
from services.airtable import load_combined_data

def _mpa_v1():
    """Main page application function"""
    st.title("Cost Analysis & Breakdown")

    # Get cost values from Settings with DB fallback
    costa_usd_cr = get_setting('costa_usd', 19000.0)
    costa_crc = get_setting('costa_crc', 38000000.0)
    hk_usd = get_setting('hk_usd', 40000.0)
    stripe_fee_pct = get_setting('stripe_fee', 4.2)
    huub_principal = get_setting('huub_principal', 1250000.0)
    huub_interest = get_setting('huub_interest', 18750.0)
    google_ads = get_setting('google_ads', 27500.0)

    # Main Navigation Tabs
    tabs = st.tabs(["Overview", "Breakdown", "Trends", "Entry"])

    with tabs[3]:  # Entry Tab
        st.subheader("Manual Cost Entry")
        
        # Entry form per category
        col1, col2, col3 = st.columns(3)
    
    with col1:
        entry_date = st.date_input("Entry Date", value=pd.Timestamp.now().replace(day=1), key="cost_entry_date")
    
    with col2:
        cost_category = st.selectbox("Cost Category", [
            "Costa USD", 
            "Costa CRC", 
            "HK USD", 
            "Stripe %", 
            "Huub Principal", 
            "Huub Interest", 
            "Google Ads"
        ], key="cost_entry_category")
    
    with col3:
        cost_amount = st.number_input("Amount", min_value=0.0, step=100.0, key="cost_entry_amount")
    
    if st.button("Add Cost Entry", key="add_cost_entry_btn"):
        try:
            # Insert cost entry into database
            from services.storage import insert_monthly_cost
            insert_monthly_cost(entry_date.strftime('%Y-%m'), cost_category, cost_amount)
            st.success(f"Added {cost_category}: ${cost_amount:,.2f} for {entry_date.strftime('%Y-%m')}")
            st.rerun()  # Refresh to show updated data
        except Exception as e:
            st.error(f"Error adding cost entry: {str(e)}")
    
    # Bulk entry section
    with st.expander("Bulk Cost Entry"):
        st.write("**Upload CSV with columns: Date, Category, Amount**")
        uploaded_file = st.file_uploader("Choose CSV file", type="csv", key="bulk_cost_upload")
        
        if uploaded_file is not None:
            try:
                bulk_df = pd.read_csv(uploaded_file)
                st.dataframe(bulk_df.head(), use_container_width=True)
                
                if st.button("Process Bulk Upload", key="process_bulk_costs"):
                    # Process each row
                    success_count = 0
                    for _, row in bulk_df.iterrows():
                        try:
                            from services.storage import insert_monthly_cost
                            date_str = pd.to_datetime(row['Date']).strftime('%Y-%m')
                            insert_monthly_cost(date_str, row['Category'], float(row['Amount']))
                            success_count += 1
                        except Exception as e:
                            st.error(f"Error processing row: {e}")
                    
                    st.success(f"Successfully processed {success_count} cost entries")
                    st.rerun()
            except Exception as e:
                st.error(f"Error processing file: {e}")
    
    # Recent entries display
    with st.expander("Recent Cost Entries"):
        try:
            from services.storage import load_monthly_costs
            recent_costs = load_monthly_costs()
            if recent_costs:
                costs_df = pd.DataFrame(recent_costs)
                # Show last 10 entries
                st.dataframe(costs_df.tail(10), use_container_width=True)
            else:
                st.info("No recent cost entries found")
        except Exception as e:
            st.error(f"Error loading recent entries: {e}")

# Monthly Cost Entry
st.subheader("Monthly Cost Entry")

col1, col2 = st.columns([1, 2])

with col1:
    month = st.date_input("Month", value=pd.Timestamp.now().replace(day=1))

with col2:
    st.write(f"**Enter costs for {month.strftime('%Y-%m')}:**")

# Cost category inputs for the selected month
col1, col2 = st.columns(2)

with col1:
    costa_usd_monthly = st.number_input(f"Costa Rica USD for {month.strftime('%Y-%m')}", value=costa_usd_cr, key="costa_usd_monthly")
    costa_crc_monthly = st.number_input(f"Costa Rica CRC for {month.strftime('%Y-%m')}", value=costa_crc, key="costa_crc_monthly")
    hk_usd_monthly = st.number_input(f"Hong Kong USD for {month.strftime('%Y-%m')}", value=hk_usd, key="hk_usd_monthly")

with col2:
    stripe_fee_monthly = st.number_input(f"Stripe % for {month.strftime('%Y-%m')}", value=stripe_fee_pct, key="stripe_fee_monthly")
    huub_principal_monthly = st.number_input(f"Huub Principal for {month.strftime('%Y-%m')}", value=huub_principal, key="huub_principal_monthly")
    huub_interest_monthly = st.number_input(f"Huub Interest for {month.strftime('%Y-%m')}", value=huub_interest, key="huub_interest_monthly")

google_ads_monthly = st.number_input(f"Google Ads for {month.strftime('%Y-%m')}", value=google_ads, key="google_ads_monthly")

# Save monthly costs to database
if st.button("Save Month Costs"):
    import sqlite3
    
    # Connect to database
    conn = sqlite3.connect('cashflow.db')
    cursor = conn.cursor()
    
    # Create costs_monthly table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS costs_monthly (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            month TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(month, category)
        )
    ''')
    
    # Insert/update monthly costs
    month_str = month.strftime('%Y-%m')
    cost_entries = [
        (month_str, 'Costa Rica USD', costa_usd_monthly),
        (month_str, 'Costa Rica CRC', costa_crc_monthly),
        (month_str, 'Hong Kong USD', hk_usd_monthly),
        (month_str, 'Stripe Fee %', stripe_fee_monthly),
        (month_str, 'Huub Principal', huub_principal_monthly),
        (month_str, 'Huub Interest', huub_interest_monthly),
        (month_str, 'Google Ads', google_ads_monthly)
    ]
    
    try:
        for month_val, category, amount in cost_entries:
            cursor.execute('''
                INSERT OR REPLACE INTO costs_monthly (month, category, amount)
                VALUES (?, ?, ?)
            ''', (month_val, category, amount))
        
        conn.commit()
        st.success(f"Monthly costs saved for {month_str}!")
        st.rerun()  # Refresh to show updated data
        
    except Exception as e:
        st.error(f"Error saving monthly costs: {str(e)}")
    finally:
        conn.close()

# Display monthly costs from database
st.subheader("Monthly Cost Breakdown from Database")

try:
    import sqlite3
    conn = sqlite3.connect('cashflow.db')
    
    # Load monthly costs from database
    monthly_costs_df = pd.read_sql_query('''
        SELECT month, category, amount, created_at
        FROM costs_monthly
        ORDER BY month DESC, category
    ''', conn)
    
    conn.close()
    
    if not monthly_costs_df.empty:
        # Create pivot table for better display
        pivot_df = monthly_costs_df.pivot(index='month', columns='category', values='amount')
        pivot_df = pivot_df.fillna(0)
        
        # Add total column
        if len(pivot_df.columns) > 0:
            # Calculate total excluding percentage-based fees
            numeric_columns = [col for col in pivot_df.columns if 'Fee %' not in col]
            pivot_df['Total (USD)'] = pivot_df[numeric_columns].sum(axis=1)
        
        st.dataframe(pivot_df, use_container_width=True)
        
        # Show detailed records
        with st.expander("View Detailed Records"):
            st.dataframe(monthly_costs_df, use_container_width=True)
    else:
        st.info("No monthly cost records found. Use the form above to add monthly costs.")
        
except Exception as e:
    st.error(f"Error loading monthly costs: {str(e)}")

# Store costs in session state for other pages
st.session_state.costs = {
    'costa_usd_cr': costa_usd_cr,
    'costa_crc': costa_crc,
    'hk_usd': hk_usd,
    'stripe_fee_pct': stripe_fee_pct,
    'huub_principal': huub_principal,
    'huub_interest': huub_interest,
    'google_ads': google_ads
}

# Convert CRC to USD using current FX rate
current_fx_rate = get_monthly_rate('2024-08', 'base')  # Get base rate
costa_crc_usd = costa_crc / current_fx_rate if current_fx_rate > 0 else 0

with tabs[1]:  # Breakdown Tab
    st.subheader("Cost Breakdown by Category")
    
    # Create cost breakdown data
    cost_data = {
        'Category': ['Costa Rica (USD)', 'Costa Rica (CRC→USD)', 'Hong Kong (USD)', 'Huub Interest', 'Google Ads', 'Stripe Fee (Variable)'],
        'Monthly Cost': [costa_usd_cr, costa_crc_usd, hk_usd, huub_interest, google_ads, 0],  # Stripe varies by sales
        'Annual Cost': [costa_usd_cr * 12, costa_crc_usd * 12, hk_usd * 12, huub_interest * 12, google_ads * 12, 0],
        'Percentage': [
            (costa_usd_cr / (costa_usd_cr + costa_crc_usd + hk_usd + huub_interest + google_ads) * 100),
            (costa_crc_usd / (costa_usd_cr + costa_crc_usd + hk_usd + huub_interest + google_ads) * 100),
            (hk_usd / (costa_usd_cr + costa_crc_usd + hk_usd + huub_interest + google_ads) * 100),
            (huub_interest / (costa_usd_cr + costa_crc_usd + hk_usd + huub_interest + google_ads) * 100),
            (google_ads / (costa_usd_cr + costa_crc_usd + hk_usd + huub_interest + google_ads) * 100),
            0  # Variable
        ]
    }
    
    cost_df = pd.DataFrame(cost_data)
    cost_df['Monthly Cost'] = cost_df['Monthly Cost'].apply(lambda x: f"${x:,.0f}")
    cost_df['Annual Cost'] = cost_df['Annual Cost'].apply(lambda x: f"${x:,.0f}")
    cost_df['Percentage'] = cost_df['Percentage'].apply(lambda x: f"{x:.1f}%")
    
    st.dataframe(cost_df, use_container_width=True)
    
    # Per-category details with expanders
    with st.expander("Costa Rica Details"):
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**USD Component:** ${costa_usd_cr:,.0f}")
            st.write(f"**CRC Component:** ₡{costa_crc:,.0f}")
        with col2:
            st.write(f"**CRC→USD Rate:** {current_fx_rate:.0f}")
            st.write(f"**CRC in USD:** ${costa_crc_usd:,.0f}")
    
    with st.expander("Hong Kong Details"):
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Monthly Cost:** ${hk_usd:,.0f}")
            st.write(f"**Daily Cost:** ${hk_usd/30:,.0f}")
        with col2:
            st.write(f"**Annual Cost:** ${hk_usd*12:,.0f}")
            st.write(f"**% of Total:** {(hk_usd/(costa_usd_cr + costa_crc_usd + hk_usd + huub_interest + google_ads)*100):.1f}%")
    
    with st.expander("Stripe & Variable Costs"):
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Stripe Fee Rate:** {stripe_fee_pct:.1f}%")
            sample_sales = 125000
            stripe_cost = sample_sales * (stripe_fee_pct / 100)
            st.write(f"**On ${sample_sales:,} sales:** ${stripe_cost:,.0f}")
        with col2:
            st.write(f"**Google Ads:** ${google_ads:,.0f}")
            st.write(f"**Total Variable:** ${google_ads + stripe_cost:,.0f}")
    
    with st.expander("Huub Loan Details"):
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Monthly Interest:** ${huub_interest:,.0f}")
            st.write(f"**Principal Amount:** ${huub_principal:,.0f}")
        with col2:
            annual_interest = huub_interest * 12
            interest_rate = (annual_interest / huub_principal * 100) if huub_principal > 0 else 0
            st.write(f"**Effective Rate:** {interest_rate:.1f}%")

    with tabs[0]:  # Overview Tab
        st.subheader("Cost Overview")
        
        # Convert CRC to USD (assuming 520 CRC/USD)
        current_fx_rate = get_monthly_rate()
        costa_crc_usd = apply_fx_conversion(costa_crc, current_fx_rate)
        
        # Calculate total monthly costs
        total_monthly_costs = costa_usd_cr + costa_crc_usd + hk_usd + huub_principal + huub_interest + google_ads
        
        # Display key metrics in columns
        col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Monthly Costs", f"${total_monthly_costs:,.0f}")
    
    with col2:
        fixed_costs = costa_usd_cr + costa_crc_usd + hk_usd + huub_principal + huub_interest
    
    with col1:
        largest_cost = max(costa_usd_cr, costa_crc_usd, hk_usd, huub_interest, google_ads)
        st.metric("Largest Cost Item", f"${largest_cost:,.0f}")
    
    with col2:
        fixed_costs = costa_usd_cr + costa_crc_usd + hk_usd + huub_interest
        st.metric("Fixed Costs", f"${fixed_costs:,.0f}")
    
    with col3:
        variable_costs = google_ads  # Simplified
        st.metric("Variable Costs", f"${variable_costs:,.0f}")
    
    with col4:
        cost_per_day = total_monthly_costs / 30
        st.metric("Cost per Day", f"${cost_per_day:,.0f}")

try:
    costs_df = load_costs_data()
except Exception as e:
    st.error(f"Data load error (costs): {e}")
    costs_df = pd.DataFrame()

try:
    combined_df = load_combined_data()
except Exception as e:
    st.error(f"Data load error: {e}")
    combined_df = pd.DataFrame()

if not costs_df.empty or not combined_df.empty:
    # Revenue Impact Analysis
    st.subheader("Revenue Impact & Margin Analysis")
    
    # Get sales data for margin calculations
    if not combined_df.empty and 'Sales_USD' in combined_df.columns:
        total_sales = combined_df['Sales_USD'].sum()
        avg_monthly_sales = combined_df['Sales_USD'].mean()
        
        # Calculate Stripe fees based on sales
        stripe_fees = total_sales * (stripe_fee_pct / 100)
        
        # Update total costs including Stripe fees
        total_all_costs = total_monthly_costs + stripe_fees
        
        # Calculate margins
        gross_margin = total_sales - total_all_costs
        margin_percentage = (gross_margin / total_sales * 100) if total_sales > 0 else 0
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Revenue", f"${total_sales:,.0f}")
        with col2:
            st.metric("Total Costs", f"${total_all_costs:,.0f}")
        with col3:
            st.metric("Gross Margin", f"${gross_margin:,.0f}")
        with col4:
            delta_color = "normal" if margin_percentage > 20 else "inverse"
            st.metric("Margin %", f"{margin_percentage:.1f}%")
        
        # Updated breakdown with Stripe fees
        st.subheader("Complete Cost Breakdown with Revenue Impact")
        
        complete_breakdown = {
            'Cost Category': [
                'Costa Rica Operations (USD)',
                'Costa Rica Operations (CRC→USD)',
                'Hong Kong Operations (USD)',
                'Stripe Processing Fees',
                'Huub Loan Principal',
                'Huub Loan Interest',
                'Google Ads (USD)',
                'TOTAL COSTS',
                'REVENUE',
                'GROSS MARGIN'
            ],
            'Amount (USD)': [
                costa_usd_cr,
                costa_crc_usd,
                hk_usd,
                stripe_fees,
                huub_principal,
                huub_interest,
                google_ads,
                total_all_costs,
                total_sales,
                gross_margin
            ],
            'Percentage of Revenue': [
                f"{(costa_usd_cr/total_sales*100):.1f}%" if total_sales > 0 else "0%",
                f"{(costa_crc_usd/total_sales*100):.1f}%" if total_sales > 0 else "0%",
                f"{(hk_usd/total_sales*100):.1f}%" if total_sales > 0 else "0%",
                f"{(stripe_fees/total_sales*100):.1f}%" if total_sales > 0 else "0%",
                f"{(huub_principal/total_sales*100):.1f}%" if total_sales > 0 else "0%",
                f"{(huub_interest/total_sales*100):.1f}%" if total_sales > 0 else "0%",
                f"{(google_ads/total_sales*100):.1f}%" if total_sales > 0 else "0%",
                f"{(total_all_costs/total_sales*100):.1f}%" if total_sales > 0 else "0%",
                "100.0%",
                f"{margin_percentage:.1f}%"
            ]
        }
        
        complete_df = pd.DataFrame(complete_breakdown)
        st.dataframe(complete_df, use_container_width=True)
        
        # Cost Impact Analysis
        st.subheader("Cost Impact Analysis")
        
        # Compare with historical data if available
        if not costs_df.empty:
            historical_avg_costs = costs_df['Costs_USD'].mean() if 'Costs_USD' in costs_df.columns else 0
            cost_difference = total_all_costs - historical_avg_costs
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Historical Avg Costs", f"${historical_avg_costs:,.0f}")
            with col2:
                delta_color = "inverse" if cost_difference > 0 else "normal"
                st.metric("Cost Change vs Historical", f"${cost_difference:,.0f}")
            
            if cost_difference > 0:
                st.warning(f"Costs increased by ${cost_difference:,.0f} compared to historical average")
            else:
                st.success(f"Costs decreased by ${abs(cost_difference):,.0f} compared to historical average")
    else:
        st.info("Revenue data not available for margin analysis")
    
    # Database upload section
    st.subheader("Upload Costs Data to Database")
    
    uploaded = st.file_uploader("Upload Costs CSV", type="csv")
    if uploaded and st.button("Save to DB"):
        # Save uploaded file temporarily and then upsert to database
        temp_path = f"temp_{uploaded.name}"
        with open(temp_path, "wb") as f:
            f.write(uploaded.getbuffer())
        
        try:
            upsert_from_csv('cash_out', temp_path)
            st.success("Data saved to database!")
            os.remove(temp_path)  # Clean up temp file
            st.rerun()  # Refresh to show new data
        except Exception as e:
            st.error(f"Error saving to database: {str(e)}")
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    # Display data from database
    st.subheader("Database Upload Records")
    
    try:
        df_db = load_table('cash_out')
    except Exception as e:
        st.error(f"Data load error (cash_out table): {e}")
        df_db = pd.DataFrame()
    if not df_db.empty:
        st.dataframe(df_db, use_container_width=True)
    else:
        st.info("No cost records found in database")
    
    # Cost breakdown table
    st.subheader("Detailed Cost Breakdown")
    
    if not costs_df.empty:
        # Add month column for better display
        display_df = costs_df.copy()
        if 'Date' in display_df.columns:
            display_df['Month'] = display_df['Date'].dt.strftime('%Y-%m')
        
        st.dataframe(display_df, use_container_width=True)
        
        # Cost trend chart
        st.subheader("Cost Trends")
        if 'Date' in costs_df.columns:
            chart_data = costs_df.set_index('Date')[['Costs_USD']]
            st.line_chart(chart_data)
    
    # Currency conversion section
    st.subheader("Currency Conversion Analysis")
    
    # FX rate scenario selector
    try:
        scenarios = get_rate_scenarios()
        scenario = st.selectbox("Select FX Rate Scenario", scenarios)
    except Exception as e:
        st.error(f"Error loading FX scenarios: {e}")
        scenario = 'base'
    
    if not combined_df.empty and 'Costs_CRC' in combined_df.columns:
        # Apply FX conversion with selected scenario
        converted_df = apply_fx_conversion(combined_df, rate_column=scenario)
        
        if 'Costs_USD_From_CRC' in converted_df.columns:
            # Display conversion results
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Original Costs:**")
                original_usd = combined_df['Costs_USD'].sum()
                original_crc = combined_df['Costs_CRC'].sum()
                st.write(f"USD: ${original_usd:,.0f}")
                st.write(f"CRC: ₡{original_crc:,.0f}")
            
            with col2:
                st.write(f"**With {scenario} Conversion:**")
                converted_crc_to_usd = converted_df['Costs_USD_From_CRC'].sum()
                total_converted = original_usd + converted_crc_to_usd
                st.write(f"CRC→USD: ${converted_crc_to_usd:,.0f}")
                st.write(f"Total USD: ${total_converted:,.0f}")
            
            # Show conversion impact
            impact = converted_crc_to_usd
            st.metric("FX Impact on Total Costs", f"${impact:,.0f}")
            
            # Detailed conversion table
            st.subheader("Detailed Conversion Breakdown")
            conversion_display = converted_df[['Date', 'Costs_USD', 'Costs_CRC', 'Costs_USD_From_CRC']].copy()
            conversion_display['Total_USD_Costs'] = conversion_display['Costs_USD'] + conversion_display['Costs_USD_From_CRC']
            st.dataframe(conversion_display, use_container_width=True)
    
    # Cost analysis insights
    st.subheader("Cost Analysis Insights")
    
    if not costs_df.empty and len(costs_df) > 1:
        # Month-over-month analysis
        costs_df_sorted = costs_df.sort_values('Date')
        if len(costs_df_sorted) >= 2:
            latest_cost = costs_df_sorted['Costs_USD'].iloc[-1]
            previous_cost = costs_df_sorted['Costs_USD'].iloc[-2]
            
            if latest_cost > previous_cost:
                change = ((latest_cost - previous_cost) / previous_cost) * 100
                st.warning(f"Costs increased by {change:.1f}% from previous month")
            elif latest_cost < previous_cost:
                change = ((previous_cost - latest_cost) / previous_cost) * 100
                st.success(f"Costs decreased by {change:.1f}% from previous month")
            else:
                st.info("Costs remained stable from previous month")
        
        # Cost distribution
        if 'Costs_USD' in costs_df.columns:
            st.write("**Cost Statistics:**")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.write(f"Min: ${costs_df['Costs_USD'].min():,.0f}")
            with col2:
                st.write(f"Max: ${costs_df['Costs_USD'].max():,.0f}")
            with col3:
                st.write(f"Std Dev: ${costs_df['Costs_USD'].std():,.0f}")
else:
    st.warning("No cost data available. Please check your data sources.")

# Main execution wrapper
try:
    _mpa_v1()
except Exception as e:
    st.error(f"App error: {e}")
