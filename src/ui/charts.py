"""
Chart components for data visualization.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Dict, List, Optional, Any
from decimal import Decimal
from ..utils.currency_utils import CurrencyUtils


class ChartComponents:
    """Collection of reusable chart components."""

    @staticmethod
    def line_chart(
        data: pd.DataFrame,
        x_col: str,
        y_col: str,
        title: str,
        color_col: Optional[str] = None,
        height: int = 400,
    ) -> None:
        """Display line chart."""
        if data.empty:
            st.info("No data available for chart")
            return

        fig = px.line(
            data, x=x_col, y=y_col, color=color_col, title=title, height=height
        )

        fig.update_layout(
            xaxis_title=x_col.replace("_", " ").title(),
            yaxis_title=y_col.replace("_", " ").title(),
            showlegend=bool(color_col),
        )

        st.plotly_chart(fig, use_container_width=True)

    @staticmethod
    def bar_chart(
        data: pd.DataFrame,
        x_col: str,
        y_col: str,
        title: str,
        color_col: Optional[str] = None,
        height: int = 400,
        orientation: str = "v",
    ) -> None:
        """Display bar chart."""
        if data.empty:
            st.info("No data available for chart")
            return

        fig = px.bar(
            data,
            x=x_col if orientation == "v" else y_col,
            y=y_col if orientation == "v" else x_col,
            color=color_col,
            title=title,
            height=height,
            orientation=orientation,
        )

        fig.update_layout(
            xaxis_title=x_col.replace("_", " ").title(),
            yaxis_title=y_col.replace("_", " ").title(),
            showlegend=bool(color_col),
        )

        st.plotly_chart(fig, use_container_width=True)

    @staticmethod
    def pie_chart(
        data: pd.DataFrame,
        values_col: str,
        names_col: str,
        title: str,
        height: int = 400,
    ) -> None:
        """Display pie chart."""
        if data.empty:
            st.info("No data available for chart")
            return

        fig = px.pie(
            data, values=values_col, names=names_col, title=title, height=height
        )

        fig.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig, use_container_width=True)

    @staticmethod
    def cash_flow_chart(
        sales_data: pd.DataFrame,
        costs_data: pd.DataFrame,
        date_col: str = "date",
        amount_col: str = "amount_usd",
        title: str = "Cash Flow Analysis",
    ) -> None:
        """Display cash flow chart with sales and costs."""
        if sales_data.empty and costs_data.empty:
            st.info("No data available for cash flow chart")
            return

        fig = make_subplots(specs=[[{"secondary_y": True}]])

        # Add sales line
        if not sales_data.empty:
            fig.add_trace(
                go.Scatter(
                    x=sales_data[date_col],
                    y=sales_data[amount_col],
                    mode="lines+markers",
                    name="Sales",
                    line=dict(color="green", width=3),
                ),
                secondary_y=False,
            )

        # Add costs line
        if not costs_data.empty:
            fig.add_trace(
                go.Scatter(
                    x=costs_data[date_col],
                    y=costs_data[amount_col],
                    mode="lines+markers",
                    name="Costs",
                    line=dict(color="red", width=3),
                ),
                secondary_y=False,
            )

        # Calculate net cash flow if both datasets exist
        if not sales_data.empty and not costs_data.empty:
            # Merge data on date
            merged = pd.merge(
                sales_data.groupby(date_col)[amount_col].sum().reset_index(),
                costs_data.groupby(date_col)[amount_col].sum().reset_index(),
                on=date_col,
                how="outer",
                suffixes=("_sales", "_costs"),
            ).fillna(0)

            merged["net_flow"] = (
                merged[f"{amount_col}_sales"] - merged[f"{amount_col}_costs"]
            )

            fig.add_trace(
                go.Scatter(
                    x=merged[date_col],
                    y=merged["net_flow"],
                    mode="lines+markers",
                    name="Net Cash Flow",
                    line=dict(color="blue", width=2, dash="dash"),
                ),
                secondary_y=True,
            )

        fig.update_layout(title=title, height=500, hovermode="x unified")

        fig.update_xaxes(title_text="Date")
        fig.update_yaxes(title_text="Amount (USD)", secondary_y=False)
        fig.update_yaxes(title_text="Net Cash Flow (USD)", secondary_y=True)

        st.plotly_chart(fig, use_container_width=True)

    @staticmethod
    def category_breakdown_chart(
        data: pd.DataFrame,
        category_col: str,
        amount_col: str,
        title: str = "Category Breakdown",
        chart_type: str = "pie",
    ) -> None:
        """Display category breakdown chart."""
        if data.empty:
            st.info("No data available for category breakdown")
            return

        # Group by category and sum amounts
        grouped = data.groupby(category_col)[amount_col].sum().reset_index()
        grouped = grouped.sort_values(amount_col, ascending=False)

        if chart_type == "pie":
            ChartComponents.pie_chart(grouped, amount_col, category_col, title)
        else:
            ChartComponents.bar_chart(
                grouped, category_col, amount_col, title, orientation="h"
            )

    @staticmethod
    def monthly_trend_chart(
        data: pd.DataFrame, date_col: str, amount_col: str, title: str = "Monthly Trend"
    ) -> None:
        """Display monthly trend chart."""
        if data.empty:
            st.info("No data available for monthly trend")
            return

        # Convert date column to datetime if it's not already
        data = data.copy()
        data[date_col] = pd.to_datetime(data[date_col])

        # Group by month
        data["month"] = data[date_col].dt.to_period("M")
        monthly_data = data.groupby("month")[amount_col].sum().reset_index()
        monthly_data["month"] = monthly_data["month"].astype(str)

        ChartComponents.line_chart(monthly_data, "month", amount_col, title)

    @staticmethod
    def comparison_chart(
        current_data: pd.DataFrame,
        previous_data: pd.DataFrame,
        x_col: str,
        y_col: str,
        title: str = "Period Comparison",
    ) -> None:
        """Display comparison chart between two periods."""
        if current_data.empty and previous_data.empty:
            st.info("No data available for comparison")
            return

        fig = go.Figure()

        if not current_data.empty:
            fig.add_trace(
                go.Bar(
                    x=current_data[x_col],
                    y=current_data[y_col],
                    name="Current Period",
                    marker_color="lightblue",
                )
            )

        if not previous_data.empty:
            fig.add_trace(
                go.Bar(
                    x=previous_data[x_col],
                    y=previous_data[y_col],
                    name="Previous Period",
                    marker_color="lightgray",
                )
            )

        fig.update_layout(
            title=title,
            barmode="group",
            height=400,
            xaxis_title=x_col.replace("_", " ").title(),
            yaxis_title=y_col.replace("_", " ").title(),
        )

        st.plotly_chart(fig, use_container_width=True)

    @staticmethod
    def gauge_chart(
        value: float,
        max_value: float,
        title: str,
        color_ranges: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Display gauge chart for KPIs."""
        default_ranges = [
            {"range": [0, max_value * 0.5], "color": "red"},
            {"range": [max_value * 0.5, max_value * 0.8], "color": "yellow"},
            {"range": [max_value * 0.8, max_value], "color": "green"},
        ]

        ranges = color_ranges or default_ranges

        fig = go.Figure(
            go.Indicator(
                mode="gauge+number+delta",
                value=value,
                domain={"x": [0, 1], "y": [0, 1]},
                title={"text": title},
                gauge={
                    "axis": {"range": [None, max_value]},
                    "bar": {"color": "darkblue"},
                    "steps": ranges,
                    "threshold": {
                        "line": {"color": "red", "width": 4},
                        "thickness": 0.75,
                        "value": max_value * 0.9,
                    },
                },
            )
        )

        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
