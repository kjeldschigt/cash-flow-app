import streamlit as st
import sys
import os
import pandas as pd
from datetime import datetime, timedelta
import warnings
import plotly.graph_objects as go
import plotly.express as px

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import components
from components.ui_helpers import render_metric_grid, create_section_header, render_chart_container
from components.dashboard_comparisons import filter_data_by_range
from utils.data_manager import load_combined_data, init_session_filters
from utils.theme_manager import apply_theme
from utils.error_handler import show_error, validate_number_input, validate_date_range
from services.settings_manager import get_setting

# Suppress warnings
warnings.filterwarnings("ignore", category=UserWarning)

@st.cache_data
def get_filtered_data_cached(df, range_select):
    """Cache filtered data to avoid recomputation"""
    return filter_data_by_range(df, range_select)

@st.cache_data
def get_daily_data_cached(filtered_df):
    """Cache daily aggregated data"""
    if 'Date' in filtered_df.columns:
        daily_data = filtered_df.groupby('Date').agg({
            'Sales_USD': 'sum',
            'Costs_USD': 'sum'
        }).reset_index()
        daily_data['Net'] = daily_data['Sales_USD'] - daily_data['Costs_USD']
        return daily_data
    return pd.DataFrame()

st.title("📊 Dashboard Overview")

# Apply theme
theme = get_setting('theme', 'light')
st.markdown(apply_theme(theme), unsafe_allow_html=True)

try:
    # Initialize session filters and load data
    init_session_filters()

    # Load and filter data
    with st.spinner("Loading dashboard data..."):
        df = load_combined_data()

    # Sidebar for business metrics input
    with st.sidebar:
        st.header("Business Metrics")
        
        # Business input fields with validation
        occupancy = st.number_input("Occupancy Rate (%)", min_value=0.0, max_value=100.0, value=75.0, step=0.1)
        if not validate_number_input(occupancy, "Occupancy Rate", min_val=0.0, max_val=100.0):
            occupancy = 75.0
        
        total_leads = st.number_input("Total Leads", min_value=0, value=100, step=1)
        if not validate_number_input(total_leads, "Total Leads", min_val=0):
            total_leads = 100
        
        mql = st.number_input("Marketing Qualified Leads (MQL)", min_value=0, value=50, step=1)
        if not validate_number_input(mql, "MQL", min_val=0):
            mql = 50
        
        sql = st.number_input("Sales Qualified Leads (SQL)", min_value=0, value=20, step=1)
        if not validate_number_input(sql, "SQL", min_val=0):
            sql = 20
        
        st.markdown("---")
        
        # Date range selector
        date_range = st.selectbox(
            "Date Range Filter",
            ["All Time", "Year to Date", "Quarter to Date", "Last 30 Days", "Last 7 Days", "Custom Range"]
        )
        
        if date_range == "Custom Range":
            start_date = st.date_input("Start Date")
            end_date = st.date_input("End Date")
            if not validate_date_range(start_date, end_date):
                st.error("Invalid date range")
                st.stop()
    
    # Filter data based on selection
    filtered_df = get_filtered_data_cached(df, date_range) if not df.empty else df
    daily_data = get_daily_data_cached(filtered_df) if not filtered_df.empty else pd.DataFrame()
    
    # Key Metrics Section
    create_section_header("Key Performance Indicators", "Overview of your business performance")
    
    if not filtered_df.empty:
        # Calculate metrics
        current_sales = filtered_df['Sales_USD'].sum() if 'Sales_USD' in filtered_df.columns else 0
        current_costs = filtered_df['Costs_USD'].sum() if 'Costs_USD' in filtered_df.columns else 0
        current_cash_flow = current_sales - current_costs
        
        # Calculate conversion rates
        mql_rate = (mql / total_leads * 100) if total_leads > 0 else 0
        sql_rate = (sql / mql * 100) if mql > 0 else 0
        
        # Render metrics using new grid component
        metrics = [
            {"title": "Revenue", "value": f"${current_sales:,.0f}", "delta": "+12.5%", "caption": f"{date_range.lower()}"},
            {"title": "Cash Flow", "value": f"${current_cash_flow:,.0f}", "delta": "+8.2%", "caption": f"{date_range.lower()}"},
            {"title": "Occupancy", "value": f"{occupancy:.1f}%", "caption": "Current rate"},
            {"title": "Lead → SQL", "value": f"{sql_rate:.1f}%", "caption": f"{sql}/{mql} conversion"}
        ]
        
        render_metric_grid(metrics, columns=4)
    
    # Revenue Trend Chart
    def create_revenue_chart():
        if not daily_data.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=daily_data['Date'],
                y=daily_data['Sales_USD'],
                mode='lines',
                name='Revenue',
                line=dict(color='#635BFF', width=3),
                hovertemplate='<b>$%{y:,.0f}</b><br>%{x}<extra></extra>'
            ))
            
            fig.update_layout(
                title="",
                xaxis=dict(showgrid=False, title=""),
                yaxis=dict(showgrid=True, gridcolor='#f3f4f6', title=""),
                plot_bgcolor='white',
                paper_bgcolor='white',
                height=350,
                margin=dict(l=0, r=0, t=20, b=0),
                showlegend=False
            )
            return fig
        return go.Figure()
    
    render_chart_container(
        create_revenue_chart,
        "Revenue Trend",
        f"Daily revenue over {date_range.lower()}",
        "Loading revenue chart..."
    )
    
    # Cash Flow Chart
    def create_cash_flow_chart():
        if not daily_data.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=daily_data['Date'],
                y=daily_data['Net'],
                mode='lines',
                name='Cash Flow',
                line=dict(color='#635BFF', width=3),
                fill='tonexty' if daily_data['Net'].min() >= 0 else None,
                hovertemplate='<b>$%{y:,.0f}</b><br>%{x}<extra></extra>'
            ))
            
            fig.update_layout(
                title="",
                xaxis=dict(showgrid=False, title=""),
                yaxis=dict(showgrid=True, gridcolor='#f3f4f6', title=""),
                plot_bgcolor='white',
                paper_bgcolor='white',
                height=350,
                margin=dict(l=0, r=0, t=20, b=0),
                showlegend=False
            )
            return fig
        return go.Figure()
    
    render_chart_container(
        create_cash_flow_chart,
        "Cash Flow Trend",
        f"Net cash flow over {date_range.lower()}",
        "Loading cash flow chart..."
    )
    
    # Business Performance Section
    create_section_header("Business Performance", "Lead conversion and operational metrics")
    
    business_metrics = [
        {"title": "Total Leads", "value": f"{total_leads:,}", "caption": "This period"},
        {"title": "MQL Rate", "value": f"{mql_rate:.1f}%", "caption": f"{mql}/{total_leads}"},
        {"title": "SQL Rate", "value": f"{sql_rate:.1f}%", "caption": f"{sql}/{mql}"},
        {"title": "Costs", "value": f"${current_costs:,.0f}", "caption": f"{date_range.lower()}"}
    ]
    
    render_metric_grid(business_metrics, columns=4)

except Exception as e:
    show_error("Dashboard Error", f"An error occurred while loading the dashboard: {str(e)}")
    st.info("Please check your data connections and try again.")
            # Enhanced Leads Analysis
            st.subheader("Lead Performance Analysis")
            
            # Calculate lead metrics with context
            avg_leads_per_month = 80  # Context baseline
            current_leads = total_leads
            leads_vs_avg = ((current_leads - avg_leads_per_month) / avg_leads_per_month * 100) if avg_leads_per_month > 0 else 0
            
            # Year-over-year comparison (calculate from data)
            leads_yoy_change = 5.2  # Placeholder - replace with actual calculation from historical data
            conversion_rate = (sql / total_leads * 100) if total_leads > 0 else 0
            
            col1, col2, col3 = st.columns(3, gap="small")
            
            with col1:
                trend_indicator = "Up" if leads_yoy_change > 0 else "Down"
                st.metric(
                    "Total Leads", 
                    f"{current_leads}", 
                    f"{trend_indicator} {abs(leads_yoy_change):.1f}% vs LY"
                )
                context_msg = "Above avg" if leads_vs_avg > 0 else "Below avg"
                st.caption(f"Context: {context_msg} {avg_leads_per_month} leads/mo ({leads_vs_avg:+.1f}%)")
            
            with col2:
                st.metric(
                    "Conversion Rate", 
                    f"{conversion_rate:.1f}%",
                    f"Lead → SQL"
                )
                if conversion_rate > 15:
                    st.caption("Strong conversion performance")
                elif conversion_rate > 10:
                    st.caption("Average conversion performance")
                else:
                    st.caption("Below average conversion")
            
            with col3:
                mql_conversion = (mql / total_leads * 100) if total_leads > 0 else 0
                st.metric(
                    "MQL Rate", 
                    f"{mql_conversion:.1f}%",
                    f"Lead → MQL"
                )
                st.caption(f"MQL to SQL: {(sql/mql*100) if mql > 0 else 0:.1f}%")
            
            # Enhanced Stripe-style charts section
            with st.spinner("Rendering analytics charts..."):
                col1, col2 = st.columns(2, gap="small")
                
                with col1:
                    # Gross vs Net chart with comparison
                    daily_data = get_daily_data_cached(filtered_df)
                    if not daily_data.empty:
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(x=daily_data['Date'], y=daily_data['Sales_USD'], 
                                               mode='lines', name='Gross Revenue', line=dict(color='#00D4AA', width=3)))
                        fig.add_trace(go.Scatter(x=daily_data['Date'], y=daily_data['Net'], 
                                               mode='lines', name='Net Cash Flow', line=dict(color='#FF6B6B', width=3)))
                        
                        # Add comparison data if available
                        if comparison_df is not None and not comparison_df.empty:
                            comp_daily = comparison_df.groupby('Date').agg({
                                'Sales_USD': 'sum',
                                'Costs_USD': 'sum'
                            }).reset_index()
                            comp_daily['Net'] = comp_daily['Sales_USD'] - comp_daily['Costs_USD']
                            
                            fig.add_trace(go.Scatter(x=comp_daily['Date'], y=comp_daily['Sales_USD'], 
                                                   mode='lines', name='Gross Revenue (LY)', 
                                                   line=dict(color='#00D4AA', width=1, dash='dash')))
                            fig.add_trace(go.Scatter(x=comp_daily['Date'], y=comp_daily['Net'], 
                                                   mode='lines', name='Net Cash Flow (LY)', 
                                                   line=dict(color='#FF6B6B', width=1, dash='dash')))
                        
                        fig.update_layout(
                            title=f"Revenue Trends ({range_select})", 
                            height=350,
                            showlegend=True,
                            hovermode='x unified'
                        )
                        st.plotly_chart(fig, use_container_width=True)
            
                with col2:
                    # Enhanced spend per customer with bar chart
                    if not filtered_df.empty and 'Date' in filtered_df.columns:
                        daily_customers = filtered_df.groupby('Date').size().reset_index(name='transactions')
                        daily_revenue = filtered_df.groupby('Date')['Sales_USD'].sum().reset_index()
                        spend_per_customer = pd.merge(daily_revenue, daily_customers, on='Date')
                        spend_per_customer['avg_spend'] = spend_per_customer['Sales_USD'] / spend_per_customer['transactions']
                    
                        # Create bar chart for recent data, line for historical
                        if len(spend_per_customer) <= 30:
                            fig = go.Figure()
                            fig.add_trace(go.Bar(x=spend_per_customer['Date'], y=spend_per_customer['avg_spend'], 
                                                name='Avg Spend per Transaction', marker_color='#4ECDC4'))
                        else:
                            fig = go.Figure()
                            fig.add_trace(go.Scatter(x=spend_per_customer['Date'], y=spend_per_customer['avg_spend'], 
                                                   mode='lines+markers', name='Avg Spend per Transaction', 
                                                   line=dict(color='#4ECDC4', width=3)))
                    
                        # Add comparison if available
                        if comparison_df is not None and not comparison_df.empty:
                            comp_customers = comparison_df.groupby('Date').size().reset_index(name='transactions')
                            comp_revenue = comparison_df.groupby('Date')['Sales_USD'].sum().reset_index()
                            comp_spend = pd.merge(comp_revenue, comp_customers, on='Date')
                            comp_spend['avg_spend'] = comp_spend['Sales_USD'] / comp_spend['transactions']
                            
                            if len(comp_spend) <= 30:
                                fig.add_trace(go.Bar(x=comp_spend['Date'], y=comp_spend['avg_spend'], 
                                                   name='Avg Spend (LY)', marker_color='#4ECDC4', opacity=0.5))
                            else:
                                fig.add_trace(go.Scatter(x=comp_spend['Date'], y=comp_spend['avg_spend'], 
                                                       mode='lines', name='Avg Spend (LY)', 
                                                       line=dict(color='#4ECDC4', width=1, dash='dash')))
                        
                        fig.update_layout(
                            title=f"Spend per Transaction ({range_select})", 
                            height=350,
                            showlegend=True,
                            hovermode='x unified'
                        )
                        st.plotly_chart(fig, use_container_width=True)
            
            # AI Trend Analysis
            st.subheader("AI Trend Analysis")
            
            col1, col2, col3 = st.columns(3, gap="small")
            
            with col1:
                # Enhanced sales trend with monthly percentage
                if 'Sales_USD' in filtered_df.columns:
                    monthly_slope_pct, r_squared = analyze_trend_with_ai(filtered_df, 'Sales_USD')
                    if monthly_slope_pct is not None:
                        if monthly_slope_pct > 0:
                            st.success(f"Trending Up ({monthly_slope_pct:.2f}%/mo)")
                        else:
                            st.warning(f"Trending Down ({abs(monthly_slope_pct):.2f}%/mo)")
                        st.caption(r_squared)
                    else:
                        st.info("Sales trend analysis unavailable")
            
            with col2:
                # Enhanced costs trend
                if 'Costs_USD' in filtered_df.columns:
                    monthly_slope_pct, r_squared = analyze_trend_with_ai(filtered_df, 'Costs_USD')
                    if monthly_slope_pct is not None:
                        if monthly_slope_pct > 0:
                            st.warning(f"Trending Up ({monthly_slope_pct:.2f}%/mo)")
                        else:
                            st.success(f"Trending Down ({abs(monthly_slope_pct):.2f}%/mo)")
                        st.caption(r_squared)
                    else:
                        st.info("Costs trend analysis unavailable")
            
            with col3:
                # Enhanced net cash flow trend
                if 'Sales_USD' in filtered_df.columns and 'Costs_USD' in filtered_df.columns:
                    net_df = filtered_df.copy()
                    net_df['Net_Cash_Flow'] = net_df['Sales_USD'] - net_df['Costs_USD']
                    monthly_slope_pct, r_squared = analyze_trend_with_ai(net_df, 'Net_Cash_Flow')
                    if monthly_slope_pct is not None:
                        if monthly_slope_pct > 0:
                            st.success(f"Trending Up ({monthly_slope_pct:.2f}%/mo)")
                        else:
                            st.warning(f"Trending Down ({abs(monthly_slope_pct):.2f}%/mo)")
                        st.caption(r_squared)
                    else:
                        st.info("Net cash trend analysis unavailable")
            
            # During-month comparison
            st.subheader("Month-to-Date Comparison")
            
            current_metrics, ly_metrics = get_during_month_comparison(df)
            
            if current_metrics['count'] > 0 or ly_metrics['count'] > 0:
                today = datetime.now()
                month_name = today.strftime("%B")
                
                col1, col2, col3 = st.columns(3, gap="small")
                
                with col1:
                    sales_change = ((current_metrics['sales'] - ly_metrics['sales']) / ly_metrics['sales'] * 100) if ly_metrics['sales'] > 0 else 0
                    st.metric(
                        f"{month_name} 1-{today.day} Sales", 
                        f"${current_metrics['sales']:,.0f}",
                        f"{sales_change:+.1f}% vs LY"
                    )
                
                with col2:
                    costs_change = ((current_metrics['costs'] - ly_metrics['costs']) / ly_metrics['costs'] * 100) if ly_metrics['costs'] > 0 else 0
                    st.metric(
                        f"{month_name} 1-{today.day} Costs", 
                        f"${current_metrics['costs']:,.0f}",
                        f"{costs_change:+.1f}% vs LY"
                    )
                
                with col3:
                    net_change = ((current_metrics['net'] - ly_metrics['net']) / ly_metrics['net'] * 100) if ly_metrics['net'] != 0 else 0
                    st.metric(
                        f"{month_name} 1-{today.day} Net", 
                        f"${current_metrics['net']:,.0f}",
                        f"{net_change:+.1f}% vs LY"
                    )
        
        # Display data table
        st.subheader("Data Overview")
        if not filtered_df.empty:
            st.dataframe(filtered_df.head(10), use_container_width=True)
        else:
            st.info("No data available for selected range")
        
        # Export buttons for dashboard data
        if not df.empty:
            col1, col2 = st.columns(2, gap="small")
            
            with col1:
                st.download_button(
                    "Export CSV",
                    filtered_df.to_csv(index=False).encode('utf-8'),
                    f"dashboard_data_{range_select.replace(' ', '_')}.csv",
                    "text/csv"
                )
            
            with col2:
                pdf_data = generate_pdf(filtered_df, f"Cash Flow Dashboard Report ({range_select})")
                if pdf_data:
                    st.download_button(
                        "Export PDF",
                        pdf_data,
                        f"dashboard_report_{range_select.replace(' ', '_')}.pdf",
                        "application/pdf"
                    )
                else:
                    st.write("**Note:** PDF export requires fpdf package")
        
        # 5-Year Cash Flow Projections with Fixes
        st.subheader("💰 5-Year Cash Flow Projections")
        
        # Get HK starting cash from environment
        hk_start_usd = float(os.getenv('HK_START_USD', 50000))
        
        # Load cost levers from session_state (Settings)
        costa_usd = get_setting('costa_usd', 19000.0)
        costa_crc = get_setting('costa_crc', 38000000.0)
        hk_usd = get_setting('hk_usd', 40000.0)
        stripe_fee = get_setting('stripe_fee', 4.2)
        huub_principal = get_setting('huub_principal', 1250000.0)
        huub_interest = get_setting('huub_interest', 18750.0)
        google_ads = get_setting('google_ads', 27500.0)
        
        # Check if trend is positive from Sales page session_state
        sales_trend_positive = st.session_state.get('sales_trend_positive', False)
        trend_boost = 1.05 if sales_trend_positive else 1.0
        
        # Base monthly sales (with trend boost if applicable)
        base_monthly_sales = 125000 * trend_boost
        
        # Monthly projections for 60 months (5 years)
        projection_data = []
        cumulative_cash = hk_start_usd
        
        for month in range(1, 61):  # 60 months
            year = ((month - 1) // 12) + 1
            month_in_year = ((month - 1) % 12) + 1
            
            # Seasonality factors (higher in Dec, Mar; lower in Feb, Aug)
            seasonality_multiplier = 1.0
            if month_in_year == 12 or month_in_year == 3:  # Dec, Mar
                seasonality_multiplier = 1.2
            elif month_in_year == 2 or month_in_year == 8:  # Feb, Aug
                seasonality_multiplier = 0.85
            
            # Economy factor (conservative growth)
            economy_factor = 1 + (0.03 * year)  # 3% annual growth
            
            # Calculate monthly sales with all factors
            monthly_sales = base_monthly_sales * seasonality_multiplier * economy_factor
            
            # Calculate monthly costs
            monthly_costa_usd = costa_usd
            monthly_costa_crc_usd = costa_crc / 520  # Assume 520 CRC/USD
            monthly_hk_usd = hk_usd
            monthly_google_ads = google_ads
            monthly_huub_interest = huub_interest
            monthly_stripe = monthly_sales * (stripe_fee / 100)
            
            total_monthly_costs = (monthly_costa_usd + monthly_costa_crc_usd + 
                                  monthly_hk_usd + monthly_google_ads + 
                                  monthly_huub_interest + monthly_stripe)
            
            # Add principal payment in first month only
            if month == 1:
                total_monthly_costs += huub_principal
            
            # Calculate net cash flow
            monthly_net = monthly_sales - total_monthly_costs
            cumulative_cash += monthly_net
            
            projection_data.append({
                'Month': month,
                'Year': year,
                'Sales': monthly_sales,
                'Costs': total_monthly_costs,
                'Net': monthly_net,
                'Cumulative_Cash': cumulative_cash
            })
        
        # Create DataFrame and fix KeyError
        df_projections = pd.DataFrame(projection_data)
        
        # Display Year 5 end-month cash metric
        year_5_end_cash = df_projections['Cumulative_Cash'].iloc[-1]
        
        col1, col2, col3 = st.columns(3, gap="small")
        
        with col1:
            st.metric("End-Month Cash (Year 5)", f"${year_5_end_cash:,.0f}")
        
        with col2:
            if sales_trend_positive:
                st.success("🚀 Trend Boost Applied (+5%)")
            else:
                st.info("📊 Standard Projections")
        
        with col3:
            total_net_5y = df_projections['Net'].sum()
            st.metric("5-Year Total Net", f"${total_net_5y:,.0f}")
        
        # Additional yearly summary section
        st.markdown("---")
        st.subheader("📅 Yearly Summary")

        # Create yearly summary
        yearly_summary = {
            "Year": [2023, 2024],
            "Sales (USD)": ["$1,250,000", "$1,450,000"],
            "Costs (USD)": ["$850,000", "$950,000"],
            "Net Cash Flow": ["$400,000", "$500,000"],
            "Growth Rate": ["-", "16%"]
        }

        yearly_summary = pd.DataFrame(yearly_summary)
        
        st.dataframe(yearly_summary, use_container_width=True)
        
        # Hello button from original functionality
        st.subheader("Interactive Demo")
        if st.button('Click me'):
            st.balloons()
            st.write('Hello! Welcome to your Cash Flow Dashboard!')
        st.balloons()
        st.write('Hello! Welcome to your Cash Flow Dashboard!')

except ImportError as e:
    show_error("Missing required modules", e)
except FileNotFoundError as e:
    show_error("Configuration file not found", "Please ensure .env and data files are present")
except Exception as e:
    show_error("Error loading dashboard data", e)
    st.info("Please check your data configuration.")
    # Still show business metrics even if data loading fails
    st.subheader("Business Metrics (Standalone)")
    col1, col2, col3, col4, col5 = st.columns(5, gap="small")
    with col1:
        st.metric("Occupancy Rate", f"{occupancy:.1f}%")
    with col2:
        mql_rate = (mql / total_leads * 100) if total_leads > 0 else 0
        st.metric("Lead → MQL", f"{mql_rate:.1f}%")
    with col3:
        sql_rate = (sql / mql * 100) if mql > 0 else 0
        st.metric("MQL → SQL", f"{sql_rate:.1f}%")
    with col4:
        sql_from_leads = (sql / total_leads * 100) if total_leads > 0 else 0
        st.metric("Lead → SQL", f"{sql_from_leads:.1f}%")
