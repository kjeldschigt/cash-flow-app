"""
Comprehensive Business Rule Validation Utilities
"""

from decimal import Decimal
from datetime import date, datetime
from typing import Dict, List, Optional, Any, Tuple
from ..models.cost import CostCategory
from ..models.transaction import TransactionType


class BusinessRuleValidator:
    """Comprehensive business rule validation for financial operations"""

    def __init__(self):
        self.validation_rules = {
            "cost_limits": {
                "marketing": Decimal("50000"),  # Monthly limit
                "operations": Decimal("100000"),
                "technology": Decimal("25000"),
                "legal": Decimal("15000"),
                "finance": Decimal("10000"),
            },
            "revenue_thresholds": {
                "minimum_monthly": Decimal("10000"),
                "warning_threshold": Decimal("5000"),
            },
            "cash_flow_rules": {
                "minimum_balance": Decimal("5000"),
                "critical_balance": Decimal("1000"),
            },
        }

    def validate_cost_against_revenue(
        self,
        cost_amount: Decimal,
        category: str,
        monthly_revenue: Decimal,
        monthly_costs: Decimal,
    ) -> Dict[str, Any]:
        """
        Validate cost against revenue limits and business rules.

        Returns validation result with warnings and recommendations.
        """
        validation_result = {
            "is_valid": True,
            "warnings": [],
            "errors": [],
            "recommendations": [],
        }

        # Check category-specific limits
        category_limit = self.validation_rules["cost_limits"].get(
            category.lower(), Decimal("20000")  # Default limit
        )

        if cost_amount > category_limit:
            validation_result["warnings"].append(
                f"Cost amount ${cost_amount} exceeds category limit of ${category_limit} for {category}"
            )

        # Check cost-to-revenue ratio
        if monthly_revenue > 0:
            total_costs_after = monthly_costs + cost_amount
            cost_ratio = (total_costs_after / monthly_revenue) * 100

            if cost_ratio > 80:
                validation_result["errors"].append(
                    f"Total costs would be {cost_ratio:.1f}% of revenue, exceeding 80% threshold"
                )
                validation_result["is_valid"] = False
            elif cost_ratio > 60:
                validation_result["warnings"].append(
                    f"Total costs would be {cost_ratio:.1f}% of revenue, approaching high threshold"
                )

        # Revenue adequacy check
        min_revenue = self.validation_rules["revenue_thresholds"]["minimum_monthly"]
        if monthly_revenue < min_revenue:
            validation_result["warnings"].append(
                f"Monthly revenue ${monthly_revenue} is below recommended minimum of ${min_revenue}"
            )

        # Generate recommendations
        if validation_result["warnings"] or validation_result["errors"]:
            validation_result["recommendations"].extend(
                [
                    "Consider cost optimization strategies",
                    "Review pricing strategy to increase revenue",
                    "Evaluate necessity and timing of this expense",
                ]
            )

        return validation_result

    def validate_cash_flow_impact(
        self,
        transaction_amount: Decimal,
        transaction_type: TransactionType,
        current_balance: Decimal,
    ) -> Dict[str, Any]:
        """Validate cash flow impact of transaction."""
        validation_result = {
            "is_valid": True,
            "warnings": [],
            "errors": [],
            "projected_balance": current_balance,
        }

        # Calculate projected balance
        if transaction_type == TransactionType.EXPENSE:
            projected_balance = current_balance - transaction_amount
        elif transaction_type == TransactionType.INCOME:
            projected_balance = current_balance + transaction_amount
        else:
            projected_balance = current_balance

        validation_result["projected_balance"] = projected_balance

        # Check balance thresholds
        min_balance = self.validation_rules["cash_flow_rules"]["minimum_balance"]
        critical_balance = self.validation_rules["cash_flow_rules"]["critical_balance"]

        if projected_balance < critical_balance:
            validation_result["errors"].append(
                f"Transaction would result in critical cash balance: ${projected_balance}"
            )
            validation_result["is_valid"] = False
        elif projected_balance < min_balance:
            validation_result["warnings"].append(
                f"Transaction would result in low cash balance: ${projected_balance}"
            )

        return validation_result

    def validate_payment_schedule(
        self, due_date: date, amount: Decimal, existing_payments: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Validate payment schedule for conflicts and cash flow."""
        validation_result = {
            "is_valid": True,
            "warnings": [],
            "errors": [],
            "conflicts": [],
        }

        # Check for payment clustering (too many payments on same date)
        same_date_payments = [
            p for p in existing_payments if p.get("due_date") == due_date
        ]

        total_same_date = (
            sum(Decimal(str(p.get("amount", 0))) for p in same_date_payments) + amount
        )

        if len(same_date_payments) >= 3:
            validation_result["warnings"].append(
                f"Multiple payments ({len(same_date_payments) + 1}) scheduled for {due_date}"
            )

        if total_same_date > Decimal("25000"):
            validation_result["warnings"].append(
                f"High payment volume (${total_same_date}) scheduled for {due_date}"
            )

        # Check for weekend/holiday scheduling
        if due_date.weekday() >= 5:  # Saturday or Sunday
            validation_result["warnings"].append(
                f"Payment scheduled for weekend ({due_date.strftime('%A')})"
            )

        return validation_result

    def validate_currency_consistency(
        self, transactions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Validate currency consistency across transactions."""
        validation_result = {"is_valid": True, "warnings": [], "currency_summary": {}}

        # Analyze currency distribution
        currencies = {}
        for transaction in transactions:
            currency = transaction.get("currency", "USD")
            currencies[currency] = currencies.get(currency, 0) + 1

        validation_result["currency_summary"] = currencies

        # Warn about currency mixing
        if len(currencies) > 2:
            validation_result["warnings"].append(
                f"Multiple currencies detected: {list(currencies.keys())}"
            )

        # Check for unusual currencies
        standard_currencies = ["USD", "CRC", "EUR", "GBP"]
        unusual_currencies = [
            curr for curr in currencies.keys() if curr not in standard_currencies
        ]

        if unusual_currencies:
            validation_result["warnings"].append(
                f"Unusual currencies detected: {unusual_currencies}"
            )

        return validation_result

    def validate_date_range(
        self, start_date: date, end_date: date, context: str = "general"
    ) -> Dict[str, Any]:
        """Validate date ranges for business logic."""
        validation_result = {"is_valid": True, "warnings": [], "errors": []}

        # Basic date validation
        if start_date > end_date:
            validation_result["errors"].append("Start date cannot be after end date")
            validation_result["is_valid"] = False
            return validation_result

        # Future date validation
        today = date.today()
        if start_date > today:
            validation_result["warnings"].append("Start date is in the future")

        # Range length validation
        days_diff = (end_date - start_date).days

        if context == "reporting" and days_diff > 365:
            validation_result["warnings"].append(
                f"Report period is very long ({days_diff} days)"
            )
        elif context == "forecasting" and days_diff < 30:
            validation_result["warnings"].append(
                f"Forecast period is very short ({days_diff} days)"
            )

        return validation_result

    def validate_integration_config(
        self, integration_type: str, config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate integration configuration."""
        validation_result = {
            "is_valid": True,
            "warnings": [],
            "errors": [],
            "required_fields": [],
        }

        # Define required fields per integration type
        required_fields = {
            "stripe": ["api_key"],
            "airtable": ["api_key", "base_id", "table_name"],
            "webhook": ["webhook_url"],
            "google_ads": ["api_key", "customer_id"],
        }

        type_requirements = required_fields.get(integration_type.lower(), [])
        validation_result["required_fields"] = type_requirements

        # Check required fields
        missing_fields = [field for field in type_requirements if not config.get(field)]

        if missing_fields:
            validation_result["errors"].extend(
                [f"Missing required field: {field}" for field in missing_fields]
            )
            validation_result["is_valid"] = False

        # Validate specific field formats
        if "webhook_url" in config:
            url = config["webhook_url"]
            if not (url.startswith("http://") or url.startswith("https://")):
                validation_result["errors"].append(
                    "Webhook URL must start with http:// or https://"
                )
                validation_result["is_valid"] = False

        if "api_key" in config:
            api_key = config["api_key"]
            if len(api_key) < 10:
                validation_result["warnings"].append("API key seems unusually short")

        return validation_result
