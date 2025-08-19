import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# New clean architecture imports
from src.container import get_container
from src.ui.auth import AuthComponents
from src.ui.components.components import UIComponents
from src.ui.forms import FormComponents
from src.security import AuditLogger, AuditAction
from src.models.cost import CostModel, RecurringCostModel
from src.utils.business_rules import BusinessRuleValidator
from src.utils.date_utils import DateUtils

# Legacy imports for backward compatibility
from src.utils.theme_manager import apply_theme
from src.services.settings_service import get_setting
from src.services.error_handler import handle_error
import traceback

if not AuthComponents.is_authenticated():
    st.stop()
# Get services from container
container = get_container()
cost_service = container.get_cost_service()
analytics_service = container.get_analytics_service()
audit_logger = AuditLogger(container.get_db_connection())
business_validator = BusinessRuleValidator()

# Get current user for audit logging
current_user = st.session_state.get("user", {}).get("email", "unknown")

# Apply theme
apply_theme()

# Page title and description
st.title("💸 Costs Management")
st.markdown(
    "Manage your business costs and expenses with detailed tracking and analysis."
)

# Initialize date range
try:
    # Get date range for filtering
    current_year = date.today().year
    year_start, year_end = DateUtils.get_year_range(current_year)
    today = date.today()
    start_date = year_start

    # Initialize filter variables
    category_filter = "All"
    currency_filter = "All"
    date_range = f"{year_start} to {year_end}"

    # Load costs using service layer
    costs_df = cost_service.get_costs_by_date_range(year_start, year_end)
    # Normalize to DataFrame if service returned a list (dev fallback)
    if isinstance(costs_df, list):
        costs_df = pd.DataFrame(costs_df)
    recurring_costs_df = cost_service.get_recurring_costs()

    # Ensure required columns exist for downstream processing
    if "category" not in costs_df.columns:
        costs_df["category"] = "Unknown"
    if "amount" not in costs_df.columns:
        costs_df["amount"] = 0

    # Log data access
    audit_logger.log_data_access(
        user_id=current_user,
        resource="costs_data",
        filters={"year": current_year},
    )

except Exception as e:
    handle_error(e, "Failed to load cost data")
    st.stop()

# Cost Entry Section
UIComponents.section_header("Add New Cost", "Record one-time or recurring expenses")

# Use new form component for cost entry
with st.expander("➕ Add New Cost", expanded=False):
    cost_form_data = FormComponents.cost_entry_form()

    if cost_form_data:
        try:
            # Validate business rules
            validation_result = business_validator.validate_cost_entry(
                cost_form_data["amount"],
                cost_form_data.get("category", "Unknown"),
                cost_form_data.get("currency", "USD"),
            )

            if not validation_result["valid"]:
                st.error(f"Validation failed: {validation_result['message']}")
            else:
                # Create cost model
                cost_model = CostModel(
                    name=cost_form_data["name"],
                    category=cost_form_data.get("category", "Unknown"),
                    amount=cost_form_data["amount"],
                    currency=cost_form_data.get("currency", "USD"),
                    date=cost_form_data["date"],
                    description=cost_form_data.get("description", ""),
                    is_recurring=cost_form_data.get("is_recurring", False),
                )

                # Save using service
                success = cost_service.create_cost(cost_model)

                if success:
                    st.success("Cost added successfully!")

                    # Log the operation
                    audit_logger.log_financial_operation(
                        user_id=current_user,
                        action=AuditAction.CREATE,
                        entity_type="cost",
                        entity_id=cost_model.id,
                        amount=cost_model.amount,
                        currency=cost_model.currency,
                        details={
                            "category": cost_model.category,
                            "name": cost_model.name,
                        },
                    )

                    st.rerun()
                else:
                    st.error("Failed to add cost. Please try again.")

        except Exception as e:
            handle_error(e, "Failed to add cost")

st.divider()

# Cost Analytics Section
UIComponents.section_header("Cost Analytics", "Overview of expenses and trends")

# Get cost analytics using service
cost_analytics = analytics_service.get_cost_analytics(
    start_date=start_date,
    end_date=today,
    category=category_filter if category_filter != "All" else None,
    currency=currency_filter if currency_filter != "All" else None,
)

if cost_analytics:
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        UIComponents.currency_metric(
            "Total Costs", cost_analytics.total_costs, "USD"
        )

    with col2:
        UIComponents.currency_metric(
            "Average Daily", cost_analytics.avg_daily_cost, "USD"
        )

    with col3:
        UIComponents.metric_card(
            "Total Transactions", str(cost_analytics.transaction_count), "expenses"
        )

    with col4:
        UIComponents.currency_metric(
            "Largest Expense", cost_analytics.max_cost, "USD"
        )

    st.divider()

    # Cost Charts Section
    UIComponents.section_header(
        "Cost Analytics Charts", "Visual breakdown and trends"
    )

    # Get cost breakdown data
    cost_breakdown = cost_service.get_cost_breakdown(
        start_date=start_date,
        end_date=today,
        category=category_filter if category_filter != "All" else None,
    )

    # Normalize to DataFrame if service returned a list of dicts (dev mode fallback)
    if isinstance(cost_breakdown, list):
        cost_breakdown = pd.DataFrame(cost_breakdown)

    if cost_breakdown:
        col1, col2 = st.columns(2)

        with col1:
            UIComponents.section_header("📊 Costs by Category")

            try:
                # Use analytics service for category analysis
                category_analysis = (
                    analytics_service.get_cost_breakdown_by_category(
                        start_date, today
                    )
                )

                if category_analysis:
                    fig_pie = UIComponents.create_pie_chart(
                        values=[item.get("total_amount", 0) for item in category_analysis],
                        labels=[item.get("category", "Unknown") for item in category_analysis],
                        title="Cost Distribution by Category",
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)
                else:
                    # Fallback to basic grouping
                    if "category" in cost_breakdown.columns:
                        category_costs = (
                            cost_breakdown.groupby("category")["amount"]
                            .sum()
                            .sort_values(ascending=False)
                        )
                    else:
                        category_costs = pd.Series([])
                    fig_pie = UIComponents.create_pie_chart(
                        values=category_costs.values,
                        labels=category_costs.index,
                        title="Cost Distribution by Category",
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)

            except Exception as e:
                handle_error(e, "Failed to create category chart")

        with col2:
            UIComponents.section_header("📈 Monthly Cost Trend")

            try:
                # Use analytics service for trend analysis
                monthly_trends = analytics_service.get_monthly_cost_trends(
                    start_date, today
                )

                if monthly_trends:
                    fig_line = UIComponents.create_line_chart(
                        x_data=[trend.get("month", "Unknown") for trend in monthly_trends],
                        y_data=[trend.get("total_costs", 0) for trend in monthly_trends],
                        title="Monthly Cost Trend",
                        x_label="Month",
                        y_label="Cost (USD)",
                    )
                    st.plotly_chart(fig_line, use_container_width=True)
                else:
                    # Fallback to basic trend calculation
                    cost_breakdown["date"] = pd.to_datetime(cost_breakdown["date"])
                    cost_breakdown["month"] = cost_breakdown["date"].dt.to_period(
                        "M"
                    )
                    monthly_costs = (
                        cost_breakdown.groupby("month")["amount"]
                        .sum()
                        .reset_index()
                    )
                    monthly_costs["month"] = monthly_costs["month"].astype(str)

                    fig_line = UIComponents.create_line_chart(
                        x_data=monthly_costs["month"].tolist(),
                        y_data=monthly_costs["amount"].tolist(),
                        title="Monthly Cost Trend",
                        x_label="Month",
                        y_label="Cost (USD)",
                    )
                    st.plotly_chart(fig_line, use_container_width=True)

            except Exception as e:
                handle_error(e, "Failed to create trend chart")

    st.divider()

    # Recent Costs Table
    UIComponents.section_header("Recent Costs", "Latest cost entries")

    # Get recent costs using service
    recent_costs = cost_service.get_recent_costs(limit=10)

    if recent_costs:
        # Convert to display format
        cost_data = []
        for cost in recent_costs:
            # Handle both Cost objects and dictionaries
            if isinstance(cost, dict):
                cost_data.append(
                    {
                        "Date": cost.get("date", ""),
                        "Description": cost.get("description", ""),
                        "Category": cost.get("category", "Unknown"),
                        "Amount": f"{cost.get('currency', 'USD')} {float(cost.get('amount', 0)):,.2f}",
                        "Notes": cost.get("notes", ""),
                    }
                )
            else:
                # Cost object
                cost_data.append(
                    {
                        "Date": cost.date.strftime("%Y-%m-%d"),
                        "Description": cost.description,
                        "Category": cost.category,
                        "Amount": f"{cost.currency} {cost.amount:,.2f}",
                        "Notes": cost.notes or "",
                    }
                )

        UIComponents.data_table(cost_data, "Recent cost transactions")
    else:
        UIComponents.empty_state(
            "No Recent Costs", "No cost entries found for the selected period."
        )

else:
    UIComponents.empty_state(
        "No Cost Data",
        f"No cost data available for {date_range.lower()}. Add some costs to see analytics.",
    )
