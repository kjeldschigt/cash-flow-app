import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.ui_helpers import (
    render_metric_grid,
    create_section_header,
    render_chart_container,
)
from src.utils.data_manager import (
    load_combined_data,
    init_session_filters,
    filter_data_by_range,
    get_daily_aggregates,
)
from src.utils.theme_manager import apply_theme
from src.services.error_handler import show_error
from src.services.fx_service import get_rate_scenarios, get_monthly_rate
from src.services.settings_service import get_setting
from src.ui.auth import AuthComponents

# Check authentication using new auth system
if not AuthComponents.require_authentication():
    st.stop()

# Apply theme
theme = get_setting("theme", "light")
st.markdown(apply_theme(theme), unsafe_allow_html=True)


def fetch_macro():
    """Stub function for future macro data API calls"""
    return {
        "us_consumer_confidence": 58.6,
        "economic_sentiment": 53.4,
        "last_updated": "Aug 2025",
    }


st.title("🧮 Scenario Planning & Projections")

try:
    # Initialize and load data
    init_session_filters()

    with st.spinner("Loading scenario data..."):
        df = load_combined_data()
        fx_rates = get_rate_scenarios()
        macro_data = fetch_macro()

        # Get base metrics
        if not df.empty and "Sales_USD" in df.columns:
            avg_monthly_sales = df["Sales_USD"].mean()
            avg_monthly_costs = (
                df["Costs_USD"].mean() if "Costs_USD" in df.columns else 0
            )
        else:
            avg_monthly_sales = 125000  # Default fallback
            avg_monthly_costs = 85000  # Default fallback

        # Get cost settings
        costa_usd_base = get_setting("costa_usd", 19000.0)
        costa_crc_base = get_setting("costa_crc", 38000000.0)
        hk_usd_base = get_setting("hk_usd", 40000.0)
        google_ads_base = get_setting("google_ads", 27500.0)
        stripe_fee_pct = get_setting("stripe_fee", 4.2)
        huub_principal = get_setting("huub_principal", 1250000.0)
        huub_interest = get_setting("huub_interest", 18750.0)

    # Sidebar Configuration
    with st.sidebar:
        st.header("Scenario Parameters")

        # Economic Environment
        st.subheader("Economic Environment")
        economy_scenario = st.selectbox(
            "Economic Scenario", ["Normal", "Recession", "Growth"], index=0
        )

        if economy_scenario == "Recession":
            economy_sales_impact = st.slider("Sales Impact (%)", -30.0, 0.0, -10.0)
            economy_ads_multiplier = st.slider("Ads Cost Multiplier", 1.0, 2.0, 1.5)
        elif economy_scenario == "Growth":
            economy_sales_impact = st.slider("Sales Impact (%)", 0.0, 30.0, 15.0)
            economy_ads_multiplier = st.slider("Ads Cost Multiplier", 0.5, 1.0, 0.8)
        else:
            economy_sales_impact = 0.0
            economy_ads_multiplier = (
                1.2 if macro_data["us_consumer_confidence"] < 60 else 1.0
            )

        # Projection Settings
        st.subheader("Projection Settings")
        growth_rate = st.slider("Annual Sales Growth Rate (%)", -20.0, 50.0, 5.0) / 100
        years = st.slider("Projection Period (Years)", 1, 10, 5)

        # FX Rate Configuration
        st.subheader("FX Rate Configuration")
        fx_years = {}
        for year in range(1, 6):
            fx_years[year] = st.number_input(
                f"CRC/USD Year {year}",
                value=502.0 + (year - 1) * 8.0,
                step=5.0,
                min_value=400.0,
                max_value=600.0,
                key=f"fx_year_{year}",
            )

        # Cost Multipliers
        st.subheader("Cost Multipliers")
        costa_usd_multiplier = st.slider("Costa Rica USD", 0.5, 2.0, 1.0, step=0.1)
        costa_crc_multiplier = st.slider("Costa Rica CRC", 0.5, 2.0, 1.0, step=0.1)
        hk_usd_multiplier = st.slider("Hong Kong USD", 0.5, 2.0, 1.0, step=0.1)
        google_ads_multiplier = st.slider(
            "Google Ads", 0.5, 3.0, economy_ads_multiplier, step=0.1
        )

        # Seasonality
        st.subheader("Seasonality")
        include_seasonality = st.checkbox("Apply Seasonality", value=True)
        if include_seasonality:
            months = [
                "Jan",
                "Feb",
                "Mar",
                "Apr",
                "May",
                "Jun",
                "Jul",
                "Aug",
                "Sep",
                "Oct",
                "Nov",
                "Dec",
            ]
            high_months = st.multiselect(
                "High Sales Months", options=months, default=["Dec", "Mar"]
            )
            low_months = st.multiselect(
                "Low Sales Months", options=months, default=["Feb", "Aug"]
            )
            seasonality_boost = st.slider("High Season Boost (%)", 10.0, 50.0, 20.0)
            seasonality_reduction = st.slider(
                "Low Season Reduction (%)", 5.0, 30.0, 15.0
            )

    # Base Metrics Overview
    create_section_header("Base Metrics", "Current performance baseline")

    base_metrics = [
        {
            "title": "Avg Monthly Sales",
            "value": f"${avg_monthly_sales:,.0f}",
            "caption": "Historical average",
        },
        {
            "title": "Avg Monthly Costs",
            "value": f"${avg_monthly_costs:,.0f}",
            "caption": "Historical average",
        },
        {
            "title": "Net Monthly",
            "value": f"${avg_monthly_sales - avg_monthly_costs:,.0f}",
            "caption": "Monthly profit",
        },
        {
            "title": "Consumer Confidence",
            "value": f"{macro_data['us_consumer_confidence']}",
            "caption": "Economic indicator",
        },
    ]

    render_metric_grid(base_metrics, columns=4)

    # Scenario Analysis
    st.subheader("Scenario Analysis")

    # Calculate adjusted costs
    adj_costa_usd = costa_usd_base * costa_usd_multiplier
    adj_costa_crc = costa_crc_base * costa_crc_multiplier
    adj_hk_usd = hk_usd_base * hk_usd_multiplier
    adj_google_ads = google_ads_base * google_ads_multiplier

    # Generate projections
    def get_seasonality_factor(month_name):
        if include_seasonality:
            if month_name in high_months:
                return 1 + (seasonality_boost / 100)
            elif month_name in low_months:
                return 1 - (seasonality_reduction / 100)
        return 1.0

    # Create projection data
    projection_data = []
    months = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]

    for year in range(1, years + 1):
        # Base annual projections with economy impact
        base_annual_sales = avg_monthly_sales * 12 * (1 + growth_rate) ** year
        economy_adjusted_sales = base_annual_sales * (1 + economy_sales_impact / 100)

        # Calculate costs with FX impact
        costa_usd_annual = adj_costa_usd * 12 * (1.02) ** year
        costa_crc_usd_annual = (adj_costa_crc * 12 * (1.02) ** year) / fx_years[year]
        hk_usd_annual = adj_hk_usd * 12 * (1.02) ** year
        google_ads_annual = (
            adj_google_ads * 12 * economy_ads_multiplier * (1.03) ** year
        )

        total_annual_costs = (
            costa_usd_annual + costa_crc_usd_annual + hk_usd_annual + google_ads_annual
        )
        annual_net = economy_adjusted_sales - total_annual_costs

        projection_data.append(
            {
                "Year": year,
                "Projected Sales": economy_adjusted_sales,
                "Projected Costs": total_annual_costs,
                "Net Cash Flow": annual_net,
                "FX Rate": fx_years[year],
            }
        )

    # Display projection results
    projection_metrics = []
    for proj in projection_data[:3]:  # Show first 3 years
        projection_metrics.append(
            {
                "title": f"Year {proj['Year']} Net",
                "value": f"${proj['Net Cash Flow']:,.0f}",
                "caption": f"Sales: ${proj['Projected Sales']:,.0f}",
            }
        )

    render_metric_grid(projection_metrics, columns=3)

    # Projection Chart
    def create_projection_chart():
        years_list = [p["Year"] for p in projection_data]
        sales_list = [p["Projected Sales"] for p in projection_data]
        costs_list = [p["Projected Costs"] for p in projection_data]
        net_list = [p["Net Cash Flow"] for p in projection_data]

        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=years_list,
                y=sales_list,
                mode="lines+markers",
                name="Sales",
                line=dict(color="#635BFF", width=3),
                marker=dict(size=8, color="#635BFF"),
            )
        )

        fig.add_trace(
            go.Scatter(
                x=years_list,
                y=costs_list,
                mode="lines+markers",
                name="Costs",
                line=dict(color="#FF6B6B", width=3),
                marker=dict(size=8, color="#FF6B6B"),
            )
        )

        fig.add_trace(
            go.Scatter(
                x=years_list,
                y=net_list,
                mode="lines+markers",
                name="Net Cash Flow",
                line=dict(color="#4ECDC4", width=3),
                marker=dict(size=8, color="#4ECDC4"),
            )
        )

        fig.update_layout(
            title="",
            xaxis=dict(title="Year", showgrid=False),
            yaxis=dict(title="Amount (USD)", showgrid=True, gridcolor="#f3f4f6"),
            plot_bgcolor="white",
            paper_bgcolor="white",
            height=400,
            margin=dict(l=0, r=0, t=20, b=0),
            showlegend=True,
        )
        return fig

    render_chart_container(
        create_projection_chart,
        "Financial Projections",
        f"{years}-year forecast with {economy_scenario.lower()} scenario",
        "Loading projections...",
    )

    # Scenario Comparison
    st.subheader("Scenario Comparison")

    scenarios = {
        "Conservative": {"growth": -0.05, "cost_change": 0.10},
        "Base Case": {"growth": growth_rate, "cost_change": 0.0},
        "Optimistic": {"growth": growth_rate + 0.10, "cost_change": -0.05},
    }

    scenario_results = []
    for scenario_name, params in scenarios.items():
        year_5_sales = avg_monthly_sales * 12 * (1 + params["growth"]) ** 5
        year_5_costs = avg_monthly_costs * 12 * (1 + params["cost_change"]) ** 5
        year_5_net = year_5_sales - year_5_costs

        scenario_results.append(
            {
                "title": scenario_name,
                "value": f"${year_5_net:,.0f}",
                "caption": f"Year 5 net cash flow",
            }
        )

    render_metric_grid(scenario_results, columns=3)

    # FX Impact Analysis
    st.subheader("FX Impact Analysis")

    fx_impact_data = []
    base_year_usd_cost = costa_crc_base / fx_years[1]

    for year in range(1, 6):
        usd_cost = costa_crc_base / fx_years[year]
        delta_vs_year1 = usd_cost - base_year_usd_cost

        fx_impact_data.append(
            {
                "Year": year,
                "FX Rate": fx_years[year],
                "USD Cost": f"${usd_cost:,.0f}",
                "Delta vs Year 1": f"${delta_vs_year1:+,.0f}",
            }
        )

    fx_df = pd.DataFrame(fx_impact_data)
    st.dataframe(fx_df, use_container_width=True)
    st.caption("CRC cost conversion impact over projection period")

except Exception as e:
    show_error(
        "Scenario Analysis Error",
        f"An error occurred while loading the scenario analysis: {str(e)}",
    )
    st.info("Please check your data connections and try again.")
