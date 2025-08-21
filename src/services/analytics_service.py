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
from .error_handler import get_error_handler
from ..analytics.compare_utils import make_daily_index


class AnalyticsService:
    """Service for analytics and business intelligence operations."""

    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection
        self.error_handler = get_error_handler()

    # --- Development fallback for cost analytics ---
    def get_cost_analytics(self, start_date=None, end_date=None, category=None, currency=None):
        """
        Fallback implementation for development.
        Returns a simple object with zero values to avoid crashes.
        """
        class CostAnalytics:
            total_costs = 0
            avg_daily_cost = 0
            transaction_count = 0
            max_cost = 0
        return CostAnalytics()

    # --- Development fallback for cost breakdown by category ---
    def get_cost_breakdown_by_category(self, start_date=None, end_date=None):
        # Return empty list for development (no data yet)
        return []

    # --- Development fallback for monthly cost trends ---
    def get_monthly_cost_trends(self, start_date=None, end_date=None):
        # Return empty list for development (no data yet)
        return []

    # --- Development fallback for revenue analytics ---
    def get_revenue_analytics(self, start_date=None, end_date=None, category=None, currency=None):
        """
        Fallback implementation for development.
        """
        class RevenueAnalytics:
            total_revenue = 0
            avg_daily_revenue = 0
            transaction_count = 0
            max_revenue = 0
        return RevenueAnalytics()

    # --- Development fallback for cash flow analytics ---
    def get_cash_flow_analytics(self, start_date=None, end_date=None, category=None, currency=None):
        """
        Fallback implementation for development.
        """
        class CashFlowAnalytics:
            net_cash_flow = 0
            total_revenue = 0
            total_costs = 0
        return CashFlowAnalytics()

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

            try:
                results = conn.execute(
                    query, (start_date.isoformat(), end_date.isoformat())
                ).fetchall()
            except Exception:
                # Dev fallback – column/table not available
                return {}

            return {row.get("category", "Unknown"): Decimal(str(row["total"])) for row in results}

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

    # --- New: Airtable-backed analytics ---
    def bookings_by_date(self, start_date: date, end_date: date) -> pd.DataFrame:
        """Aggregate bookings by booking_date with sums and counts.

        Returns a DataFrame with columns: date, total_amount, total_guests, bookings_count
        """
        try:
            with self.db.get_connection() as conn:
                query = (
                    """
                    SELECT booking_date AS date,
                           SUM(amount)        AS total_amount,
                           SUM(guests)        AS total_guests,
                           COUNT(*)           AS bookings_count
                      FROM bookings
                     WHERE booking_date BETWEEN ? AND ?
                  GROUP BY booking_date
                  ORDER BY booking_date
                    """
                )
                rows = conn.execute(
                    query, (start_date.isoformat(), end_date.isoformat())
                ).fetchall()
                data = [
                    {
                        "date": r["date"],
                        "total_amount": float(r["total_amount"] or 0.0),
                        "total_guests": int(r["total_guests"] or 0),
                        "bookings_count": int(r["bookings_count"] or 0),
                    }
                    for r in rows
                ]
                return pd.DataFrame(data)
        except Exception as e:
            # Consistent error handling
            self.error_handler.handle_database_error(
                e, operation="bookings_by_date", affected_table="bookings"
            )
            return pd.DataFrame(columns=["date", "total_amount", "total_guests", "bookings_count"])

    def bookings_by_date_daily(self, start_date: date, end_date: date) -> pd.DataFrame:
        """Return daily-indexed bookings data with zero-filled gaps.

        Columns: date, total_amount, total_guests, bookings_count.
        Ensures a continuous daily range between start_date and end_date.
        """
        try:
            df = self.bookings_by_date(start_date, end_date)
            # Zero-fill missing days across standard booking metrics
            daily = make_daily_index(
                df,
                start=start_date,
                end=end_date,
                value_cols=["total_amount", "total_guests", "bookings_count"],
            )
            return daily
        except Exception as e:
            self.error_handler.handle_database_error(
                e, operation="bookings_by_date_daily", affected_table="bookings"
            )
            return pd.DataFrame(columns=["date", "total_amount", "total_guests", "bookings_count"])

    def bookings_summary(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """Return total sales amount, bookings count, and average booking amount for date range.

        Sums are based on the `bookings` table and filtered by `booking_date`.
        """
        try:
            with self.db.get_connection() as conn:
                row = conn.execute(
                    """
                    SELECT SUM(amount)   AS total_amount,
                           COUNT(*)      AS bookings_count,
                           AVG(amount)   AS avg_amount
                      FROM bookings
                     WHERE booking_date BETWEEN ? AND ?
                    """,
                    (start_date.isoformat(), end_date.isoformat()),
                ).fetchone()

                total = float(row["total_amount"] or 0.0)
                count = int(row["bookings_count"] or 0)
                avg = float(row["avg_amount"] or 0.0)
                return {
                    "total_amount": total,
                    "bookings_count": count,
                    "avg_booking_amount": avg,
                }
        except Exception as e:
            self.error_handler.handle_database_error(
                e, operation="bookings_summary", affected_table="bookings"
            )
            return {"total_amount": 0.0, "bookings_count": 0, "avg_booking_amount": 0.0}

    def bookings_by_month(self, start_date: date, end_date: date) -> pd.DataFrame:
        """Return monthly aggregated bookings data.

        Columns: month (YYYY-MM), total_amount, total_guests, bookings_count
        """
        try:
            with self.db.get_connection() as conn:
                rows = conn.execute(
                    """
                    SELECT SUBSTR(booking_date, 1, 7) AS month,
                           SUM(amount)                 AS total_amount,
                           SUM(guests)                 AS total_guests,
                           COUNT(*)                    AS bookings_count
                      FROM bookings
                     WHERE booking_date BETWEEN ? AND ?
                  GROUP BY SUBSTR(booking_date, 1, 7)
                  ORDER BY month
                    """,
                    (start_date.isoformat(), end_date.isoformat()),
                ).fetchall()

                data = [
                    {
                        "month": r["month"],
                        "total_amount": float(r["total_amount"] or 0.0),
                        "total_guests": int(r["total_guests"] or 0),
                        "bookings_count": int(r["bookings_count"] or 0),
                    }
                    for r in rows
                ]
                return pd.DataFrame(data)
        except Exception as e:
            self.error_handler.handle_database_error(
                e, operation="bookings_by_month", affected_table="bookings"
            )
            return pd.DataFrame(columns=["month", "total_amount", "total_guests", "bookings_count"])

    def cash_ledger_by_date(self, start_date: date, end_date: date) -> pd.DataFrame:
        """Aggregate true cash flow from cash_ledger entries by date.

        Returns a DataFrame with columns: date, inflow, outflow (outflow is positive values of absolute outflows).
        """
        try:
            with self.db.get_connection() as conn:
                rows = conn.execute(
                    """
                    SELECT entry_date AS date,
                           SUM(CASE WHEN amount >= 0 THEN amount ELSE 0 END)           AS inflow,
                           SUM(CASE WHEN amount  < 0 THEN -amount ELSE 0 END)          AS outflow
                      FROM cash_ledger
                     WHERE entry_date BETWEEN ? AND ?
                  GROUP BY entry_date
                  ORDER BY entry_date
                    """,
                    (start_date.isoformat(), end_date.isoformat()),
                ).fetchall()

                data = [
                    {
                        "date": r["date"],
                        "inflow": float(r["inflow"] or 0.0),
                        "outflow": float(r["outflow"] or 0.0),
                    }
                    for r in rows
                ]
                return pd.DataFrame(data)
        except Exception as e:
            self.error_handler.handle_database_error(
                e, operation="cash_ledger_by_date", affected_table="cash_ledger"
            )
            return pd.DataFrame(columns=["date", "inflow", "outflow"])

    def cash_ledger_summary(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """Summary of cash ledger within range: inflow, outflow, net, entries."""
        try:
            with self.db.get_connection() as conn:
                row = conn.execute(
                    """
                    SELECT SUM(CASE WHEN amount >= 0 THEN amount ELSE 0 END)  AS inflow,
                           SUM(CASE WHEN amount  < 0 THEN -amount ELSE 0 END) AS outflow,
                           SUM(amount)                                          AS net,
                           COUNT(*)                                             AS entries
                      FROM cash_ledger
                     WHERE entry_date BETWEEN ? AND ?
                    """,
                    (start_date.isoformat(), end_date.isoformat()),
                ).fetchone()

                inflow = float(row["inflow"] or 0.0)
                outflow = float(row["outflow"] or 0.0)
                net = float(row["net"] or 0.0)
                entries = int(row["entries"] or 0)
                return {"inflow": inflow, "outflow": outflow, "net": net, "entries": entries}
        except Exception as e:
            self.error_handler.handle_database_error(
                e, operation="cash_ledger_summary", affected_table="cash_ledger"
            )
            return {"inflow": 0.0, "outflow": 0.0, "net": 0.0, "entries": 0}

    def leads_summary(self, start_date: date, end_date: date) -> Dict[str, int]:
        """Return total leads, MQL count, SQL count in date range (created_at)."""
        try:
            with self.db.get_connection() as conn:
                total_q = "SELECT COUNT(*) AS c FROM leads WHERE created_at BETWEEN ? AND ?"
                mql_q = (
                    "SELECT COUNT(*) AS c FROM leads WHERE created_at BETWEEN ? AND ? AND COALESCE(mql_yes, 0) = 1"
                )
                sql_q = (
                    "SELECT COUNT(*) AS c FROM leads WHERE created_at BETWEEN ? AND ? AND COALESCE(sql_yes, 0) = 1"
                )
                params = (start_date.isoformat(), end_date.isoformat())
                total = conn.execute(total_q, params).fetchone()["c"]
                mql = conn.execute(mql_q, params).fetchone()["c"]
                sql = conn.execute(sql_q, params).fetchone()["c"]
                return {
                    "total_leads": int(total or 0),
                    "mql_count": int(mql or 0),
                    "sql_count": int(sql or 0),
                }
        except Exception as e:
            self.error_handler.handle_database_error(
                e, operation="leads_summary", affected_table="leads"
            )
            return {"total_leads": 0, "mql_count": 0, "sql_count": 0}

    def leads_by_utm(self, start_date: date, end_date: date) -> Dict[str, List[Dict[str, Any]]]:
        """Return counts split by utm_source and utm_campaign for leads in date range."""
        try:
            with self.db.get_connection() as conn:
                params = (start_date.isoformat(), end_date.isoformat())
                by_source_rows = conn.execute(
                    """
                    SELECT COALESCE(NULLIF(utm_source, ''), 'Unknown') AS utm_source,
                           COUNT(*) AS cnt
                      FROM leads
                     WHERE created_at BETWEEN ? AND ?
                  GROUP BY utm_source
                  ORDER BY cnt DESC
                    """,
                    params,
                ).fetchall()
                by_campaign_rows = conn.execute(
                    """
                    SELECT COALESCE(NULLIF(utm_campaign, ''), 'Unknown') AS utm_campaign,
                           COUNT(*) AS cnt
                      FROM leads
                     WHERE created_at BETWEEN ? AND ?
                  GROUP BY utm_campaign
                  ORDER BY cnt DESC
                    """,
                    params,
                ).fetchall()

                by_source = [
                    {"utm_source": r["utm_source"], "count": int(r["cnt"] or 0)}
                    for r in by_source_rows
                ]
                by_campaign = [
                    {"utm_campaign": r["utm_campaign"], "count": int(r["cnt"] or 0)}
                    for r in by_campaign_rows
                ]

                return {"by_source": by_source, "by_campaign": by_campaign}
        except Exception as e:
            self.error_handler.handle_database_error(
                e, operation="leads_by_utm", affected_table="leads"
            )
            return {"by_source": [], "by_campaign": []}

    def lead_to_booking_lag(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Compute lead→booking lag in days for bookings within [start_date, end_date] (inclusive).

        Inputs are ISO strings YYYY-MM-DD. Returns dict with summary, lag_table, utm_breakdown, monthly_cohorts.
        Matching rules:
        - Only consider leads with created_at <= booking_date
        - For each booking, match most recent qualifying lead for same email
        - If multiple same-day leads exist, pick latest created_at (ORDER BY created_at DESC LIMIT 1)
        - Bookings without a match are excluded from lag stats but counted as unmatched
        """
        def _parse_date_safe(v: Any) -> Optional[pd.Timestamp]:
            try:
                if v is None or v == "":
                    return None
                ts = pd.to_datetime(v, errors="coerce")
                return ts if pd.notnull(ts) else None
            except Exception:
                return None

        def _median(values: List[int]) -> float:
            if not values:
                return 0.0
            s = sorted(values)
            n = len(s)
            mid = n // 2
            if n % 2 == 1:
                return float(s[mid])
            return (s[mid - 1] + s[mid]) / 2.0

        def _p90(values: List[int]) -> float:
            if not values:
                return 0.0
            s = sorted(values)
            # Nearest-rank method
            import math
            k = max(1, math.ceil(0.9 * len(s))) - 1
            return float(s[k])

        try:
            with self.db.get_connection() as conn:
                # Indices to keep things snappy (portable IF NOT EXISTS)
                try:
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_leads_email_created ON leads(email, created_at)")
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_bookings_booking_date ON bookings(booking_date)")
                except Exception:
                    # Non-fatal; continue without indices
                    pass

                # Step 1: bookings in range with email
                bookings_rows = conn.execute(
                    """
                    SELECT booking_id, booking_date, amount, guests, email
                      FROM bookings
                     WHERE COALESCE(email, '') <> ''
                       AND booking_date BETWEEN ? AND ?
                  ORDER BY booking_date DESC
                    """,
                    (start_date, end_date),
                ).fetchall()

                total_in_range = len(bookings_rows)
                lag_records: List[Dict[str, Any]] = []

                # Step 2: find most recent lead per booking
                lead_query = (
                    """
                    SELECT created_at, utm_source, utm_medium, utm_campaign
                      FROM leads
                     WHERE email = ?
                       AND COALESCE(created_at, '') <> ''
                       AND created_at <= ?
                  ORDER BY created_at DESC
                     LIMIT 1
                    """
                )

                for b in bookings_rows:
                    try:
                        email = b["email"]
                        b_date = _parse_date_safe(b["booking_date"])
                        if not email or b_date is None:
                            continue

                        lead_row = conn.execute(lead_query, (email, b_date.date().isoformat())).fetchone()
                        if not lead_row:
                            continue

                        lead_dt = _parse_date_safe(lead_row["created_at"])
                        if lead_dt is None:
                            continue

                        # Step 3: compute lag in days (booking_date - lead_created_at)
                        lag_days = int((b_date.normalize() - lead_dt.normalize()).days)
                        if lag_days < 0:
                            # Safety guard; skip inconsistent data
                            continue

                        lag_records.append(
                            {
                                "booking_id": b["booking_id"],
                                "booking_date": b_date.date().isoformat(),
                                "amount": float(b["amount"] or 0.0),
                                "guests": int(b["guests"] or 0),
                                "email": email,
                                "lead_created_at": lead_dt.to_pydatetime().isoformat(timespec="seconds"),
                                "utm_source": lead_row["utm_source"],
                                "utm_medium": lead_row["utm_medium"],
                                "utm_campaign": lead_row["utm_campaign"],
                                "lag_days": lag_days,
                            }
                        )
                    except Exception:
                        # Skip malformed rows, continue
                        continue

                # Step 4: aggregates
                lags = [r["lag_days"] for r in lag_records]
                matched = len(lag_records)
                unmatched = max(0, total_in_range - matched)

                avg_days = float(sum(lags) / matched) if matched else 0.0
                median_days = _median(lags)
                p90_days = _p90(lags)

                # UTM breakdowns (matched only)
                from collections import defaultdict

                src_map: Dict[str, List[int]] = defaultdict(list)
                camp_map: Dict[str, List[int]] = defaultdict(list)
                for r in lag_records:
                    src = r.get("utm_source") or "Unknown"
                    camp = r.get("utm_campaign") or "Unknown"
                    src_map[src].append(r["lag_days"])
                    camp_map[camp].append(r["lag_days"])

                by_source = [
                    {
                        "utm_source": k,
                        "count": len(v),
                        "avg_days": float(sum(v) / len(v)) if v else 0.0,
                        "median_days": _median(v),
                    }
                    for k, v in sorted(src_map.items(), key=lambda kv: -len(kv[1]))
                ]
                by_campaign = [
                    {
                        "utm_campaign": k,
                        "count": len(v),
                        "avg_days": float(sum(v) / len(v)) if v else 0.0,
                        "median_days": _median(v),
                    }
                    for k, v in sorted(camp_map.items(), key=lambda kv: -len(kv[1]))
                ]

                # Monthly cohorts by booking month
                cohort_map: Dict[str, List[int]] = defaultdict(list)
                for r in lag_records:
                    m = (r["booking_date"])[:7]
                    cohort_map[m].append(r["lag_days"])
                monthly_cohorts = [
                    {
                        "month": m,
                        "count": len(vals),
                        "avg_days": float(sum(vals) / len(vals)) if vals else 0.0,
                        "median_days": _median(vals),
                    }
                    for m, vals in sorted(cohort_map.items())
                ]

                # Step 5: assemble response
                lag_table_sorted = sorted(
                    lag_records, key=lambda r: r.get("booking_date", ""), reverse=True
                )
                top50 = lag_table_sorted[:50]

                return {
                    "summary": {
                        "matched_bookings": matched,
                        "unmatched_bookings": unmatched,
                        "avg_days": avg_days,
                        "median_days": median_days,
                        "p90_days": p90_days,
                    },
                    "lag_table": top50,
                    "utm_breakdown": {"by_source": by_source, "by_campaign": by_campaign},
                    "monthly_cohorts": monthly_cohorts,
                }
        except Exception as e:
            self.error_handler.handle_database_error(
                e, operation="lead_to_booking_lag", affected_table="bookings/leads"
            )
            return {
                "summary": {
                    "matched_bookings": 0,
                    "unmatched_bookings": 0,
                    "avg_days": 0.0,
                    "median_days": 0.0,
                    "p90_days": 0.0,
                },
                "lag_table": [],
                "utm_breakdown": {"by_source": [], "by_campaign": []},
                "monthly_cohorts": [],
            }

    def get_daily_trends(self, start_date, end_date):
        """
        Development fallback method for daily trends.
        Returns an empty list if trend data is not available.
        """
        return []

    def get_yoy_comparison(self, start_date, end_date):
        """Development fallback for year-over-year comparison."""
        return {}

    def get_cost_trends(self, start_date, end_date):
        """Development fallback for cost trends."""
        return []

    def get_revenue_trends(self, start_date, end_date):
        """Development fallback for revenue trends."""
        return []

    def get_cost_breakdown(self, start_date=None, end_date=None):
        """
        Development fallback for cost breakdown.
        Returns an empty list when not yet implemented.
        """
        return []

    def get_revenue_breakdown(self, start_date=None, end_date=None):
        """
        Development fallback for revenue breakdown.
        Returns an empty list when not yet implemented.
        """
        return []
