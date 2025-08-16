import streamlit as st

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
try:
    import plotly.express as px
    import plotly.graph_objects as go
except ImportError:
    px = None
    go = None

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.storage import get_combined_data, load_settings
from services.fx import get_yearly_fx_rates, convert_crc_costs_by_year, calculate_fx_impact_table

def fetch_macro():
    """Stub function for future macro data API calls"""
    # Future API call to fetch real-time macro indicators
    # Could integrate with FRED, Bloomberg, or other economic data APIs
    return {
        'us_consumer_confidence': 58.6,
        'economic_sentiment': 53.4,
        'last_updated': 'Aug 2025'
    }

st.title("Scenario Planning & Projections")


# Macro Indicators Section
st.subheader("Macro Indicators")

# Get macro data (currently using stub)
macro_data = fetch_macro()

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("US Consumer Confidence", f"{macro_data['us_consumer_confidence']}", "UMich Prelim")
with col2:
    st.metric("Economic Sentiment", f"{macro_data['economic_sentiment']}", "LSEG/Ipsos")
with col3:
    st.metric("Last Updated", macro_data['last_updated'])

# Impact guidance based on sentiment levels
if macro_data['economic_sentiment'] < 55.0 or macro_data['us_consumer_confidence'] < 60.0:
    st.write("**Economic Guidance:** In low sentiment environment, consider adjusting Google Ads up 20% to address conversion challenges")
else:
    st.write("**Economic Guidance:** Macro indicators suggest stable consumer environment")

# Load data
try:
    df = get_combined_data()
except Exception as e:
    st.error(f"Data load error: {e}")
    df = pd.DataFrame()

if not df.empty:
    # Base metrics for projections
    if not df.empty and 'Sales_USD' in df.columns:
        avg_monthly_sales = df['Sales_USD'].mean()
        avg_monthly_costs = df['Costs_USD'].mean() if 'Costs_USD' in df.columns else 0
        
        st.subheader("Base Metrics")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Avg Monthly Sales", f"${avg_monthly_sales:,.0f}")
        with col2:
            st.metric("Avg Monthly Costs", f"${avg_monthly_costs:,.0f}")
        with col3:
            net_monthly = avg_monthly_sales - avg_monthly_costs
            st.metric("Avg Monthly Net", f"${net_monthly:,.0f}")
        
        # Per-Year FX Rate Configuration
        st.subheader("Per-Year FX Rate Configuration")
        
        # Initialize FX rates with specific defaults
        fx_years = {1: 502.0, 2: 510.0, 3: 520.0, 4: 520.0, 5: 530.0}
        
        st.write("**Configure CRC/USD rates for each projection year:**")
        col1, col2, col3, col4, col5 = st.columns(5)
        
        # Create input fields for each year with error handling
        cols = [col1, col2, col3, col4, col5]
        try:
            for i, year in enumerate(range(1, 6)):
                with cols[i]:
                    fx_years[year] = st.number_input(
                        f"CRC/USD Year {year}", 
                        value=float(fx_years[year]), 
                        step=5.0, 
                        min_value=400.0, 
                        max_value=600.0
                    )
        except Exception as e:
            st.error(f"Error loading FX rate inputs: {e}")
            # Use default values if inputs fail
            fx_years = {1: 502.0, 2: 510.0, 3: 520.0, 4: 520.0, 5: 530.0}
        
        # Use the configured FX rates
        year_fx_rates = fx_years
        
        # FX Impact Analysis with CRC Costs
        st.subheader("FX Impact Analysis")
        
        # Get CRC cost from settings with DB fallback
        sample_crc_cost = get_setting('costa_crc', 38000000.0)
        st.write(f"**Using CRC cost from Settings:** ₡{sample_crc_cost:,.0f}")
        
        # Calculate USD costs for each year with error handling
        try:
            fx_impact_data = []
            base_year_usd_cost = sample_crc_cost / fx_years[1]
            
            for year in range(1, 6):
                usd_cost = sample_crc_cost / fx_years[year]
                delta_vs_year1 = usd_cost - base_year_usd_cost
                delta_pct = (delta_vs_year1 / base_year_usd_cost * 100) if base_year_usd_cost > 0 else 0
                
                fx_impact_data.append({
                    'Year': year,
                    'FX Rate (CRC/USD)': fx_years[year],
                    'CRC Cost': f"₡{sample_crc_cost:,.0f}",
                    'USD Cost': f"${usd_cost:,.0f}",
                    'Delta vs Year 1': f"${delta_vs_year1:+,.0f}",
                    'Delta %': f"{delta_pct:+.1f}%"
                })
            
            fx_impact_df = pd.DataFrame(fx_impact_data)
            st.dataframe(fx_impact_df, use_container_width=True)
        except Exception as e:
            st.error(f"Error calculating FX impact: {e}")
            st.info("Using default FX rates for calculations")
        
        # Visual FX impact summary
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**FX Rate Trend:**")
            rate_change = fx_years[5] - fx_years[1]
            if rate_change > 0:
                st.write(f"**CRC Weakening:** +{rate_change} over 5 years")
                st.write("📈 CRC costs in USD will decrease")
            elif rate_change < 0:
                st.write(f"**CRC Strengthening:** {rate_change} over 5 years")
                st.write("📉 CRC costs in USD will increase")
            else:
                st.write("**CRC Stable:** No change over 5 years")
        
        with col2:
            year5_usd_cost = sample_crc_cost / fx_years[5]
            total_impact = year5_usd_cost - base_year_usd_cost
            st.write("**5-Year Cost Impact:**")
            if total_impact > 0:
                st.write(f"**Cost Increase:** +${total_impact:,.0f}")
            elif total_impact < 0:
                st.write(f"**Cost Savings:** ${abs(total_impact):,.0f}")
            else:
                st.write("**No Impact:** Costs remain stable")
        
        # Cost Levers Configuration
        st.subheader("Cost Structure Levers")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Base Cost Inputs (from Settings with DB fallback):**")
            # Get costs from settings with DB fallback
            costa_usd_base = get_setting('costa_usd', 19000.0)
            costa_crc_base = get_setting('costa_crc', 38000000.0)
            hk_usd_base = get_setting('hk_usd', 40000.0)
            google_ads_base = get_setting('google_ads', 27500.0)
            stripe_fee_pct = get_setting('stripe_fee', 4.2)
            huub_principal = get_setting('huub_principal', 1250000.0)
            huub_interest = get_setting('huub_interest', 18750.0)
            
            st.write(f"✅ **Loaded from Settings:**")
            st.write(f"• Costa Rica USD: ${costa_usd_base:,.0f}")
            st.write(f"• Costa Rica CRC: ₡{costa_crc_base:,.0f}")
            st.write(f"• Hong Kong USD: ${hk_usd_base:,.0f}")
            st.write(f"• Google Ads: ${google_ads_base:,.0f}")
            st.write(f"• Stripe Fee: {stripe_fee_pct}%")
            st.write(f"• Huub Principal: ${huub_principal:,.0f}")
            st.write(f"• Huub Interest: ${huub_interest:,.0f}")
        
        with col2:
            st.write("**Economic Impact Multipliers:**")
            ads_multiplier = st.slider("Ads Cost Multiplier (Economy)", 1.0, 1.5, 1.2, step=0.05)
            costa_multiplier = st.slider("Costa Rica Cost Multiplier", 0.8, 1.3, 1.0, step=0.05)
            hk_multiplier = st.slider("Hong Kong Cost Multiplier", 0.9, 1.4, 1.0, step=0.05)
            loan_multiplier = st.slider("Loan Cost Multiplier", 0.5, 1.5, 1.0, step=0.1)
        
        # Enhanced Seasonality Configuration
        st.subheader("Seasonality Controls")
        
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        
        col1, col2 = st.columns(2)
        
        with col1:
            high_months = st.multiselect("High Sales Months", options=months, default=['Dec', 'Mar'])
            seasonality_boost = st.slider("High Season Boost (%)", 10.0, 50.0, 20.0)
        
        with col2:
            low_months = st.multiselect("Low Sales Months", options=months, default=['Feb', 'Aug'])
            seasonality_reduction = st.slider("Low Season Reduction (%)", 5.0, 30.0, 15.0)
        
        # Macro-Economic Tie-in
        st.subheader("Macro-Economic Integration")
        
        # Get macro data for consumer confidence
        consumer_confidence = macro_data.get('us_consumer_confidence', 70.0)
        
        # Automatic ads multiplier based on consumer confidence
        if consumer_confidence < 60:
            auto_ads_multiplier = 1.2
            st.warning(f"⚠️ **Low Consumer Confidence ({consumer_confidence}):** Ads multiplier increased to 1.2x (20% increase)")
            st.write("**Strategy:** Increase marketing spend to counter low consumer sentiment")
        else:
            auto_ads_multiplier = 1.0
            st.success(f"✅ **Healthy Consumer Confidence ({consumer_confidence}):** Normal ads spending")
        
        # Economic Environment Controls
        st.subheader("Economic Environment Controls")
        
        col1, col2 = st.columns(2)
        
        with col1:
            economy_scenario = st.selectbox("Economic Scenario", ["Normal", "Recession", "Growth"], index=0)
            if economy_scenario == "Recession":
                economy_sales_impact = st.slider("Sales Impact (%)", -30.0, 0.0, -10.0)
                economy_ads_multiplier = st.slider("Ads Cost Multiplier", 1.0, 2.0, max(1.5, auto_ads_multiplier))
            elif economy_scenario == "Growth":
                economy_sales_impact = st.slider("Sales Impact (%)", 0.0, 30.0, 15.0)
                economy_ads_multiplier = st.slider("Ads Cost Multiplier", 0.5, 1.0, min(0.8, auto_ads_multiplier))
            else:
                economy_sales_impact = 0.0
                economy_ads_multiplier = auto_ads_multiplier  # Use macro-driven multiplier
        
        with col2:
            st.write("**Economic Impact Summary:**")
            st.write(f"• Consumer Confidence: {consumer_confidence}")
            st.write(f"• Auto Ads Multiplier: {auto_ads_multiplier:.1f}x")
            if economy_scenario == "Recession":
                st.write(f"• Sales: {economy_sales_impact:+.1f}%")
                st.write(f"• Final Ads Cost: {economy_ads_multiplier:.1f}x")
                st.write("• Strategy: Counter recession with marketing")
            elif economy_scenario == "Growth":
                st.write(f"• Sales: +{economy_sales_impact:.1f}%")
                st.write(f"• Final Ads Cost: {economy_ads_multiplier:.1f}x")
                st.write("• Strategy: Optimize for growth")
            else:
                st.write(f"• Sales: Baseline")
                st.write(f"• Final Ads Cost: {economy_ads_multiplier:.1f}x")
                st.write("• Strategy: Macro-driven adjustments")
        
        # Individual Cost Levers (from Settings with DB fallback)
        st.subheader("Individual Cost Levers")
        
        st.write("✅ **Using costs from Settings:**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            costa_usd_multiplier = st.slider("Costa Rica USD Multiplier", 0.5, 2.0, 1.0, step=0.1)
            costa_crc_multiplier = st.slider("Costa Rica CRC Multiplier", 0.5, 2.0, 1.0, step=0.1)
            hk_usd_multiplier = st.slider("Hong Kong USD Multiplier", 0.5, 2.0, 1.0, step=0.1)
            google_ads_multiplier = st.slider("Google Ads Multiplier", 0.5, 3.0, economy_ads_multiplier, step=0.1)
        
        with col2:
            stripe_fee_multiplier = st.slider("Stripe Fee Multiplier", 0.8, 1.5, 1.0, step=0.1)
            huub_principal_multiplier = st.slider("Huub Principal Multiplier", 0.0, 2.0, 1.0, step=0.1)
            huub_interest_multiplier = st.slider("Huub Interest Multiplier", 0.5, 2.0, 1.0, step=0.1)
        
        # Calculate adjusted costs using settings values
        adj_costa_usd = costa_usd_base * costa_usd_multiplier
        adj_costa_crc = costa_crc_base * costa_crc_multiplier
        adj_hk_usd = hk_usd_base * hk_usd_multiplier
        adj_google_ads = google_ads_base * google_ads_multiplier
        adj_stripe_fee = stripe_fee_pct * stripe_fee_multiplier
        adj_huub_principal = huub_principal * huub_principal_multiplier
        adj_huub_interest = huub_interest * huub_interest_multiplier
        
        # Scenario planning controls
        st.subheader("Projection Controls")
        
        col1, col2 = st.columns(2)
        
        with col1:
            growth_rate = st.slider("Annual Sales Growth Rate (%)", -20.0, 50.0, 5.0) / 100
            years = st.slider("Projection Period (Years)", 1, 10, 5)
        
        with col2:
            include_seasonality = st.checkbox("Apply Seasonality to Projections", value=True)
            focus_end_month_cash = st.checkbox("Focus on End-Month Cash Position", value=True)
        
        # Generate monthly projections with enhanced cost structure
        st.subheader("Monthly Financial Projections (5-Year Detail)")
        
        # Create seasonality factors
        def get_seasonality_factor(month_name):
            if month_name in high_months:
                return 1 + (seasonality_boost / 100)
            elif month_name in low_months:
                return 1 - (seasonality_reduction / 100)
            else:
                return 1.0
        
        # Generate monthly data for 5 years
        monthly_forecast_data = []
        fx_projection_data = []
        
        for year in range(1, years + 1):
            # Base annual projections
            base_annual_sales = avg_monthly_sales * 12 * (1 + growth_rate) ** year
            
            # Calculate enhanced cost structure using individual levers and FX rates
            costa_usd_annual = adj_costa_usd * 12 * (1.02) ** year  # 2% annual inflation
            
            # Convert CRC costs using year-specific FX rates
            costa_crc_usd_annual = (adj_costa_crc * 12 * (1.02) ** year) / fx_years[year]
            
            hk_usd_annual = adj_hk_usd * 12 * (1.02) ** year
            
            # Apply macro-driven ads multiplier
            google_ads_annual = adj_google_ads * 12 * economy_ads_multiplier * (1.03) ** year
            
            huub_principal_annual = adj_huub_principal if year == 1 else 0  # One-time in year 1
            huub_interest_annual = adj_huub_interest * (1.01) ** year  # 1% annual increase
            
            # Apply economy impact to sales
            economy_adjusted_sales = base_annual_sales * (1 + economy_sales_impact / 100)
            # Calculate total annual costs (using FX-converted CRC costs)
            total_annual_costs = (costa_usd_annual + costa_crc_usd_annual + hk_usd_annual + 
                                google_ads_annual + huub_principal_annual + huub_interest_annual)
            
            
            # Store for FX analysis
            fx_projection_data.append({
                'Year': year,
                'CRC Costs (Original)': adj_costa_crc * 12 * (1.02) ** year,
                'CRC Costs (USD)': costa_crc_usd_annual,
                'FX Rate Used': fx_years[year],
                'Google Ads (Base)': adj_google_ads * 12 * (1.03) ** year,
                'Google Ads (Adjusted)': google_ads_annual,
                'Ads Multiplier': economy_ads_multiplier
            })
            
            base_annual_costs = costa_usd_annual + costa_crc_usd_annual + hk_usd_annual + google_ads_annual
            
            # Generate monthly breakdown
            for month_idx, month_name in enumerate(months):
                month_date = f"Year {year} - {month_name}"
                
                # Apply seasonality to sales
                seasonality_factor = get_seasonality_factor(month_name) if include_seasonality else 1.0
                monthly_sales = (economy_adjusted_sales / 12) * seasonality_factor
                monthly_costs = total_annual_costs / 12
                monthly_net_cash = monthly_sales - monthly_costs
                
                # Calculate end-month cash position (cumulative)
                if month_idx == 0 and year == 1:
                    cumulative_cash = monthly_net_cash
                else:
                    prev_cumulative = monthly_forecast_data[-1].get('Cumulative_Cash', 0) if monthly_forecast_data else 0
                    cumulative_cash = prev_cumulative + monthly_net_cash
                
                monthly_forecast_data.append({
                    'Year': year,
                    'Month': month_name,
                    'Date': month_date,
                    'Sales': monthly_sales,
                    'Costs': monthly_costs,
                    'Net_Cash_Flow': monthly_net_cash,
                    'Cumulative_Cash': cumulative_cash,
                    'Seasonality_Factor': seasonality_factor,
                    'Economy_Impact': economy_sales_impact
                })
                
                # Monthly costs (distributed evenly)
                monthly_costs = base_annual_costs / 12
                
                # Add Stripe fees based on sales
                stripe_fees = monthly_sales * (stripe_fee_pct / 100)
                total_monthly_costs = monthly_costs + stripe_fees
                
                monthly_net = monthly_sales - total_monthly_costs
                
                monthly_forecast_data.append({
                    'Month': month_date,
                    'Year': year,
                    'Month_Name': month_name,
                    'Sales': monthly_sales,
                    'Costs': total_monthly_costs,
                    'Net': monthly_net,
                    'Seasonality_Factor': seasonality_factor,
                    'Costa_USD': costa_usd_annual / 12,
                    'Costa_CRC_USD': costa_crc_usd_annual / 12,
                    'HK_USD': hk_usd_annual / 12,
                    'Google_Ads': google_ads_annual / 12,
                    'Stripe_Fees': stripe_fees
                })
            
            # Store annual FX projection data
            if year in year_fx_rates:
                fx_projection_data.append({
                    'Year': year,
                    'FX Rate': year_fx_rates[year],
                    'CRC Costs (USD)': costa_crc_usd_annual,
                    'Total Costs (USD)': base_annual_costs,
                    'Sales (USD)': base_annual_sales,
                    'Net Cash Flow': base_annual_sales - base_annual_costs
                })
        
        # Create monthly forecast DataFrame
        monthly_df = pd.DataFrame(monthly_forecast_data)
        
        # Display monthly projections table
        st.subheader("Monthly Projections Table")
        
        # Format the display table
        display_df = monthly_df[['Month', 'Sales', 'Costs', 'Net', 'Seasonality_Factor']].copy()
        display_df['Sales'] = display_df['Sales'].apply(lambda x: f"${x:,.0f}")
        display_df['Costs'] = display_df['Costs'].apply(lambda x: f"${x:,.0f}")
        display_df['Net'] = display_df['Net'].apply(lambda x: f"${x:,.0f}")
        display_df['Seasonality_Factor'] = display_df['Seasonality_Factor'].apply(lambda x: f"{x:.2f}x")
        
        st.dataframe(display_df, use_container_width=True)
        
        # Annual summary from monthly data
        annual_summary = monthly_df.groupby('Year').agg({
            'Sales': 'sum',
            'Costs': 'sum',
            'Net': 'sum'
        }).reset_index()
        annual_summary['Cumulative_Net'] = annual_summary['Net'].cumsum()
        
        forecast_data = []
        for _, row in annual_summary.iterrows():
            forecast_data.append({
                'Year': int(row['Year']),
                'Projected Sales': row['Sales'],
                'Projected Costs': row['Costs'],
                'Net Cash Flow': row['Net'],
                'Cumulative Cash Flow': row['Cumulative_Net']
            })
        
        df_forecast = pd.DataFrame(forecast_data)
        
        # Display annual summary table
        st.subheader("Annual Summary")
        df_forecast = pd.DataFrame(forecast_data)
        st.dataframe(df_forecast, use_container_width=True)
        
        # Cost Structure Analysis
        st.subheader("Cost Structure Breakdown by Year")
        
        cost_breakdown_data = []
        for year in range(1, years + 1):
            year_data = monthly_df[monthly_df['Year'] == year]
            total_costa_usd = year_data['Costa_USD'].sum()
            total_costa_crc_usd = year_data['Costa_CRC_USD'].sum()
            total_hk_usd = year_data['HK_USD'].sum()
            total_google_ads = year_data['Google_Ads'].sum()
            total_stripe_fees = year_data['Stripe_Fees'].sum()
            
            cost_breakdown_data.append({
                'Year': year,
                'Costa Rica USD': total_costa_usd,
                'Costa Rica CRC→USD': total_costa_crc_usd,
                'Hong Kong USD': total_hk_usd,
                'Google Ads': total_google_ads,
                'Stripe Fees': total_stripe_fees,
                'Total Costs': year_data['Costs'].sum()
            })
        
        cost_breakdown_df = pd.DataFrame(cost_breakdown_data)
        st.dataframe(cost_breakdown_df, use_container_width=True)
        
        # Economic Impact Analysis
        st.subheader("Economic Impact Analysis")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.write("**Cost Multipliers Applied:**")
            st.write(f"• Ads Multiplier: {ads_multiplier:.2f}x")
            st.write(f"• Costa Rica: {costa_multiplier:.2f}x")
            st.write(f"• Hong Kong: {hk_multiplier:.2f}x")
        
        with col2:
            base_google_ads_5y = google_ads_base * 12 * 5
            adjusted_google_ads_5y = base_google_ads_5y * ads_multiplier
            ads_impact = adjusted_google_ads_5y - base_google_ads_5y
            
            st.write("**5-Year Economic Impact:**")
            st.write(f"• Base Google Ads: ${base_google_ads_5y:,.0f}")
            st.write(f"• Adjusted: ${adjusted_google_ads_5y:,.0f}")
            if ads_impact > 0:
                st.write(f"• **Additional Cost:** +${ads_impact:,.0f}")
            else:
                st.write(f"• **Cost Savings:** ${abs(ads_impact):,.0f}")
        
        with col3:
            if include_seasonality:
                avg_seasonality = (len(high_months) * (1 + seasonality_boost/100) + 
                                 len(low_months) * (1 - seasonality_reduction/100) + 
                                 (12 - len(high_months) - len(low_months))) / 12
                st.write("**Seasonality Impact:**")
                st.write(f"• Avg Factor: {avg_seasonality:.2f}x")
                st.write(f"• High Months: {len(high_months)}")
                st.write(f"• Low Months: {len(low_months)}")
        
        # FX Impact Projection Table
        if fx_projection_data:
            st.subheader("FX Impact on Projections")
            fx_df = pd.DataFrame(fx_projection_data)
            st.dataframe(fx_df, use_container_width=True)
            
            # FX Impact Summary
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**FX Rate Trend:**")
                rate_change = year_fx_rates[5] - year_fx_rates[1] if 5 in year_fx_rates else 0
                if rate_change > 0:
                    st.write(f"**FX Trend:** CRC weakening: +{rate_change} over 5 years")
                elif rate_change < 0:
                    st.write(f"**FX Trend:** CRC strengthening: {rate_change} over 5 years")
                else:
                    st.write(f"**FX Trend:** CRC stable over projection period")
            
            with col2:
                if len(fx_projection_data) >= 2:
                    year1_cost = fx_projection_data[0]['CRC Costs (USD)']
                    year5_cost = fx_projection_data[-1]['CRC Costs (USD)']
                    cost_impact = year5_cost - year1_cost
                    st.write("**5-Year Cost Impact:**")
                    if cost_impact > 0:
                        st.write(f"**5-Year Impact:** Cost increase: +${cost_impact:,.0f}")
                    elif cost_impact < 0:
                        st.write(f"**5-Year Impact:** Cost savings: ${abs(cost_impact):,.0f}")
                    else:
                        st.write(f"**5-Year Impact:** No cost impact from FX")
        
        # Convert to DataFrame for analysis
        df_monthly_forecast = pd.DataFrame(monthly_forecast_data)
        
        # Focus on End-Month Cash Position
        if focus_end_month_cash:
            st.subheader("End-Month Cash Position Analysis")
            
            # Show year-end cash positions
            year_end_data = []
            for year in range(1, years + 1):
                year_data = df_monthly_forecast[df_monthly_forecast['Year'] == year]
                if not year_data.empty:
                    dec_data = year_data[year_data['Month'] == 'Dec']
                    if not dec_data.empty:
                        end_cash = dec_data['Cumulative_Cash'].iloc[0]
                        year_end_data.append({
                            'Year': f'Year {year}',
                            'End_Cash_Position': end_cash,
                            'Annual_Net_Flow': year_data['Net_Cash_Flow'].sum()
                        })
            
            year_end_df = pd.DataFrame(year_end_data)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Year-End Cash Positions:**")
                for _, row in year_end_df.iterrows():
                    delta_color = "normal" if row['End_Cash_Position'] >= 0 else "inverse"
                    st.metric(row['Year'], f"${row['End_Cash_Position']:,.0f}", f"${row['Annual_Net_Flow']:,.0f}")
            
            with col2:
                st.write("**Cash Position Chart:**")
                if not year_end_df.empty:
                    chart_data = year_end_df.set_index('Year')[['End_Cash_Position']]
                    st.bar_chart(chart_data)
        
        # Monthly Projections Table
        st.subheader("5-Year Monthly Projections")
        
        # Display options
        col1, col2 = st.columns(2)
        
        with col1:
            show_year = st.selectbox("Show Year", ["All"] + [f"Year {i}" for i in range(1, years + 1)])
        with col2:
            show_metrics = st.multiselect("Show Metrics", 
                                        ["Sales", "Costs", "Net_Cash_Flow", "Cumulative_Cash", "Seasonality_Factor"],
                                        default=["Sales", "Costs", "Net_Cash_Flow", "Cumulative_Cash"])
        
        # Filter data
        if show_year != "All":
            year_num = int(show_year.split()[1])
            display_monthly_df = df_monthly_forecast[df_monthly_forecast['Year'] == year_num].copy()
        else:
            display_monthly_df = df_monthly_forecast.copy()
        
        # Format for display
        display_cols = ['Year', 'Month'] + show_metrics
        display_monthly_df = display_monthly_df[display_cols]
        
        # Format currency columns
        for col in ['Sales', 'Costs', 'Net_Cash_Flow', 'Cumulative_Cash']:
            if col in display_monthly_df.columns:
                display_monthly_df[col] = display_monthly_df[col].apply(lambda x: f"${x:,.0f}")
        
        if 'Seasonality_Factor' in display_monthly_df.columns:
            display_monthly_df['Seasonality_Factor'] = display_monthly_df['Seasonality_Factor'].apply(lambda x: f"{x:.2f}x")
        
        st.dataframe(display_monthly_df, use_container_width=True)
        
        # Enhanced Visualizations
        st.subheader("Projection Visualizations")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Monthly Sales & Costs**")
            chart_data = df_monthly_forecast.set_index('Date')[['Sales', 'Costs']]
            st.line_chart(chart_data)
        
        with col2:
            st.write("**Cumulative Cash Position**")
            chart_data = df_monthly_forecast.set_index('Date')[['Cumulative_Cash']]
            st.line_chart(chart_data)
        
        # Seasonality Impact Chart
        if include_seasonality:
            st.subheader("Seasonality Impact")
            seasonality_chart = df_monthly_forecast.set_index('Date')[['Seasonality_Factor']]
            st.line_chart(seasonality_chart)
            st.subheader("Monthly Seasonality Impact")
            
            # Show first year monthly data as example
            first_year_data = monthly_df[monthly_df['Year'] == 1]
            seasonality_chart = first_year_data.set_index('Month_Name')[['Sales', 'Costs', 'Net']]
            st.line_chart(seasonality_chart)
            
            # Seasonality summary
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**High Season Months:**")
                for month in high_months:
                    boost_factor = 1 + (seasonality_boost / 100)
                    st.write(f"• {month}: {boost_factor:.2f}x multiplier")
            
            with col2:
                st.write("**Low Season Months:**")
                for month in low_months:
                    reduction_factor = 1 - (seasonality_reduction / 100)
                    st.write(f"• {month}: {reduction_factor:.2f}x multiplier")
        
        # Scenario comparison
        st.subheader("Scenario Comparison")
        
        # Create multiple scenarios
        scenarios = {
            'Conservative': {'growth': -0.05, 'cost_change': 0.10},
            'Base Case': {'growth': growth_rate, 'cost_change': 0.0},
            'Optimistic': {'growth': growth_rate + 0.10, 'cost_change': -0.05}
        }
        
        scenario_results = []
        for scenario_name, params in scenarios.items():
            year_5_sales = avg_monthly_sales * 12 * (1 + params['growth']) ** 5
            year_5_costs = avg_monthly_costs * 12 * (1 + params['cost_change']) ** 5
            year_5_net = year_5_sales - year_5_costs
            
            scenario_results.append({
                'Scenario': scenario_name,
                'Year 5 Sales': year_5_sales,
                'Year 5 Costs': year_5_costs,
                'Year 5 Net Cash Flow': year_5_net,
                'Growth Rate': f"{params['growth']*100:.1f}%",
                'Cost Change': f"{params['cost_change']*100:.1f}%"
            })
        
        scenario_df = pd.DataFrame(scenario_results)
        st.dataframe(scenario_df, use_container_width=True)
        
        # Break-Even Analysis
        st.subheader("Break-Even Analysis")
        
        if avg_monthly_costs > 0:
            breakeven_sales = avg_monthly_costs
            current_margin = (avg_monthly_sales - avg_monthly_costs) / avg_monthly_sales * 100 if avg_monthly_sales > 0 else 0
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Monthly Break-even Sales", f"${breakeven_sales:,.0f}")
            with col2:
                st.metric("Current Margin %", f"{current_margin:.1f}%")
            
            # Safety margin
            if avg_monthly_sales > breakeven_sales:
                safety_margin = (avg_monthly_sales - breakeven_sales) / avg_monthly_sales * 100
                st.success(f"Safety Margin: {safety_margin:.1f}% above break-even")
            else:
                deficit = (breakeven_sales - avg_monthly_sales) / breakeven_sales * 100
                st.error(f"Below break-even by {deficit:.1f}%")
        
        # Sensitivity analysis
        st.subheader("Sensitivity Analysis")
        
        st.write("**Impact of ±10% changes on Year 5 Net Cash Flow:**")
        
        base_year_5_net = avg_monthly_sales * 12 * (1 + growth_rate) ** 5 - avg_monthly_costs * 12 * (1 + 0.0) ** 5
        
        sensitivity_data = []
        for factor in ['Sales Growth', 'Cost Change']:
            if factor == 'Sales Growth':
                high_impact = avg_monthly_sales * 12 * (1 + growth_rate + 0.1) ** 5 - avg_monthly_costs * 12 * (1 + 0.0) ** 5
                low_impact = avg_monthly_sales * 12 * (1 + growth_rate - 0.1) ** 5 - avg_monthly_costs * 12 * (1 + 0.0) ** 5
            else:
                high_impact = avg_monthly_sales * 12 * (1 + growth_rate) ** 5 - avg_monthly_costs * 12 * (1 + 0.1) ** 5
                low_impact = avg_monthly_sales * 12 * (1 + growth_rate) ** 5 - avg_monthly_costs * 12 * (1 - 0.1) ** 5
            
            sensitivity_data.append({
                'Factor': factor,
                'Base Case': base_year_5_net,
                '+10% Impact': high_impact,
                '-10% Impact': low_impact,
                'Upside Potential': high_impact - base_year_5_net,
                'Downside Risk': base_year_5_net - low_impact
            })
        
        sensitivity_df = pd.DataFrame(sensitivity_data)
        st.dataframe(sensitivity_df, use_container_width=True)
        
        # HK Balance Projections
        st.subheader("HK Balance Projections")
        
        # Load starting balances from environment
        hk_start_usd = float(os.getenv('HK_START_USD', 100000))
        hk_start_hkd = float(os.getenv('HK_START_HKD', 800000))
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Starting USD Balance", f"${hk_start_usd:,.0f}")
        with col2:
            st.metric("Starting HKD Balance", f"HK${hk_start_hkd:,.0f}")
        
        # Wire transfer assumptions
        wire_frequency = st.selectbox("Wire Transfer Frequency", ["Monthly", "Quarterly", "Semi-Annual"])
        wire_amount_usd = st.number_input("Wire Amount (USD)", min_value=0.0, value=25000.0, step=5000.0)
        
        # Calculate balance projections
        months = years * 12
        balance_projections = []
        
        for scenario_name, params in scenarios.items():
            monthly_sales = avg_monthly_sales * (1 + params['growth'] / 12)
            monthly_costs = avg_monthly_costs * (1 + params['cost_change'] / 12)
            
            # Wire frequency mapping
            wire_months = {"Monthly": 1, "Quarterly": 3, "Semi-Annual": 6}[wire_frequency]
            
            current_usd = hk_start_usd
            current_hkd = hk_start_hkd
            
            for month in range(1, months + 1):
                # Monthly cash flows
                monthly_inflow = monthly_sales * (1 + params['growth'] / 12) ** (month / 12)
                monthly_outflow = monthly_costs * (1 + params['cost_change'] / 12) ** (month / 12)
                
                # Wire transfers
                wire_outflow = wire_amount_usd if month % wire_months == 0 else 0
                
                # Update balances
                current_usd = current_usd + monthly_inflow - monthly_outflow - wire_outflow
                current_hkd = current_hkd + (wire_outflow * 7.8)  # Assume 7.8 USD/HKD rate
                
                balance_projections.append({
                    'Scenario': scenario_name,
                    'Month': month,
                    'Year': month / 12,
                    'USD_Balance': current_usd,
                    'HKD_Balance': current_hkd,
                    'Total_USD_Equivalent': current_usd + (current_hkd / 7.8)
                })
        
        balance_df = pd.DataFrame(balance_projections)
        
        # Plotly chart for balance projections
        if px and go:
            fig = go.Figure()
            
            for scenario in balance_df['Scenario'].unique():
                scenario_data = balance_df[balance_df['Scenario'] == scenario]
                fig.add_trace(go.Scatter(
                    x=scenario_data['Year'],
                    y=scenario_data['Total_USD_Equivalent'],
                    mode='lines+markers',
                    name=f'{scenario} Total (USD Equiv)',
                    line=dict(width=3)
                ))
            
            fig.update_layout(
                title="HK Balance Projections (USD Equivalent)",
                xaxis_title="Years",
                yaxis_title="Balance (USD)",
                hovermode='x unified',
                height=500
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Separate USD and HKD charts
            col1, col2 = st.columns(2)
            
            with col1:
                fig_usd = px.line(balance_df, x='Year', y='USD_Balance', color='Scenario',
                                title="USD Balance Projections", height=400)
                st.plotly_chart(fig_usd, use_container_width=True)
            
            with col2:
                fig_hkd = px.line(balance_df, x='Year', y='HKD_Balance', color='Scenario',
                                title="HKD Balance Projections", height=400)
                st.plotly_chart(fig_hkd, use_container_width=True)
        
        else:
            st.warning("Install plotly for interactive charts: pip install plotly")
            st.line_chart(balance_df.pivot(index='Year', columns='Scenario', values='Total_USD_Equivalent'))
        
        # Balance summary table
        st.subheader("📊 Final Balance Summary")
        final_balances = balance_df[balance_df['Year'] == years].copy()
        final_summary = final_balances[['Scenario', 'USD_Balance', 'HKD_Balance', 'Total_USD_Equivalent']].round(0)
        st.dataframe(final_summary, use_container_width=True)
        
        # Summary metrics
        st.subheader(f"{years}-Year Summary")
        
        total_projected_sales = df_monthly_forecast['Sales'].sum()
        total_projected_costs = df_monthly_forecast['Costs'].sum()
        total_net_cash_flow = total_projected_sales - total_projected_costs
        final_cash_position = df_monthly_forecast['Cumulative_Cash'].iloc[-1] if not df_monthly_forecast.empty else 0
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(f"Total {years}-Year Sales", f"${total_projected_sales:,.0f}")
        with col2:
            st.metric(f"Total {years}-Year Costs", f"${total_projected_costs:,.0f}")
        with col3:
            st.metric(f"Total {years}-Year Net", f"${total_net_cash_flow:,.0f}")
        with col4:
            delta_color = "normal" if final_cash_position >= 0 else "inverse"
            st.metric("Final Cash Position", f"${final_cash_position:,.0f}")
        
        # Cost Breakdown Analysis
        st.subheader("Cost Component Analysis")
        
        cost_breakdown_data = {
            'Cost Component': ['Costa Rica USD', 'Costa Rica CRC', 'Hong Kong USD', 'Google Ads', 'Huub Principal', 'Huub Interest'],
            'Monthly Amount': [adj_costa_usd, adj_costa_crc/520, adj_hk_usd, adj_google_ads, adj_huub_principal/12, adj_huub_interest/12],
            'Annual Amount': [adj_costa_usd*12, adj_costa_crc, adj_hk_usd*12, adj_google_ads*12, adj_huub_principal, adj_huub_interest],
            'Multiplier Applied': [costa_usd_multiplier if 'costs' in st.session_state else 1.0,
                                 costa_crc_multiplier if 'costs' in st.session_state else 1.0,
                                 hk_usd_multiplier if 'costs' in st.session_state else 1.0,
                                 google_ads_multiplier,
                                 huub_principal_multiplier if 'costs' in st.session_state else 1.0,
                                 huub_interest_multiplier if 'costs' in st.session_state else 1.0]
        }
        
        cost_breakdown_df = pd.DataFrame(cost_breakdown_data)
        cost_breakdown_df['Monthly Amount'] = cost_breakdown_df['Monthly Amount'].apply(lambda x: f"${x:,.0f}")
        cost_breakdown_df['Annual Amount'] = cost_breakdown_df['Annual Amount'].apply(lambda x: f"${x:,.0f}")
        cost_breakdown_df['Multiplier Applied'] = cost_breakdown_df['Multiplier Applied'].apply(lambda x: f"{x:.1f}x")
        
        st.dataframe(cost_breakdown_df, use_container_width=True)
        
        # Economic impact summary
        st.subheader("Economic Impact Analysis")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.write("**Economic Scenario Impact:**")
            st.write(f"• Scenario: {economy_scenario}")
            st.write(f"• Sales Impact: {economy_sales_impact:+.1f}%")
            st.write(f"• Ads Multiplier: {economy_ads_multiplier:.1f}x")
        
        with col2:
            base_google_ads_total = adj_google_ads * 12 * years
            economy_adjusted_ads = base_google_ads_total * economy_ads_multiplier
            ads_impact = economy_adjusted_ads - base_google_ads_total
            
            st.write(f"**{years}-Year Ads Impact:**")
            st.write(f"• Base Ads Cost: ${base_google_ads_total:,.0f}")
            st.write(f"• Economy Adjusted: ${economy_adjusted_ads:,.0f}")
            if ads_impact > 0:
                st.write(f"• **Additional Cost:** +${ads_impact:,.0f}")
            else:
                st.write(f"• **Cost Savings:** ${abs(ads_impact):,.0f}")
        
        with col3:
            if include_seasonality:
                avg_seasonality = (len(high_months) * (1 + seasonality_boost/100) + 
                                 len(low_months) * (1 - seasonality_reduction/100) + 
                                 (12 - len(high_months) - len(low_months))) / 12
                st.write("**Seasonality Impact:**")
                st.write(f"• Avg Factor: {avg_seasonality:.2f}x")
                st.write(f"• High Months: {len(high_months)} (+{seasonality_boost:.0f}%)")
                st.write(f"• Low Months: {len(low_months)} (-{seasonality_reduction:.0f}%)")
        
        # Risk Analysis
        st.subheader("Risk Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Cash Flow Risks:**")
            negative_months = len(df_monthly_forecast[df_monthly_forecast['Net_Cash_Flow'] < 0])
            if negative_months > 0:
                st.write(f"⚠️ {negative_months} months with negative cash flow")
            else:
                st.write("✅ All months show positive cash flow")
            
            min_cumulative = df_monthly_forecast['Cumulative_Cash'].min()
            if min_cumulative < 0:
                st.write(f"⚠️ Lowest cash position: ${min_cumulative:,.0f}")
            else:
                st.write(f"✅ Minimum cash position: ${min_cumulative:,.0f}")
        
        with col2:
            st.write("**Scenario Sensitivity:**")
            sales_volatility = df_monthly_forecast['Sales'].std()
            cost_volatility = df_monthly_forecast['Costs'].std()
            
            st.write(f"• Sales volatility: ${sales_volatility:,.0f}")
            st.write(f"• Cost volatility: ${cost_volatility:,.0f}")
            
            if economy_scenario == "Recession":
                st.write("⚠️ Recession scenario active")
            elif economy_scenario == "Growth":
                st.title("🧮 Scenario Planning & Projections")

# Main Navigation Tabs
tabs = st.tabs(["Forecasting", "Scenarios", "Visuals", "Levers"])

# Load combined data and FX rates
try:
    combined_df = get_combined_data()
    fx_rates = get_rate_scenarios()
    
    if combined_df.empty:
        st.warning("No data available for scenario analysis")
        combined_df = pd.DataFrame()  # Continue with empty data
        
except Exception as e:
    st.error(f"Error loading data: {e}")
    combined_df = pd.DataFrame()
    fx_rates = {} 

# Handle any other errors
try:
    pass  # Main processing already handled above
except Exception as e:
    st.error(f"Error loading scenario data: {str(e)}")
    st.info("Please check that your data files are properly configured.")
