"""
Analytics service for business metrics and data analysis.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
from ..models.analytics import CashFlowMetrics, BusinessMetrics, FXRateData
from ..repositories.base import DatabaseConnection
from ..utils.date_utils import DateUtils
from ..utils.currency_utils import CurrencyUtils


class AnalyticsService:
    """Service for analytics and business intelligence operations."""

    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection

    def get_cash_flow_metrics(
        self, start_date: date, end_date: date
    ) -> CashFlowMetrics:
        """Calculate cash flow metrics for date range."""
        with self.db.get_connection() as conn:
            # Get sales data
            sales_query = """
                SELECT SUM(amount_usd) as total_sales, COUNT(*) as transaction_count
                FROM sales_orders 
                WHERE date BETWEEN ? AND ?
            """
            sales_result = conn.execute(
                sales_query, (start_date.isoformat(), end_date.isoformat())
            ).fetchone()

            # Get costs data
            costs_query = """
                SELECT SUM(amount_usd) as total_costs
                FROM costs 
                WHERE date BETWEEN ? AND ?
            """
            costs_result = conn.execute(
                costs_query, (start_date.isoformat(), end_date.isoformat())
            ).fetchone()

            total_sales = Decimal(str(sales_result["total_sales"] or 0))
            total_costs = Decimal(str(costs_result["total_costs"] or 0))
            transaction_count = sales_result["transaction_count"] or 0

            # Calculate derived metrics
            net_cash_flow = total_sales - total_costs
            days = (end_date - start_date).days + 1
            avg_daily_sales = total_sales / days if days > 0 else Decimal("0")
            avg_transaction_size = (
                total_sales / transaction_count
                if transaction_count > 0
                else Decimal("0")
            )

            # Calculate growth rates (compare with previous period)
            previous_start = DateUtils.add_months(start_date, -1)
            previous_end = DateUtils.add_months(end_date, -1)

            prev_sales_result = conn.execute(
                sales_query, (previous_start.isoformat(), previous_end.isoformat())
            ).fetchone()
            prev_costs_result = conn.execute(
                costs_query, (previous_start.isoformat(), previous_end.isoformat())
            ).fetchone()

            prev_sales = Decimal(str(prev_sales_result["total_sales"] or 0))
            prev_costs = Decimal(str(prev_costs_result["total_costs"] or 0))

            sales_growth = CurrencyUtils.calculate_percentage_change(
                prev_sales, total_sales
            )
            cost_growth = CurrencyUtils.calculate_percentage_change(
                prev_costs, total_costs
            )

            return CashFlowMetrics(
                period_start=start_date,
                period_end=end_date,
                total_sales_usd=total_sales,
                total_costs_usd=total_costs,
                net_cash_flow=net_cash_flow,
                avg_daily_sales=avg_daily_sales,
                avg_transaction_size=avg_transaction_size,
                transaction_count=transaction_count,
                sales_growth_rate=sales_growth,
                cost_growth_rate=cost_growth,
            )

    def get_business_metrics(self, start_date: date, end_date: date) -> BusinessMetrics:
        """Calculate business performance metrics."""
        with self.db.get_connection() as conn:
            # This would integrate with Airtable or other CRM data
            # For now, return mock data structure
            return BusinessMetrics(
                period_start=start_date,
                period_end=end_date,
                total_leads=0,
                mql_count=0,
                sql_count=0,
                conversion_rate=Decimal("0"),
                occupancy_rate=None,
                customer_acquisition_cost=None,
                lifetime_value=None,
            )

    def get_monthly_summary(self, year: int, month: int) -> Dict[str, Any]:
        """Get comprehensive monthly summary."""
        start_date, end_date = DateUtils.get_month_range(year, month)

        # Get cash flow metrics
        cash_flow = self.get_cash_flow_metrics(start_date, end_date)

        # Get category breakdown
        category_breakdown = self._get_cost_category_breakdown(start_date, end_date)

        # Get daily trends
        daily_trends = self._get_daily_trends(start_date, end_date)

        return {
            "period": f"{year}-{month:02d}",
            "cash_flow_metrics": cash_flow,
            "category_breakdown": category_breakdown,
            "daily_trends": daily_trends,
            "summary": {
                "total_sales": cash_flow.total_sales_usd,
                "total_costs": cash_flow.total_costs_usd,
                "net_cash_flow": cash_flow.net_cash_flow,
                "profit_margin": cash_flow.profit_margin,
                "transaction_count": cash_flow.transaction_count,
            },
        }

    def _get_cost_category_breakdown(
        self, start_date: date, end_date: date
    ) -> Dict[str, Decimal]:
        """Get cost breakdown by category."""
        with self.db.get_connection() as conn:
            query = """
                SELECT category, SUM(amount_usd) as total
                FROM costs 
                WHERE date BETWEEN ? AND ?
                GROUP BY category
                ORDER BY total DESC
            """

            results = conn.execute(
                query, (start_date.isoformat(), end_date.isoformat())
            ).fetchall()

            return {row["category"]: Decimal(str(row["total"])) for row in results}

    def _get_daily_trends(
        self, start_date: date, end_date: date
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get daily sales and cost trends."""
        with self.db.get_connection() as conn:
            # Daily sales
            sales_query = """
                SELECT date, SUM(amount_usd) as amount
                FROM sales_orders 
                WHERE date BETWEEN ? AND ?
                GROUP BY date
                ORDER BY date
            """

            # Daily costs
            costs_query = """
                SELECT date, SUM(amount_usd) as amount
                FROM costs 
                WHERE date BETWEEN ? AND ?
                GROUP BY date
                ORDER BY date
            """

            sales_results = conn.execute(
                sales_query, (start_date.isoformat(), end_date.isoformat())
            ).fetchall()
            costs_results = conn.execute(
                costs_query, (start_date.isoformat(), end_date.isoformat())
            ).fetchall()

            sales_trends = [
                {"date": row["date"], "amount": float(row["amount"])}
                for row in sales_results
            ]

            costs_trends = [
                {"date": row["date"], "amount": float(row["amount"])}
                for row in costs_results
            ]

            return {"sales": sales_trends, "costs": costs_trends}

    def get_fx_rates(self, month: str) -> Optional[FXRateData]:
        """Get FX rates for a specific month."""
        with self.db.get_connection() as conn:
            query = """
                SELECT month, low_crc_usd, base_crc_usd, high_crc_usd
                FROM fx_rates 
                WHERE month = ?
            """

            result = conn.execute(query, (month,)).fetchone()

            if result:
                return FXRateData(
                    month=result["month"],
                    low_crc_usd=Decimal(str(result["low_crc_usd"])),
                    base_crc_usd=Decimal(str(result["base_crc_usd"])),
                    high_crc_usd=Decimal(str(result["high_crc_usd"])),
                )

            return None

    def get_year_over_year_comparison(self, year: int) -> Dict[str, Any]:
        """Get year-over-year comparison data."""
        current_year_start = date(year, 1, 1)
        current_year_end = date(year, 12, 31)
        previous_year_start = date(year - 1, 1, 1)
        previous_year_end = date(year - 1, 12, 31)

        current_metrics = self.get_cash_flow_metrics(
            current_year_start, current_year_end
        )
        previous_metrics = self.get_cash_flow_metrics(
            previous_year_start, previous_year_end
        )

        sales_change = CurrencyUtils.calculate_percentage_change(
            previous_metrics.total_sales_usd, current_metrics.total_sales_usd
        )

        costs_change = CurrencyUtils.calculate_percentage_change(
            previous_metrics.total_costs_usd, current_metrics.total_costs_usd
        )

        return {
            "current_year": current_metrics,
            "previous_year": previous_metrics,
            "changes": {
                "sales_change": sales_change,
                "costs_change": costs_change,
                "net_flow_change": current_metrics.net_cash_flow
                - previous_metrics.net_cash_flow,
            },
        }
