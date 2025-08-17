import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import numpy as np

def render_revenue_trends_chart(filtered_df, comparison_df=None, range_select=""):
    """Render revenue trends chart with gross vs net"""
    if 'Date' in filtered_df.columns and not filtered_df.empty:
        daily_data = filtered_df.groupby('Date').agg({
            'Sales_USD': 'sum',
            'Costs_USD': 'sum'
        }).reset_index()
        daily_data['Net'] = daily_data['Sales_USD'] - daily_data['Costs_USD']
        
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

def render_spend_per_transaction_chart(filtered_df, comparison_df=None, range_select=""):
    """Render spend per transaction chart"""
    if 'Date' in filtered_df.columns and len(filtered_df) > 0:
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

def render_performance_deltas_chart(sales_delta, cash_flow_delta, leads_delta, occupancy_delta, date_select):
    """Render performance deltas bar chart"""
    fig = go.Figure()

    fig.add_trace(go.Bar(
        name='Performance Deltas',
        x=['Sales', 'Cash Flow', 'Leads', 'Occupancy'],
        y=[sales_delta, cash_flow_delta, leads_delta, occupancy_delta],
        marker_color=['green' if x > 0 else 'red' for x in [sales_delta, cash_flow_delta, leads_delta, occupancy_delta]]
    ))

    fig.update_layout(
        title=f"Performance Deltas - {date_select}",
        yaxis_title="Change %",
        xaxis_title="Metrics",
        showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True)

def render_occupancy_analysis_charts(total_sales, total_costs, occupancy):
    """Render occupancy vs performance analysis charts"""
    st.subheader("Occupancy vs Performance Analysis")
    
    # Generate sample data points for different occupancy levels
    occupancy_levels = np.arange(50, 101, 5)  # 50% to 100% in 5% increments
    
    # Calculate theoretical sales based on occupancy (assuming linear relationship)
    base_sales_per_occupancy = total_sales / occupancy if occupancy > 0 else 0
    theoretical_sales = occupancy_levels * base_sales_per_occupancy
    
    # Calculate theoretical cash flow (assuming costs remain relatively fixed)
    base_costs = total_costs
    theoretical_cash_flow = theoretical_sales - base_costs
    
    # Create DataFrame for charts
    occupancy_analysis = pd.DataFrame({
        'Occupancy %': occupancy_levels,
        'Projected Sales': theoretical_sales,
        'Projected Cash Flow': theoretical_cash_flow
    })
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Occupancy vs Sales Projection**")
        chart_data = occupancy_analysis.set_index('Occupancy %')[['Projected Sales']]
        st.line_chart(chart_data)
        
        # Current position marker
        current_sales_at_occupancy = occupancy * base_sales_per_occupancy if occupancy > 0 else 0
        st.write(f"**Current Position:** {occupancy:.1f}% occupancy → ${current_sales_at_occupancy:,.0f} sales")
    
    with col2:
        st.write("**Occupancy vs Cash Flow Projection**")
        chart_data = occupancy_analysis.set_index('Occupancy %')[['Projected Cash Flow']]
        st.line_chart(chart_data)
        
        # Current position marker
        current_cash_flow_at_occupancy = current_sales_at_occupancy - base_costs
        st.write(f"**Current Position:** {occupancy:.1f}% occupancy → ${current_cash_flow_at_occupancy:,.0f} cash flow")

def render_5year_projections_chart(projection_data):
    """Render 5-year cash flow projections chart"""
    if not projection_data:
        return
        
    df_projections = pd.DataFrame(projection_data)
    
    # Create interactive chart for projections
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Monthly Cash Flow', 'Cumulative Cash Position'),
        vertical_spacing=0.1
    )
    
    # Monthly net cash flow
    fig.add_trace(
        go.Scatter(x=df_projections['Month'], y=df_projections['Net'], 
                  mode='lines', name='Monthly Net', line=dict(color='#00D4AA')),
        row=1, col=1
    )
    
    # Cumulative cash position
    fig.add_trace(
        go.Scatter(x=df_projections['Month'], y=df_projections['Cumulative_Cash'], 
                  mode='lines', name='Cumulative Cash', line=dict(color='#FF6B6B')),
        row=2, col=1
    )
    
    fig.update_layout(height=600, showlegend=True)
    fig.update_xaxes(title_text="Month", row=2, col=1)
    fig.update_yaxes(title_text="Amount ($)", row=1, col=1)
    fig.update_yaxes(title_text="Cumulative ($)", row=2, col=1)
    
    st.plotly_chart(fig, use_container_width=True)

def render_charts_section(filtered_df, comparison_df=None, range_select=""):
    """Render the main charts section with expandable charts"""
    st.subheader("📈 Visualizations")
    
    with st.expander("Revenue Trends Chart", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            render_revenue_trends_chart(filtered_df, comparison_df, range_select)
        
        with col2:
            render_spend_per_transaction_chart(filtered_df, comparison_df, range_select)
    
    with st.expander("Performance Analysis"):
        if not filtered_df.empty:
            total_sales = filtered_df['Sales_USD'].sum() if 'Sales_USD' in filtered_df.columns else 0
            total_costs = filtered_df['Costs_USD'].sum() if 'Costs_USD' in filtered_df.columns else 0
            occupancy = st.session_state.get('occupancy', 75.0)
            
            render_occupancy_analysis_charts(total_sales, total_costs, occupancy)

def render_simple_line_chart(data, title, x_col, y_col):
    """Render a simple line chart using st.line_chart"""
    if not data.empty and x_col in data.columns and y_col in data.columns:
        chart_data = data.set_index(x_col)[[y_col]]
        st.subheader(title)
        st.line_chart(chart_data)
    else:
        st.info(f"No data available for {title}")

def render_expandable_charts(filtered_df):
    """Render charts in expandable sections"""
    if filtered_df.empty:
        st.info("No data available for charts")
        return
    
    with st.expander("📊 Sales Trend", expanded=False):
        if 'Date' in filtered_df.columns and 'Sales_USD' in filtered_df.columns:
            daily_sales = filtered_df.groupby('Date')['Sales_USD'].sum().reset_index()
            render_simple_line_chart(daily_sales, "Daily Sales", 'Date', 'Sales_USD')
    
    with st.expander("💰 Cash Flow Trend", expanded=False):
        if 'Date' in filtered_df.columns and 'Sales_USD' in filtered_df.columns and 'Costs_USD' in filtered_df.columns:
            daily_data = filtered_df.groupby('Date').agg({
                'Sales_USD': 'sum',
                'Costs_USD': 'sum'
            }).reset_index()
            daily_data['Net_Cash_Flow'] = daily_data['Sales_USD'] - daily_data['Costs_USD']
            render_simple_line_chart(daily_data, "Daily Net Cash Flow", 'Date', 'Net_Cash_Flow')
    
    with st.expander("📈 Costs Analysis", expanded=False):
        if 'Date' in filtered_df.columns and 'Costs_USD' in filtered_df.columns:
            daily_costs = filtered_df.groupby('Date')['Costs_USD'].sum().reset_index()
            render_simple_line_chart(daily_costs, "Daily Costs", 'Date', 'Costs_USD')
