"""
Reusable Metric Components for Cash Flow Dashboard
"""

import streamlit as st
import plotly.graph_objects as go
from typing import Optional, Dict, Any, Union
from datetime import datetime, timedelta
import pandas as pd

class MetricCard:
    """Base metric card component with consistent styling"""
    
    @staticmethod
    def render(
        title: str,
        value: Union[str, int, float],
        delta: Optional[Union[str, int, float]] = None,
        delta_color: str = "normal",
        help_text: Optional[str] = None,
        prefix: str = "",
        suffix: str = "",
        format_value: bool = True
    ):
        """
        Render a metric card with consistent styling
        
        Args:
            title: Metric title
            value: Main metric value
            delta: Change value (optional)
            delta_color: Color for delta ("normal", "inverse", "off")
            help_text: Tooltip help text
            prefix: Value prefix (e.g., "$", "€")
            suffix: Value suffix (e.g., "%", "K", "M")
            format_value: Whether to format numeric values with commas
        """
        # Format value if numeric
        if format_value and isinstance(value, (int, float)):
            if abs(value) >= 1_000_000:
                formatted_value = f"{value / 1_000_000:.1f}M"
            elif abs(value) >= 1_000:
                formatted_value = f"{value / 1_000:.1f}K"
            else:
                formatted_value = f"{value:,.0f}" if isinstance(value, int) else f"{value:,.2f}"
        else:
            formatted_value = str(value)
        
        display_value = f"{prefix}{formatted_value}{suffix}"
        
        # Format delta if provided
        formatted_delta = None
        if delta is not None:
            if isinstance(delta, (int, float)):
                if format_value:
                    if abs(delta) >= 1_000_000:
                        formatted_delta = f"{delta / 1_000_000:.1f}M"
                    elif abs(delta) >= 1_000:
                        formatted_delta = f"{delta / 1_000:.1f}K"
                    else:
                        formatted_delta = f"{delta:,.0f}" if isinstance(delta, int) else f"{delta:,.2f}"
                else:
                    formatted_delta = str(delta)
            else:
                formatted_delta = str(delta)
        
        st.metric(
            label=title,
            value=display_value,
            delta=formatted_delta,
            delta_color=delta_color,
            help=help_text
        )

class RevenueMetricCard:
    """Specialized revenue metric card with revenue-specific formatting"""
    
    @staticmethod
    def render(
        revenue: float,
        previous_revenue: Optional[float] = None,
        currency: str = "USD",
        period: str = "month",
        help_text: Optional[str] = None
    ):
        """
        Render revenue metric card
        
        Args:
            revenue: Current revenue amount
            previous_revenue: Previous period revenue for comparison
            currency: Currency symbol/code
            period: Time period (month, quarter, year)
            help_text: Optional help text
        """
        currency_symbols = {
            "USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥", "CAD": "C$", "AUD": "A$"
        }
        
        symbol = currency_symbols.get(currency, currency)
        
        delta = None
        if previous_revenue is not None and previous_revenue != 0:
            delta = revenue - previous_revenue
        
        title = f"Revenue ({period.title()})"
        if not help_text:
            help_text = f"Total revenue for the current {period}"
        
        MetricCard.render(
            title=title,
            value=revenue,
            delta=delta,
            delta_color="normal",
            help_text=help_text,
            prefix=symbol
        )

class CostMetricCard:
    """Specialized cost metric card with cost-specific formatting"""
    
    @staticmethod
    def render(
        cost: float,
        previous_cost: Optional[float] = None,
        currency: str = "USD",
        period: str = "month",
        cost_type: str = "Total",
        help_text: Optional[str] = None
    ):
        """
        Render cost metric card
        
        Args:
            cost: Current cost amount
            previous_cost: Previous period cost for comparison
            currency: Currency symbol/code
            period: Time period (month, quarter, year)
            cost_type: Type of cost (Total, Operating, etc.)
            help_text: Optional help text
        """
        currency_symbols = {
            "USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥", "CAD": "C$", "AUD": "A$"
        }
        
        symbol = currency_symbols.get(currency, currency)
        
        delta = None
        delta_color = "inverse"  # For costs, lower is better
        if previous_cost is not None and previous_cost != 0:
            delta = cost - previous_cost
        
        title = f"{cost_type} Costs ({period.title()})"
        if not help_text:
            help_text = f"{cost_type} costs for the current {period}"
        
        MetricCard.render(
            title=title,
            value=cost,
            delta=delta,
            delta_color=delta_color,
            help_text=help_text,
            prefix=symbol
        )

class ProfitMarginCard:
    """Profit margin card with color-coded indicators"""
    
    @staticmethod
    def render(
        margin: float,
        previous_margin: Optional[float] = None,
        period: str = "month",
        help_text: Optional[str] = None
    ):
        """
        Render profit margin card with color coding
        
        Args:
            margin: Current profit margin (as percentage)
            previous_margin: Previous period margin for comparison
            period: Time period (month, quarter, year)
            help_text: Optional help text
        """
        delta = None
        if previous_margin is not None:
            delta = margin - previous_margin
        
        title = f"Profit Margin ({period.title()})"
        if not help_text:
            help_text = f"Profit margin percentage for the current {period}"
        
        # Color coding based on margin level
        if margin >= 20:
            delta_color = "normal"  # Green for good margins
        elif margin >= 10:
            delta_color = "normal"  # Normal for acceptable margins
        else:
            delta_color = "inverse"  # Red for low margins
        
        MetricCard.render(
            title=title,
            value=margin,
            delta=delta,
            delta_color=delta_color,
            help_text=help_text,
            suffix="%",
            format_value=False
        )

class TrendIndicator:
    """Trend indicator component with visual arrows and colors"""
    
    @staticmethod
    def render(
        current_value: float,
        previous_value: float,
        title: str = "Trend",
        show_percentage: bool = True,
        invert_colors: bool = False
    ):
        """
        Render trend indicator with arrows and colors
        
        Args:
            current_value: Current period value
            previous_value: Previous period value
            title: Indicator title
            show_percentage: Show percentage change
            invert_colors: Invert color logic (for costs where down is good)
        """
        if previous_value == 0:
            st.warning(f"{title}: No previous data for comparison")
            return
        
        change = current_value - previous_value
        percentage_change = (change / abs(previous_value)) * 100
        
        # Determine trend direction and color
        if change > 0:
            arrow = "↗️" if not invert_colors else "↗️"
            color = "green" if not invert_colors else "red"
            trend_text = "Increasing"
        elif change < 0:
            arrow = "↘️" if not invert_colors else "↘️"
            color = "red" if not invert_colors else "green"
            trend_text = "Decreasing"
        else:
            arrow = "➡️"
            color = "gray"
            trend_text = "Stable"
        
        # Format the display
        if show_percentage:
            change_text = f"{abs(percentage_change):.1f}%"
        else:
            change_text = f"{abs(change):,.2f}"
        
        # Create columns for layout
        col1, col2, col3 = st.columns([2, 1, 2])
        
        with col1:
            st.markdown(f"**{title}**")
        
        with col2:
            st.markdown(f"<span style='font-size: 24px;'>{arrow}</span>", unsafe_allow_html=True)
        
        with col3:
            if color == "green":
                st.success(f"{trend_text} {change_text}")
            elif color == "red":
                st.error(f"{trend_text} {change_text}")
            else:
                st.info(f"{trend_text}")

class KPIGrid:
    """Grid layout for multiple KPI metrics"""
    
    @staticmethod
    def render(metrics: list, columns: int = 4):
        """
        Render metrics in a responsive grid
        
        Args:
            metrics: List of metric dictionaries with render functions
            columns: Number of columns in the grid
        """
        # Create columns
        cols = st.columns(columns)
        
        for i, metric in enumerate(metrics):
            col_index = i % columns
            
            with cols[col_index]:
                if callable(metric):
                    metric()
                elif isinstance(metric, dict):
                    # Extract metric parameters and render
                    metric_type = metric.get('type', 'basic')
                    
                    if metric_type == 'revenue':
                        RevenueMetricCard.render(**metric.get('params', {}))
                    elif metric_type == 'cost':
                        CostMetricCard.render(**metric.get('params', {}))
                    elif metric_type == 'margin':
                        ProfitMarginCard.render(**metric.get('params', {}))
                    else:
                        MetricCard.render(**metric.get('params', {}))

class FinancialSummaryCard:
    """Comprehensive financial summary card"""
    
    @staticmethod
    def render(
        revenue: float,
        costs: float,
        previous_revenue: Optional[float] = None,
        previous_costs: Optional[float] = None,
        currency: str = "USD",
        period: str = "month"
    ):
        """
        Render financial summary with revenue, costs, and profit
        
        Args:
            revenue: Current revenue
            costs: Current costs
            previous_revenue: Previous period revenue
            previous_costs: Previous period costs
            currency: Currency code
            period: Time period
        """
        profit = revenue - costs
        previous_profit = None
        if previous_revenue is not None and previous_costs is not None:
            previous_profit = previous_revenue - previous_costs
        
        margin = (profit / revenue * 100) if revenue != 0 else 0
        previous_margin = None
        if previous_revenue is not None and previous_revenue != 0 and previous_profit is not None:
            previous_margin = (previous_profit / previous_revenue * 100)
        
        st.subheader(f"Financial Summary ({period.title()})")
        
        # Create metrics grid
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            RevenueMetricCard.render(
                revenue=revenue,
                previous_revenue=previous_revenue,
                currency=currency,
                period=period
            )
        
        with col2:
            CostMetricCard.render(
                cost=costs,
                previous_cost=previous_costs,
                currency=currency,
                period=period
            )
        
        with col3:
            profit_delta = None
            if previous_profit is not None:
                profit_delta = profit - previous_profit
            
            MetricCard.render(
                title=f"Profit ({period.title()})",
                value=profit,
                delta=profit_delta,
                delta_color="normal",
                prefix={"USD": "$", "EUR": "€", "GBP": "£"}.get(currency, currency),
                help_text=f"Net profit for the current {period}"
            )
        
        with col4:
            ProfitMarginCard.render(
                margin=margin,
                previous_margin=previous_margin,
                period=period
            )

class CashFlowIndicator:
    """Cash flow status indicator with visual elements"""
    
    @staticmethod
    def render(
        cash_inflow: float,
        cash_outflow: float,
        currency: str = "USD",
        period: str = "month"
    ):
        """
        Render cash flow indicator
        
        Args:
            cash_inflow: Total cash inflow
            cash_outflow: Total cash outflow
            currency: Currency code
            period: Time period
        """
        net_cash_flow = cash_inflow - cash_outflow
        
        st.subheader(f"Cash Flow ({period.title()})")
        
        col1, col2, col3 = st.columns(3)
        
        currency_symbol = {"USD": "$", "EUR": "€", "GBP": "£"}.get(currency, currency)
        
        with col1:
            st.metric(
                label="💰 Cash Inflow",
                value=f"{currency_symbol}{cash_inflow:,.2f}",
                help=f"Total cash received during {period}"
            )
        
        with col2:
            st.metric(
                label="💸 Cash Outflow",
                value=f"{currency_symbol}{cash_outflow:,.2f}",
                delta_color="inverse",
                help=f"Total cash spent during {period}"
            )
        
        with col3:
            if net_cash_flow >= 0:
                st.success(f"✅ Positive Cash Flow")
                st.metric(
                    label="Net Cash Flow",
                    value=f"{currency_symbol}{net_cash_flow:,.2f}",
                    delta_color="normal"
                )
            else:
                st.error(f"⚠️ Negative Cash Flow")
                st.metric(
                    label="Net Cash Flow",
                    value=f"{currency_symbol}{net_cash_flow:,.2f}",
                    delta_color="inverse"
                )

# Convenience functions for common metric patterns
def render_revenue_metrics(data: Dict[str, Any], currency: str = "USD", period: str = "month"):
    """Render standard revenue metrics"""
    metrics = [
        {
            'type': 'revenue',
            'params': {
                'revenue': data.get('current_revenue', 0),
                'previous_revenue': data.get('previous_revenue'),
                'currency': currency,
                'period': period
            }
        }
    ]
    
    if 'recurring_revenue' in data:
        metrics.append({
            'type': 'basic',
            'params': {
                'title': f"Recurring Revenue ({period.title()})",
                'value': data['recurring_revenue'],
                'prefix': {"USD": "$", "EUR": "€", "GBP": "£"}.get(currency, currency),
                'help_text': f"Recurring revenue for {period}"
            }
        })
    
    KPIGrid.render(metrics, columns=len(metrics))

def render_cost_breakdown_metrics(data: Dict[str, Any], currency: str = "USD", period: str = "month"):
    """Render cost breakdown metrics"""
    metrics = []
    
    cost_categories = ['operating_costs', 'marketing_costs', 'personnel_costs', 'other_costs']
    
    for category in cost_categories:
        if category in data:
            category_name = category.replace('_', ' ').title()
            metrics.append({
                'type': 'cost',
                'params': {
                    'cost': data[category],
                    'currency': currency,
                    'period': period,
                    'cost_type': category_name.replace(' Costs', '')
                }
            })
    
    if metrics:
        KPIGrid.render(metrics, columns=min(len(metrics), 4))
