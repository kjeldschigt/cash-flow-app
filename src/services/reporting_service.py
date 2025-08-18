"""
Reporting Service
Generates financial reports and exports in multiple formats.
"""

import logging
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Optional, Any, Union
from io import BytesIO
import json
from ..repositories.base import DatabaseConnection
from ..models.analytics import BusinessMetrics, CashFlowMetrics

logger = logging.getLogger(__name__)

class ReportFormat:
    """Report format constants"""
    PDF = "pdf"
    EXCEL = "excel"
    CSV = "csv"
    JSON = "json"

class ReportType:
    """Report type constants"""
    PROFIT_LOSS = "profit_loss"
    CASH_FLOW = "cash_flow"
    BALANCE_SHEET = "balance_sheet"
    EXECUTIVE_SUMMARY = "executive_summary"

class ReportingService:
    """Service for generating financial reports and visualizations."""
    
    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection
    
    def generate_profit_loss_report(
        self, 
        start_date: date, 
        end_date: date,
        format_type: str = ReportFormat.JSON
    ) -> Dict[str, Any]:
        """
        Generate Profit & Loss statement.
        
        Args:
            start_date: Report start date
            end_date: Report end date
            format_type: Output format (json, csv, excel, pdf)
            
        Returns:
            Dict containing P&L data and metadata
        """
        try:
            with self.db.get_connection() as conn:
                # Revenue data
                revenue_query = """
                    SELECT 
                        DATE(order_date) as date,
                        SUM(amount) as revenue,
                        currency,
                        COUNT(*) as transaction_count
                    FROM sales_orders 
                    WHERE order_date BETWEEN ? AND ?
                    GROUP BY DATE(order_date), currency
                    ORDER BY date
                """
                revenue_data = pd.read_sql_query(
                    revenue_query, 
                    conn, 
                    params=[start_date.isoformat(), end_date.isoformat()]
                )
                
                # Cost data
                cost_query = """
                    SELECT 
                        DATE(cost_date) as date,
                        SUM(amount) as costs,
                        category,
                        currency
                    FROM costs 
                    WHERE cost_date BETWEEN ? AND ?
                    GROUP BY DATE(cost_date), category, currency
                    ORDER BY date
                """
                cost_data = pd.read_sql_query(
                    cost_query, 
                    conn, 
                    params=[start_date.isoformat(), end_date.isoformat()]
                )
            
            # Calculate totals
            total_revenue = revenue_data['revenue'].sum() if not revenue_data.empty else 0
            total_costs = cost_data['costs'].sum() if not cost_data.empty else 0
            gross_profit = total_revenue - total_costs
            gross_margin = (gross_profit / total_revenue * 100) if total_revenue > 0 else 0
            
            # Prepare P&L structure
            pl_report = {
                'report_type': ReportType.PROFIT_LOSS,
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'revenue': {
                    'total_revenue': float(total_revenue),
                    'by_date': revenue_data.to_dict('records') if not revenue_data.empty else []
                },
                'costs': {
                    'total_costs': float(total_costs),
                    'by_category': cost_data.groupby('category')['costs'].sum().to_dict() if not cost_data.empty else {},
                    'by_date': cost_data.to_dict('records') if not cost_data.empty else []
                },
                'profitability': {
                    'gross_profit': float(gross_profit),
                    'gross_margin_percentage': float(gross_margin),
                    'net_profit': float(gross_profit),  # Simplified - no tax/interest
                    'net_margin_percentage': float(gross_margin)
                },
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'currency': 'USD',
                    'format': format_type
                }
            }
            
            return self._format_report(pl_report, format_type)
            
        except Exception as e:
            logger.error(f"Error generating P&L report: {str(e)}")
            raise
    
    def generate_cash_flow_report(
        self, 
        start_date: date, 
        end_date: date,
        format_type: str = ReportFormat.JSON
    ) -> Dict[str, Any]:
        """Generate Cash Flow Statement."""
        try:
            with self.db.get_connection() as conn:
                # Operating cash flow
                operating_query = """
                    SELECT 
                        'revenue' as type,
                        DATE(order_date) as date,
                        SUM(amount) as amount
                    FROM sales_orders 
                    WHERE order_date BETWEEN ? AND ?
                    GROUP BY DATE(order_date)
                    
                    UNION ALL
                    
                    SELECT 
                        'expense' as type,
                        DATE(cost_date) as date,
                        -SUM(amount) as amount
                    FROM costs 
                    WHERE cost_date BETWEEN ? AND ?
                    GROUP BY DATE(cost_date)
                    
                    ORDER BY date
                """
                cash_flow_data = pd.read_sql_query(
                    operating_query, 
                    conn, 
                    params=[
                        start_date.isoformat(), end_date.isoformat(),
                        start_date.isoformat(), end_date.isoformat()
                    ]
                )
            
            # Calculate cash flow metrics
            operating_cash_flow = cash_flow_data['amount'].sum() if not cash_flow_data.empty else 0
            
            # Daily cash flow
            daily_cf = cash_flow_data.groupby('date')['amount'].sum().reset_index()
            daily_cf['cumulative'] = daily_cf['amount'].cumsum()
            
            cash_flow_report = {
                'report_type': ReportType.CASH_FLOW,
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'operating_activities': {
                    'net_operating_cash_flow': float(operating_cash_flow),
                    'daily_cash_flow': daily_cf.to_dict('records') if not daily_cf.empty else []
                },
                'investing_activities': {
                    'net_investing_cash_flow': 0.0,  # Placeholder
                    'details': []
                },
                'financing_activities': {
                    'net_financing_cash_flow': 0.0,  # Placeholder
                    'details': []
                },
                'summary': {
                    'net_change_in_cash': float(operating_cash_flow),
                    'beginning_cash_balance': 0.0,  # Would need to track this
                    'ending_cash_balance': float(operating_cash_flow)
                },
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'currency': 'USD',
                    'format': format_type
                }
            }
            
            return self._format_report(cash_flow_report, format_type)
            
        except Exception as e:
            logger.error(f"Error generating cash flow report: {str(e)}")
            raise
    
    def generate_balance_sheet(
        self, 
        as_of_date: date,
        format_type: str = ReportFormat.JSON
    ) -> Dict[str, Any]:
        """Generate Balance Sheet (simplified version)."""
        try:
            with self.db.get_connection() as conn:
                # Assets (simplified - cash and receivables)
                cash_query = """
                    SELECT SUM(
                        CASE 
                            WHEN order_date <= ? THEN amount 
                            ELSE 0 
                        END
                    ) - SUM(
                        CASE 
                            WHEN cost_date <= ? THEN amount 
                            ELSE 0 
                        END
                    ) as cash_balance
                    FROM sales_orders, costs
                """
                
                # This is a simplified calculation - in reality you'd need proper cash tracking
                assets_data = pd.read_sql_query(
                    cash_query,
                    conn,
                    params=[as_of_date.isoformat(), as_of_date.isoformat()]
                )
            
            cash_balance = float(assets_data['cash_balance'].iloc[0]) if not assets_data.empty else 0
            
            balance_sheet = {
                'report_type': ReportType.BALANCE_SHEET,
                'as_of_date': as_of_date.isoformat(),
                'assets': {
                    'current_assets': {
                        'cash_and_equivalents': cash_balance,
                        'accounts_receivable': 0.0,  # Placeholder
                        'inventory': 0.0,  # Placeholder
                        'total_current_assets': cash_balance
                    },
                    'non_current_assets': {
                        'property_plant_equipment': 0.0,  # Placeholder
                        'intangible_assets': 0.0,  # Placeholder
                        'total_non_current_assets': 0.0
                    },
                    'total_assets': cash_balance
                },
                'liabilities': {
                    'current_liabilities': {
                        'accounts_payable': 0.0,  # Placeholder
                        'short_term_debt': 0.0,  # Placeholder
                        'total_current_liabilities': 0.0
                    },
                    'non_current_liabilities': {
                        'long_term_debt': 0.0,  # Placeholder
                        'total_non_current_liabilities': 0.0
                    },
                    'total_liabilities': 0.0
                },
                'equity': {
                    'retained_earnings': cash_balance,  # Simplified
                    'total_equity': cash_balance
                },
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'currency': 'USD',
                    'format': format_type
                }
            }
            
            return self._format_report(balance_sheet, format_type)
            
        except Exception as e:
            logger.error(f"Error generating balance sheet: {str(e)}")
            raise
    
    def generate_executive_summary(
        self, 
        start_date: date, 
        end_date: date,
        format_type: str = ReportFormat.JSON
    ) -> Dict[str, Any]:
        """Generate executive summary report."""
        try:
            # Get data from other reports
            pl_report = self.generate_profit_loss_report(start_date, end_date, ReportFormat.JSON)
            cf_report = self.generate_cash_flow_report(start_date, end_date, ReportFormat.JSON)
            
            # Extract key metrics
            total_revenue = pl_report['revenue']['total_revenue']
            total_costs = pl_report['costs']['total_costs']
            gross_profit = pl_report['profitability']['gross_profit']
            gross_margin = pl_report['profitability']['gross_margin_percentage']
            operating_cash_flow = cf_report['operating_activities']['net_operating_cash_flow']
            
            # Calculate period metrics
            days_in_period = (end_date - start_date).days + 1
            daily_revenue = total_revenue / days_in_period if days_in_period > 0 else 0
            
            executive_summary = {
                'report_type': ReportType.EXECUTIVE_SUMMARY,
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'days': days_in_period
                },
                'key_metrics': {
                    'total_revenue': total_revenue,
                    'total_costs': total_costs,
                    'gross_profit': gross_profit,
                    'gross_margin_percentage': gross_margin,
                    'operating_cash_flow': operating_cash_flow,
                    'daily_average_revenue': daily_revenue
                },
                'performance_indicators': {
                    'revenue_growth': 0.0,  # Would need historical comparison
                    'cost_efficiency': (total_costs / total_revenue * 100) if total_revenue > 0 else 0,
                    'cash_conversion': (operating_cash_flow / gross_profit * 100) if gross_profit > 0 else 0
                },
                'insights': self._generate_insights(total_revenue, total_costs, gross_margin),
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'currency': 'USD',
                    'format': format_type
                }
            }
            
            return self._format_report(executive_summary, format_type)
            
        except Exception as e:
            logger.error(f"Error generating executive summary: {str(e)}")
            raise
    
    def create_visualization(
        self, 
        report_data: Dict[str, Any], 
        chart_type: str = "revenue_trend"
    ) -> go.Figure:
        """Create visualization for report data."""
        try:
            if chart_type == "revenue_trend" and 'revenue' in report_data:
                revenue_data = report_data['revenue'].get('by_date', [])
                if revenue_data:
                    df = pd.DataFrame(revenue_data)
                    fig = px.line(
                        df, 
                        x='date', 
                        y='revenue',
                        title='Revenue Trend',
                        labels={'revenue': 'Revenue ($)', 'date': 'Date'}
                    )
                    return fig
            
            elif chart_type == "cost_breakdown" and 'costs' in report_data:
                cost_by_category = report_data['costs'].get('by_category', {})
                if cost_by_category:
                    fig = px.pie(
                        values=list(cost_by_category.values()),
                        names=list(cost_by_category.keys()),
                        title='Cost Breakdown by Category'
                    )
                    return fig
            
            elif chart_type == "cash_flow" and 'operating_activities' in report_data:
                cf_data = report_data['operating_activities'].get('daily_cash_flow', [])
                if cf_data:
                    df = pd.DataFrame(cf_data)
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=df['date'],
                        y=df['amount'],
                        mode='lines+markers',
                        name='Daily Cash Flow',
                        line=dict(color='blue')
                    ))
                    fig.add_trace(go.Scatter(
                        x=df['date'],
                        y=df['cumulative'],
                        mode='lines',
                        name='Cumulative Cash Flow',
                        line=dict(color='green')
                    ))
                    fig.update_layout(
                        title='Cash Flow Analysis',
                        xaxis_title='Date',
                        yaxis_title='Amount ($)'
                    )
                    return fig
            
            # Default empty chart
            fig = go.Figure()
            fig.add_annotation(
                text="No data available for visualization",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle'
            )
            return fig
            
        except Exception as e:
            logger.error(f"Error creating visualization: {str(e)}")
            # Return empty figure on error
            return go.Figure()
    
    def _format_report(self, report_data: Dict[str, Any], format_type: str) -> Dict[str, Any]:
        """Format report data according to specified format."""
        if format_type == ReportFormat.JSON:
            return report_data
        
        elif format_type == ReportFormat.CSV:
            # Convert to CSV-friendly format
            csv_data = self._flatten_for_csv(report_data)
            return {
                'data': csv_data,
                'format': 'csv',
                'metadata': report_data.get('metadata', {})
            }
        
        elif format_type == ReportFormat.EXCEL:
            # Prepare for Excel export
            return {
                'sheets': self._prepare_excel_sheets(report_data),
                'format': 'excel',
                'metadata': report_data.get('metadata', {})
            }
        
        else:
            return report_data
    
    def _flatten_for_csv(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Flatten nested report data for CSV export."""
        flattened = []
        
        def flatten_dict(d, parent_key='', sep='_'):
            items = []
            for k, v in d.items():
                new_key = f"{parent_key}{sep}{k}" if parent_key else k
                if isinstance(v, dict):
                    items.extend(flatten_dict(v, new_key, sep=sep).items())
                elif isinstance(v, list) and v and isinstance(v[0], dict):
                    # Handle list of dictionaries
                    for i, item in enumerate(v):
                        items.extend(flatten_dict(item, f"{new_key}_{i}", sep=sep).items())
                else:
                    items.append((new_key, v))
            return dict(items)
        
        flattened_data = flatten_dict(data)
        return [flattened_data]
    
    def _prepare_excel_sheets(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare data for Excel export with multiple sheets."""
        sheets = {}
        
        if 'revenue' in data:
            sheets['Revenue'] = data['revenue']
        
        if 'costs' in data:
            sheets['Costs'] = data['costs']
        
        if 'profitability' in data:
            sheets['Profitability'] = data['profitability']
        
        if 'operating_activities' in data:
            sheets['Cash Flow'] = data['operating_activities']
        
        return sheets
    
    def _generate_insights(
        self, 
        revenue: float, 
        costs: float, 
        margin: float
    ) -> List[str]:
        """Generate business insights based on financial data."""
        insights = []
        
        if margin > 30:
            insights.append("Excellent profit margins indicate strong pricing power and cost control.")
        elif margin > 15:
            insights.append("Good profit margins with room for optimization.")
        elif margin > 0:
            insights.append("Positive margins but consider cost reduction strategies.")
        else:
            insights.append("Negative margins require immediate attention to cost structure.")
        
        cost_ratio = (costs / revenue * 100) if revenue > 0 else 100
        if cost_ratio > 80:
            insights.append("High cost ratio suggests need for operational efficiency improvements.")
        elif cost_ratio < 50:
            insights.append("Efficient cost structure provides competitive advantage.")
        
        if revenue > 0:
            insights.append(f"Revenue generation is active with ${revenue:,.2f} in the period.")
        else:
            insights.append("No revenue recorded in this period - focus on sales activities.")
        
        return insights
