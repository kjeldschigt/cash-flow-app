"""
Main Dashboard Page Component
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import sys
import os

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from ui.components.metrics import (
    FinancialSummaryCard, CashFlowIndicator, KPIGrid,
    render_revenue_metrics, render_cost_breakdown_metrics
)
from ui.components.charts import (
    CashFlowChart, RevenueBreakdownPieChart, ForecastLineChart,
    render_monthly_trends, render_kpi_sparklines
)
from ui.components.tables import TransactionTable, render_financial_summary_table
from ui.layouts.dashboard import DashboardLayout, WidgetManager, create_financial_overview_layout

class DashboardPage:
    """Main dashboard page with overview metrics and charts"""
    
    def __init__(self):
        """Initialize dashboard page"""
        self.page_title = "Financial Overview"
        self.page_icon = "🏠"
    
    def render(self, data_manager=None):
        """
        Render complete dashboard page
        
        Args:
            data_manager: Data manager instance for loading data
        """
        st.set_page_config(
            page_title=self.page_title,
            page_icon=self.page_icon,
            layout="wide"
        )
        
        st.title("🏠 Financial Dashboard")
        
        # Load dashboard data
        dashboard_data = self._load_dashboard_data(data_manager)
        
        # Render main sections
        self._render_overview_section(dashboard_data)
        self._render_cash_flow_section(dashboard_data)
        self._render_analytics_section(dashboard_data)
        self._render_recent_transactions(dashboard_data)
    
    def _load_dashboard_data(self, data_manager) -> Dict[str, Any]:
        """Load all data needed for dashboard"""
        try:
            if data_manager is None:
                # Return sample data if no data manager
                return self._get_sample_data()
            
            # Load real data
            current_date = datetime.now()
            start_date = current_date - timedelta(days=30)
            
            # Load various data sources
            costs_data = data_manager.load_costs(start_date, current_date)
            sales_data = data_manager.load_sales_orders()
            cash_out_data = data_manager.load_cash_out()
            
            # Calculate metrics
            total_revenue = sales_data['amount'].sum() if not sales_data.empty else 0
            total_costs = costs_data['amount'].sum() if not costs_data.empty else 0
            total_cash_out = cash_out_data['amount'].sum() if not cash_out_data.empty else 0
            
            net_profit = total_revenue - total_costs
            profit_margin = (net_profit / total_revenue * 100) if total_revenue > 0 else 0
            
            return {
                'revenue': total_revenue,
                'costs': total_costs,
                'cash_out': total_cash_out,
                'profit': net_profit,
                'margin': profit_margin,
                'costs_data': costs_data,
                'sales_data': sales_data,
                'cash_out_data': cash_out_data
            }
            
        except Exception as e:
            st.error(f"Error loading dashboard data: {str(e)}")
            return self._get_sample_data()
    
    def _get_sample_data(self) -> Dict[str, Any]:
        """Get sample data for demonstration"""
        # Generate sample data
        dates = pd.date_range(start='2024-01-01', end='2024-08-17', freq='D')
        
        sample_costs = pd.DataFrame({
            'date': dates[:100],
            'amount': [1000 + (i * 10) + (i % 7 * 200) for i in range(100)],
            'category': ['Operating', 'Marketing', 'Personnel', 'Other'][i % 4] for i in range(100)
        })
        
        sample_sales = pd.DataFrame({
            'date': dates[:80],
            'amount': [5000 + (i * 50) + (i % 5 * 500) for i in range(80)],
            'category': ['Product Sales', 'Service Revenue', 'Subscriptions'][i % 3] for i in range(80)
        })
        
        return {
            'revenue': 450000,
            'costs': 320000,
            'cash_out': 280000,
            'profit': 130000,
            'margin': 28.9,
            'costs_data': sample_costs,
            'sales_data': sample_sales,
            'cash_out_data': sample_costs.copy()
        }
    
    def _render_overview_section(self, data: Dict[str, Any]):
        """Render financial overview section"""
        st.header("📊 Financial Overview")
        
        # Financial summary card
        FinancialSummaryCard.render(
            revenue=data['revenue'],
            costs=data['costs'],
            currency="USD",
            period="month"
        )
        
        st.divider()
        
        # Cash flow indicator
        CashFlowIndicator.render(
            cash_inflow=data['revenue'],
            cash_outflow=data['cash_out'],
            currency="USD",
            period="month"
        )
    
    def _render_cash_flow_section(self, data: Dict[str, Any]):
        """Render cash flow analysis section"""
        st.header("💰 Cash Flow Analysis")
        
        # Prepare cash flow data
        if not data['sales_data'].empty and not data['cash_out_data'].empty:
            # Combine inflow and outflow data
            cash_flow_data = self._prepare_cash_flow_data(
                data['sales_data'], 
                data['cash_out_data']
            )
            
            # Render cash flow chart
            CashFlowChart.render(
                data=cash_flow_data,
                title="Monthly Cash Flow Trend",
                show_net_flow=True,
                show_cumulative=True
            )
        else:
            st.info("No cash flow data available for the selected period")
    
    def _render_analytics_section(self, data: Dict[str, Any]):
        """Render analytics and charts section"""
        st.header("📈 Financial Analytics")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Revenue breakdown
            if not data['sales_data'].empty:
                revenue_breakdown = data['sales_data'].groupby('category')['amount'].sum().to_dict()
                
                RevenueBreakdownPieChart.render(
                    data=revenue_breakdown,
                    title="Revenue by Category"
                )
            else:
                st.info("No revenue data available")
        
        with col2:
            # Cost breakdown
            if not data['costs_data'].empty:
                cost_breakdown = data['costs_data'].groupby('category')['amount'].sum().to_dict()
                
                RevenueBreakdownPieChart.render(
                    data=cost_breakdown,
                    title="Costs by Category"
                )
            else:
                st.info("No cost data available")
        
        # Monthly trends
        if not data['costs_data'].empty:
            monthly_data = self._prepare_monthly_trends(data)
            render_monthly_trends(
                monthly_data,
                ['Revenue', 'Costs', 'Profit'],
                "Monthly Financial Trends"
            )
    
    def _render_recent_transactions(self, data: Dict[str, Any]):
        """Render recent transactions section"""
        st.header("📋 Recent Transactions")
        
        # Combine recent transactions
        recent_transactions = self._get_recent_transactions(data)
        
        if not recent_transactions.empty:
            # Format currency columns
            formatters = {
                'amount': lambda x: f"${x:,.2f}",
                'date': lambda x: x.strftime('%Y-%m-%d') if pd.notnull(x) else ''
            }
            
            TransactionTable.render(
                data=recent_transactions,
                title="Recent Financial Transactions",
                page_size=10,
                formatters=formatters,
                export_filename="recent_transactions"
            )
        else:
            st.info("No recent transactions available")
    
    def _prepare_cash_flow_data(self, sales_data: pd.DataFrame, cash_out_data: pd.DataFrame) -> pd.DataFrame:
        """Prepare cash flow data for charting"""
        # Aggregate by date
        sales_daily = sales_data.groupby('date')['amount'].sum().reset_index()
        sales_daily.columns = ['date', 'inflow']
        
        cash_out_daily = cash_out_data.groupby('date')['amount'].sum().reset_index()
        cash_out_daily.columns = ['date', 'outflow']
        
        # Merge data
        cash_flow = pd.merge(sales_daily, cash_out_daily, on='date', how='outer').fillna(0)
        
        return cash_flow
    
    def _prepare_monthly_trends(self, data: Dict[str, Any]) -> pd.DataFrame:
        """Prepare monthly trend data"""
        # Aggregate by month
        if not data['sales_data'].empty:
            sales_monthly = data['sales_data'].set_index('date').resample('M')['amount'].sum()
        else:
            sales_monthly = pd.Series(dtype=float)
        
        if not data['costs_data'].empty:
            costs_monthly = data['costs_data'].set_index('date').resample('M')['amount'].sum()
        else:
            costs_monthly = pd.Series(dtype=float)
        
        # Combine into DataFrame
        monthly_data = pd.DataFrame({
            'Revenue': sales_monthly,
            'Costs': costs_monthly
        }).fillna(0)
        
        monthly_data['Profit'] = monthly_data['Revenue'] - monthly_data['Costs']
        
        return monthly_data
    
    def _get_recent_transactions(self, data: Dict[str, Any]) -> pd.DataFrame:
        """Get recent transactions from all sources"""
        transactions = []
        
        # Add sales transactions
        if not data['sales_data'].empty:
            sales_recent = data['sales_data'].tail(10).copy()
            sales_recent['type'] = 'Revenue'
            transactions.append(sales_recent[['date', 'amount', 'category', 'type']])
        
        # Add cost transactions
        if not data['costs_data'].empty:
            costs_recent = data['costs_data'].tail(10).copy()
            costs_recent['type'] = 'Cost'
            transactions.append(costs_recent[['date', 'amount', 'category', 'type']])
        
        if transactions:
            combined = pd.concat(transactions, ignore_index=True)
            return combined.sort_values('date', ascending=False).head(20)
        
        return pd.DataFrame()

class DashboardPageWithLayout:
    """Dashboard page using the layout system"""
    
    def __init__(self):
        """Initialize dashboard with layout system"""
        self.layout = None
    
    def render(self, data_manager=None):
        """Render dashboard using layout system"""
        # Load data
        dashboard_data = self._load_dashboard_data(data_manager)
        
        # Create layout configuration
        layout_config = create_financial_overview_layout(dashboard_data)
        
        # Initialize and render layout
        self.layout = DashboardLayout(layout_config)
        self.layout.render()
    
    def _load_dashboard_data(self, data_manager) -> Dict[str, Any]:
        """Load dashboard data (same as DashboardPage)"""
        # Reuse the same data loading logic
        dashboard_page = DashboardPage()
        return dashboard_page._load_dashboard_data(data_manager)

# Convenience function for easy integration
def render_dashboard_page(data_manager=None, use_layout_system: bool = False):
    """
    Render dashboard page
    
    Args:
        data_manager: Data manager instance
        use_layout_system: Whether to use the advanced layout system
    """
    if use_layout_system:
        dashboard = DashboardPageWithLayout()
    else:
        dashboard = DashboardPage()
    
    dashboard.render(data_manager)

# Example usage for standalone page
if __name__ == "__main__":
    render_dashboard_page()
