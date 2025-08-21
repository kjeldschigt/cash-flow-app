"""
Interactive Chart Components for Cash Flow Dashboard
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
import numpy as np


class BaseChart:
    """Base chart component with common functionality"""

    @staticmethod
    def _apply_theme(fig: go.Figure, title: str = None) -> go.Figure:
        """Apply consistent theme to charts"""
        fig.update_layout(
            title=title,
            title_font_size=16,
            title_font_color="#1f1f1f",
            font=dict(family="Arial, sans-serif", size=12, color="#1f1f1f"),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=20, r=20, t=40, b=20),
            height=400,
            showlegend=True,
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
            ),
        )

        fig.update_xaxes(
            showgrid=True,
            gridwidth=1,
            gridcolor="rgba(128,128,128,0.2)",
            showline=True,
            linewidth=1,
            linecolor="rgba(128,128,128,0.3)",
        )

        fig.update_yaxes(
            showgrid=True,
            gridwidth=1,
            gridcolor="rgba(128,128,128,0.2)",
            showline=True,
            linewidth=1,
            linecolor="rgba(128,128,128,0.3)",
        )

        return fig

    @staticmethod
    def _add_export_buttons(fig: go.Figure, filename: str = "chart"):
        """Add export functionality to charts"""
        col1, col2, col3 = st.columns([1, 1, 1])

        with col1:
            if st.button("📊 Export PNG", key=f"png_{filename}"):
                fig.write_image(f"{filename}.png", width=1200, height=600)
                st.success("Chart exported as PNG!")

        with col2:
            if st.button("📈 Export HTML", key=f"html_{filename}"):
                fig.write_html(f"{filename}.html")
                st.success("Chart exported as HTML!")

        with col3:
            if st.button("📋 Export Data", key=f"data_{filename}"):
                # This would need the underlying data to be passed
                st.info("Data export functionality - implement with chart data")


class CashFlowChart:
    """Interactive cash flow chart with tooltips and zoom"""

    @staticmethod
    def render(
        data: pd.DataFrame,
        date_column: str = "date",
        inflow_column: str = "inflow",
        outflow_column: str = "outflow",
        title: str = "Cash Flow Analysis",
        show_net_flow: bool = True,
        show_cumulative: bool = False,
        export_filename: str = "cash_flow",
    ):
        """
        Render interactive cash flow chart

        Args:
            data: DataFrame with cash flow data
            date_column: Name of date column
            inflow_column: Name of cash inflow column
            outflow_column: Name of cash outflow column
            title: Chart title
            show_net_flow: Show net cash flow line
            show_cumulative: Show cumulative cash flow
            export_filename: Filename for exports
        """
        if data.empty:
            st.warning("No cash flow data available")
            return

        # Ensure date column is datetime
        data[date_column] = pd.to_datetime(data[date_column])
        data = data.sort_values(date_column)

        # Calculate net flow
        data["net_flow"] = data[inflow_column] - data[outflow_column]

        # Calculate cumulative flow if requested
        if show_cumulative:
            data["cumulative_flow"] = data["net_flow"].cumsum()

        fig = go.Figure()

        # Add cash inflow
        fig.add_trace(
            go.Scatter(
                x=data[date_column],
                y=data[inflow_column],
                mode="lines+markers",
                name="Cash Inflow",
                line=dict(color="#2E8B57", width=3),
                marker=dict(size=6),
                hovertemplate="<b>Cash Inflow</b><br>"
                + "Date: %{x}<br>"
                + "Amount: $%{y:,.2f}<extra></extra>",
            )
        )

        # Add cash outflow
        fig.add_trace(
            go.Scatter(
                x=data[date_column],
                y=data[outflow_column],
                mode="lines+markers",
                name="Cash Outflow",
                line=dict(color="#DC143C", width=3),
                marker=dict(size=6),
                hovertemplate="<b>Cash Outflow</b><br>"
                + "Date: %{x}<br>"
                + "Amount: $%{y:,.2f}<extra></extra>",
            )
        )

        # Add net flow if requested
        if show_net_flow:
            colors = ["#2E8B57" if x >= 0 else "#DC143C" for x in data["net_flow"]]
            fig.add_trace(
                go.Scatter(
                    x=data[date_column],
                    y=data["net_flow"],
                    mode="lines+markers",
                    name="Net Cash Flow",
                    line=dict(color="#4169E1", width=2, dash="dash"),
                    marker=dict(size=4),
                    hovertemplate="<b>Net Cash Flow</b><br>"
                    + "Date: %{x}<br>"
                    + "Amount: $%{y:,.2f}<extra></extra>",
                )
            )

        # Add cumulative flow if requested
        if show_cumulative:
            fig.add_trace(
                go.Scatter(
                    x=data[date_column],
                    y=data["cumulative_flow"],
                    mode="lines",
                    name="Cumulative Flow",
                    line=dict(color="#9370DB", width=2),
                    yaxis="y2",
                    hovertemplate="<b>Cumulative Flow</b><br>"
                    + "Date: %{x}<br>"
                    + "Amount: $%{y:,.2f}<extra></extra>",
                )
            )

            # Add secondary y-axis for cumulative
            fig.update_layout(
                yaxis2=dict(title="Cumulative Flow ($)", overlaying="y", side="right")
            )

        # Apply theme and layout
        fig = BaseChart._apply_theme(fig, title)
        fig.update_layout(
            xaxis_title="Date", yaxis_title="Cash Flow ($)", hovermode="x unified"
        )

        # Display chart
        st.plotly_chart(fig, use_container_width=True)

        # Add export buttons
        BaseChart._add_export_buttons(fig, export_filename)


class RevenueBreakdownPieChart:
    """Revenue breakdown pie chart with drill-down capability"""

    @staticmethod
    def render(
        data: Dict[str, float],
        title: str = "Revenue Breakdown",
        show_percentages: bool = True,
        export_filename: str = "revenue_breakdown",
    ):
        """
        Render revenue breakdown pie chart

        Args:
            data: Dictionary with category names and values
            title: Chart title
            show_percentages: Show percentages in labels
            export_filename: Filename for exports
        """
        if not data:
            st.warning("No revenue data available")
            return

        categories = list(data.keys())
        values = list(data.values())
        total = sum(values)

        # Calculate percentages
        percentages = [v / total * 100 for v in values]

        # Create color palette
        colors = px.colors.qualitative.Set3[: len(categories)]

        fig = go.Figure(
            data=[
                go.Pie(
                    labels=categories,
                    values=values,
                    hole=0.4,  # Donut chart
                    marker=dict(colors=colors, line=dict(color="#FFFFFF", width=2)),
                    textinfo="label+percent" if show_percentages else "label+value",
                    textposition="auto",
                    hovertemplate="<b>%{label}</b><br>"
                    + "Amount: $%{value:,.2f}<br>"
                    + "Percentage: %{percent}<extra></extra>",
                )
            ]
        )

        # Add center text for donut
        fig.add_annotation(
            text=f"Total<br>${total:,.0f}", x=0.5, y=0.5, font_size=16, showarrow=False
        )

        # Apply theme
        fig = BaseChart._apply_theme(fig, title)
        fig.update_layout(height=500)

        # Display chart
        st.plotly_chart(fig, use_container_width=True)

        # Show breakdown table
        with st.expander("📊 Detailed Breakdown"):
            breakdown_df = pd.DataFrame(
                {
                    "Category": categories,
                    "Amount": [f"${v:,.2f}" for v in values],
                    "Percentage": [f"{p:.1f}%" for p in percentages],
                }
            )
            st.dataframe(breakdown_df, use_container_width=True)

        # Add export buttons
        BaseChart._add_export_buttons(fig, export_filename)


class ForecastLineChart:
    """Forecast line chart with confidence bands"""

    @staticmethod
    def render(
        historical_data: pd.DataFrame,
        forecast_data: pd.DataFrame,
        date_column: str = "date",
        value_column: str = "value",
        confidence_lower: str = "lower_bound",
        confidence_upper: str = "upper_bound",
        title: str = "Financial Forecast",
        metric_name: str = "Value",
        export_filename: str = "forecast",
    ):
        """
        Render forecast chart with confidence bands

        Args:
            historical_data: Historical data DataFrame
            forecast_data: Forecast data DataFrame with confidence intervals
            date_column: Name of date column
            value_column: Name of value column
            confidence_lower: Lower confidence bound column
            confidence_upper: Upper confidence bound column
            title: Chart title
            metric_name: Name of the metric being forecasted
            export_filename: Filename for exports
        """
        fig = go.Figure()

        # Add historical data
        if not historical_data.empty:
            fig.add_trace(
                go.Scatter(
                    x=historical_data[date_column],
                    y=historical_data[value_column],
                    mode="lines+markers",
                    name="Historical Data",
                    line=dict(color="#2E8B57", width=3),
                    marker=dict(size=6),
                    hovertemplate=f"<b>Historical {metric_name}</b><br>"
                    + "Date: %{x}<br>"
                    + "Value: $%{y:,.2f}<extra></extra>",
                )
            )

        # Add forecast line
        if not forecast_data.empty:
            fig.add_trace(
                go.Scatter(
                    x=forecast_data[date_column],
                    y=forecast_data[value_column],
                    mode="lines+markers",
                    name="Forecast",
                    line=dict(color="#4169E1", width=3, dash="dash"),
                    marker=dict(size=6),
                    hovertemplate=f"<b>Forecast {metric_name}</b><br>"
                    + "Date: %{x}<br>"
                    + "Value: $%{y:,.2f}<extra></extra>",
                )
            )

            # Add confidence bands if available
            if (
                confidence_lower in forecast_data.columns
                and confidence_upper in forecast_data.columns
            ):
                # Upper bound
                fig.add_trace(
                    go.Scatter(
                        x=forecast_data[date_column],
                        y=forecast_data[confidence_upper],
                        mode="lines",
                        line=dict(width=0),
                        showlegend=False,
                        hoverinfo="skip",
                    )
                )

                # Lower bound with fill
                fig.add_trace(
                    go.Scatter(
                        x=forecast_data[date_column],
                        y=forecast_data[confidence_lower],
                        mode="lines",
                        line=dict(width=0),
                        name="Confidence Interval",
                        fill="tonexty",
                        fillcolor="rgba(65, 105, 225, 0.2)",
                        hovertemplate="<b>Confidence Interval</b><br>"
                        + "Date: %{x}<br>"
                        + "Lower: $%{y:,.2f}<extra></extra>",
                    )
                )

        # Apply theme
        fig = BaseChart._apply_theme(fig, title)
        fig.update_layout(
            xaxis_title="Date", yaxis_title=f"{metric_name} ($)", hovermode="x unified"
        )

        # Display chart
        st.plotly_chart(fig, use_container_width=True)

        # Add forecast summary
        if not forecast_data.empty:
            with st.expander("📈 Forecast Summary"):
                col1, col2, col3 = st.columns(3)

                with col1:
                    avg_forecast = forecast_data[value_column].mean()
                    st.metric("Average Forecast", f"${avg_forecast:,.2f}")

                with col2:
                    if len(forecast_data) > 1:
                        growth_rate = (
                            (
                                forecast_data[value_column].iloc[-1]
                                / forecast_data[value_column].iloc[0]
                            )
                            - 1
                        ) * 100
                        st.metric("Growth Rate", f"{growth_rate:.1f}%")

                with col3:
                    forecast_range = (
                        forecast_data[value_column].max()
                        - forecast_data[value_column].min()
                    )
                    st.metric("Forecast Range", f"${forecast_range:,.2f}")

        # Add export buttons
        BaseChart._add_export_buttons(fig, export_filename)


class ScenarioComparisonChart:
    """Scenario comparison chart for what-if analysis"""

    @staticmethod
    def render(
        scenarios: Dict[str, pd.DataFrame],
        date_column: str = "date",
        value_column: str = "value",
        title: str = "Scenario Comparison",
        metric_name: str = "Value",
        export_filename: str = "scenarios",
    ):
        """
        Render scenario comparison chart

        Args:
            scenarios: Dictionary with scenario names and DataFrames
            date_column: Name of date column
            value_column: Name of value column
            title: Chart title
            metric_name: Name of the metric being compared
            export_filename: Filename for exports
        """
        if not scenarios:
            st.warning("No scenario data available")
            return

        fig = go.Figure()

        # Color palette for scenarios
        colors = ["#2E8B57", "#4169E1", "#DC143C", "#FF8C00", "#9370DB", "#20B2AA"]

        for i, (scenario_name, data) in enumerate(scenarios.items()):
            if data.empty:
                continue

            color = colors[i % len(colors)]

            fig.add_trace(
                go.Scatter(
                    x=data[date_column],
                    y=data[value_column],
                    mode="lines+markers",
                    name=scenario_name,
                    line=dict(color=color, width=3),
                    marker=dict(size=6),
                    hovertemplate=f"<b>{scenario_name}</b><br>"
                    + "Date: %{x}<br>"
                    + f"{metric_name}: $%{{y:,.2f}}<extra></extra>",
                )
            )

        # Apply theme
        fig = BaseChart._apply_theme(fig, title)
        fig.update_layout(
            xaxis_title="Date", yaxis_title=f"{metric_name} ($)", hovermode="x unified"
        )

        # Display chart
        st.plotly_chart(fig, use_container_width=True)

        # Add scenario comparison table
        with st.expander("📊 Scenario Comparison Table"):
            comparison_data = {}

            for scenario_name, data in scenarios.items():
                if not data.empty:
                    comparison_data[scenario_name] = {
                        "Average": data[value_column].mean(),
                        "Maximum": data[value_column].max(),
                        "Minimum": data[value_column].min(),
                        "Final Value": (
                            data[value_column].iloc[-1] if len(data) > 0 else 0
                        ),
                    }

            if comparison_data:
                comparison_df = pd.DataFrame(comparison_data).T
                comparison_df = comparison_df.round(2)
                st.dataframe(comparison_df, use_container_width=True)

        # Add export buttons
        BaseChart._add_export_buttons(fig, export_filename)


class WaterfallChart:
    """Waterfall chart for showing cumulative effects"""

    @staticmethod
    def render(
        categories: List[str],
        values: List[float],
        title: str = "Waterfall Analysis",
        start_value: float = 0,
        export_filename: str = "waterfall",
    ):
        """
        Render waterfall chart

        Args:
            categories: List of category names
            values: List of values (positive or negative)
            title: Chart title
            start_value: Starting value
            export_filename: Filename for exports
        """
        # Calculate cumulative values
        cumulative = [start_value]
        for value in values:
            cumulative.append(cumulative[-1] + value)

        # Prepare data for waterfall
        x_labels = ["Starting Value"] + categories + ["Final Value"]
        y_values = [start_value] + values + [cumulative[-1]]

        # Create colors (green for positive, red for negative)
        colors = ["blue"]  # Starting value
        for value in values:
            colors.append("green" if value >= 0 else "red")
        colors.append("blue")  # Final value

        fig = go.Figure(
            go.Waterfall(
                name="",
                orientation="v",
                measure=["absolute"] + ["relative"] * len(values) + ["total"],
                x=x_labels,
                textposition="outside",
                text=[f"${v:,.0f}" for v in y_values],
                y=y_values,
                connector={"line": {"color": "rgb(63, 63, 63)"}},
                increasing={"marker": {"color": "#2E8B57"}},
                decreasing={"marker": {"color": "#DC143C"}},
                totals={"marker": {"color": "#4169E1"}},
            )
        )

        # Apply theme
        fig = BaseChart._apply_theme(fig, title)
        fig.update_layout(
            xaxis_title="Categories", yaxis_title="Value ($)", showlegend=False
        )

        # Display chart
        st.plotly_chart(fig, use_container_width=True)

        # Add export buttons
        BaseChart._add_export_buttons(fig, export_filename)


class HeatmapChart:
    """Heatmap chart for correlation analysis"""

    @staticmethod
    def render(
        data: pd.DataFrame,
        title: str = "Correlation Heatmap",
        export_filename: str = "heatmap",
    ):
        """
        Render correlation heatmap

        Args:
            data: DataFrame with numeric columns
            title: Chart title
            export_filename: Filename for exports
        """
        # Calculate correlation matrix
        corr_matrix = data.corr()

        fig = go.Figure(
            data=go.Heatmap(
                z=corr_matrix.values,
                x=corr_matrix.columns,
                y=corr_matrix.columns,
                colorscale="RdBu",
                zmid=0,
                text=np.round(corr_matrix.values, 2),
                texttemplate="%{text}",
                textfont={"size": 10},
                hovertemplate="<b>%{y} vs %{x}</b><br>Correlation: %{z:.2f}<extra></extra>",
            )
        )

        # Apply theme
        fig = BaseChart._apply_theme(fig, title)
        fig.update_layout(xaxis_title="Variables", yaxis_title="Variables", height=500)

        # Display chart
        st.plotly_chart(fig, use_container_width=True)

        # Add export buttons
        BaseChart._add_export_buttons(fig, export_filename)


# Convenience functions for common chart patterns
def render_monthly_trends(
    data: pd.DataFrame, metrics: List[str], title: str = "Monthly Trends"
):
    """Render multiple metrics as monthly trends"""
    if data.empty:
        st.warning("No data available for trends")
        return

    fig = make_subplots(
        rows=len(metrics), cols=1, subplot_titles=metrics, vertical_spacing=0.08
    )

    colors = ["#2E8B57", "#4169E1", "#DC143C", "#FF8C00", "#9370DB"]

    for i, metric in enumerate(metrics):
        if metric in data.columns:
            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=data[metric],
                    mode="lines+markers",
                    name=metric,
                    line=dict(color=colors[i % len(colors)], width=2),
                    marker=dict(size=4),
                ),
                row=i + 1,
                col=1,
            )

    fig = BaseChart._apply_theme(fig, title)
    fig.update_layout(height=200 * len(metrics))

    st.plotly_chart(fig, use_container_width=True)


def render_kpi_sparklines(kpis: Dict[str, pd.Series]):
    """Render KPI sparklines in a grid"""
    cols = st.columns(len(kpis))

    for i, (kpi_name, data) in enumerate(kpis.items()):
        with cols[i]:
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=list(range(len(data))),
                    y=data.values,
                    mode="lines",
                    line=dict(color="#4169E1", width=2),
                    showlegend=False,
                )
            )

            fig.update_layout(
                title=kpi_name,
                height=150,
                margin=dict(l=10, r=10, t=30, b=10),
                xaxis=dict(showgrid=False, showticklabels=False),
                yaxis=dict(showgrid=False, showticklabels=False),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
            )

            st.plotly_chart(fig, use_container_width=True)


class ChartComponents:
    """Main chart components class that aggregates all chart types"""
    
    def __init__(self):
        self.base_chart = BaseChart()
        self.cash_flow_chart = CashFlowChart()
        self.revenue_breakdown_pie_chart = RevenueBreakdownPieChart()
        self.forecast_line_chart = ForecastLineChart()
        self.scenario_comparison_chart = ScenarioComparisonChart()
        self.waterfall_chart = WaterfallChart()
        self.heatmap_chart = HeatmapChart()
    
    # Cash Flow Charts
    def create_cash_flow_chart(self, data: pd.DataFrame, title: str = "Cash Flow Analysis", **kwargs):
        """Create interactive cash flow chart"""
        return self.cash_flow_chart.create_chart(data, title, **kwargs)
    
    # Revenue Charts
    def create_revenue_pie_chart(self, data: Dict[str, float], title: str = "Revenue Breakdown", **kwargs):
        """Create revenue breakdown pie chart"""
        return self.revenue_breakdown_pie_chart.create_chart(data, title, **kwargs)
    
    # Forecast Charts
    def create_forecast_chart(self, historical_data: pd.DataFrame, forecast_data: pd.DataFrame, 
                            title: str = "Financial Forecast", **kwargs):
        """Create forecast line chart with confidence bands"""
        return self.forecast_line_chart.create_chart(historical_data, forecast_data, title, **kwargs)
    
    # Scenario Analysis
    def create_scenario_comparison(self, scenarios: Dict[str, pd.DataFrame], 
                                 title: str = "Scenario Comparison", **kwargs):
        """Create scenario comparison chart"""
        return self.scenario_comparison_chart.create_chart(scenarios, title, **kwargs)
    
    # Waterfall Charts
    def create_waterfall_chart(self, categories: List[str], values: List[float], 
                             title: str = "Waterfall Analysis", **kwargs):
        """Create waterfall chart for cumulative effects"""
        return self.waterfall_chart.create_chart(categories, values, title, **kwargs)
    
    # Heatmap Charts
    def create_heatmap(self, data: pd.DataFrame, title: str = "Correlation Heatmap", **kwargs):
        """Create heatmap for correlation analysis"""
        return self.heatmap_chart.create_chart(data, title, **kwargs)
    
    # Utility methods
    def apply_theme(self, fig: go.Figure, title: str = None) -> go.Figure:
        """Apply consistent theme to any chart"""
        return self.base_chart._apply_theme(fig, title)

    @staticmethod
    def monthly_trend_chart(data, title="Monthly Trend"):
        """Development placeholder for monthly trend chart."""
        st.info(f"{title} chart is not yet implemented.")

    @staticmethod
    def yearly_trend_chart(data, title="Yearly Trend"):
        """Development placeholder for yearly trend chart."""
        st.info(f"{title} chart is not yet implemented.")

    @staticmethod
    def revenue_category_pie(data, title="Revenue by Category"):
        """Development placeholder for revenue category pie chart."""
        st.info(f"{title} chart is not yet implemented.")

    @staticmethod
    def cost_category_pie(data, title="Cost by Category"):
        """Development placeholder for cost category pie chart."""
        st.info(f"{title} chart is not yet implemented.")

    @staticmethod
    def revenue_cost_comparison_chart(data, title="Revenue vs Cost Comparison"):
        """Development placeholder for revenue vs cost comparison chart."""
        st.info(f"{title} chart is not yet implemented.")

    @staticmethod
    def cash_flow_chart(
        df: pd.DataFrame,
        title: str = "Cash Flow",
        date_column: str = "date",
        inflow_column: str = "inflow",
        outflow_column: str = "outflow",
    ):
        """Render a cash flow chart with flexible column naming.

        Renames provided columns to the standard schema expected by CashFlowChart.render
        and delegates rendering.
        """
        try:
            if df is None or df.empty:
                st.warning("No cash flow data available")
                return

            # Prepare rename map; only include keys that actually exist
            rename_map = {}
            if date_column in df.columns and date_column != "date":
                rename_map[date_column] = "date"
            if inflow_column in df.columns and inflow_column != "inflow":
                rename_map[inflow_column] = "inflow"
            if outflow_column in df.columns and outflow_column != "outflow":
                rename_map[outflow_column] = "outflow"

            data = df.rename(columns=rename_map)

            # Ensure required columns exist
            missing = [c for c in ["date", "inflow"] if c not in data.columns]
            if missing:
                st.warning(f"Missing required columns for cash flow chart: {', '.join(missing)}")
                return
            if "outflow" not in data.columns:
                # Gracefully default to zero outflows
                data = data.copy()
                data["outflow"] = 0.0

            return CashFlowChart.render(
                data,
                date_column="date",
                inflow_column="inflow",
                outflow_column="outflow",
                title=title,
            )
        except Exception as e:
            # Graceful error display without crashing the page
            st.warning(f"Unable to render cash flow chart: {e}")

    @staticmethod
    def category_breakdown_chart(data, title="Category Breakdown"):
        """Development placeholder for category breakdown chart."""
        st.info(f"{title} chart is not yet implemented.")

    @staticmethod
    def sales_line_chart(
        df: pd.DataFrame,
        title: str = "Daily Sales (Bookings)",
        date_column: str = "date",
        value_column: str = "total_amount",
        # Optional comparison overlay
        comp_df: Optional[pd.DataFrame] = None,
        comp_date_column: str = "date",
        comp_value_column: str = "total_amount",
        comp_label: str = "Comparison",
    ):
        """Render a daily sales (bookings) line chart with flexible columns.

        Expects a DataFrame with a date column and a numeric value column representing
        total daily booking amounts. Additional columns are ignored.
        """
        try:
            if df is None or df.empty:
                st.warning("No bookings sales data available")
                return

            # Prepare rename map for flexible columns
            rename_map = {}
            if date_column in df.columns and date_column != "date":
                rename_map[date_column] = "date"
            if value_column in df.columns and value_column != "value":
                rename_map[value_column] = "value"

            data = df.rename(columns=rename_map)

            # Ensure required columns
            if "date" not in data.columns or "value" not in data.columns:
                st.warning("Missing required columns for sales chart: date, value")
                return

            data = data.copy()
            data["date"] = pd.to_datetime(data["date"])  # ensure datetime
            data = data.sort_values("date")

            fig = go.Figure()

            # Current period line
            fig.add_trace(
                go.Scatter(
                    x=data["date"],
                    y=data["value"],
                    mode="lines+markers",
                    name="Sales (Bookings)",
                    line=dict(color="#4169E1", width=3),
                    marker=dict(size=6),
                    hovertemplate="<b>Sales</b><br>" + "Date: %{x}<br>" + "Amount: $%{y:,.2f}<extra></extra>",
                )
            )

            # Optional comparison overlay
            if comp_df is not None and not comp_df.empty:
                comp_map = {}
                if comp_date_column in comp_df.columns and comp_date_column != "date":
                    comp_map[comp_date_column] = "date"
                if comp_value_column in comp_df.columns and comp_value_column != "value":
                    comp_map[comp_value_column] = "value"
                comp_data = comp_df.rename(columns=comp_map).copy()
                if "date" in comp_data.columns and "value" in comp_data.columns:
                    comp_data["date"] = pd.to_datetime(comp_data["date"])  # ensure datetime
                    comp_data = comp_data.sort_values("date")
                    fig.add_trace(
                        go.Scatter(
                            x=comp_data["date"],
                            y=comp_data["value"],
                            mode="lines+markers",
                            name=comp_label,
                            line=dict(color="#A9A9A9", width=2, dash="dash"),
                            marker=dict(size=5, color="#A9A9A9"),
                            hovertemplate="<b>" + comp_label + "</b><br>" + "Date: %{x}<br>" + "Amount: $%{y:,.2f}<extra></extra>",
                        )
                    )

            fig = BaseChart._apply_theme(fig, title)
            fig.update_layout(xaxis_title="Date", yaxis_title="Sales ($)", hovermode="x unified")

            st.plotly_chart(fig, use_container_width=True)

            BaseChart._add_export_buttons(fig, "sales_bookings")
        except Exception as e:
            st.warning(f"Unable to render sales chart: {e}")
