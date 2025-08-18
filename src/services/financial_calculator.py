"""
Financial Calculator Service

Provides comprehensive financial calculations including margins, ROI,
trend analysis, and break-even calculations with currency support.
"""

from __future__ import annotations

import logging
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Any, Union, Tuple, TypeVar, Generic, Type, cast

import pandas as pd
import numpy as np

# Import from local modules with absolute imports
from src.security.pii_protection import get_structured_logger
from src.utils.currency_utils import CurrencyUtils
from src.models import (
    Cost, RecurringCost, CostCategory,
    Payment, PaymentStatus, PaymentSchedule
)

# Type variables for generic methods
T = TypeVar('T', bound='FinancialCalculator')

# Configure logger
try:
    logger = get_structured_logger().get_logger(__name__)
except Exception:
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class FinancialCalculator:
    """Financial calculator with comprehensive business metrics."""

    def __init__(self, currency_utils: Optional[CurrencyUtils] = None):
        self.currency_utils = currency_utils or CurrencyUtils()

    def calculate_net_profit(
        self,
        revenue: Decimal,
        costs: Decimal,
        exchange_rates: Optional[Dict[str, Decimal]] = None,
    ) -> Dict[str, Any]:
        """
        Calculate net profit with currency conversion support.

        Args:
            revenue: Total revenue amount
            costs: Total costs amount
            exchange_rates: Optional currency conversion rates

        Returns:
            Dict containing net profit, margin, and metadata

        Example:
            >>> calc = FinancialCalculator()
            >>> result = calc.calculate_net_profit(
            ...     revenue=Decimal('100000'),
            ...     costs=Decimal('75000')
            ... )
            >>> print(result['net_profit'])  # 25000
        """
        try:
            if revenue < 0 or costs < 0:
                raise ValueError("Revenue and costs must be non-negative")

            net_profit = revenue - costs
            margin = self.calculate_margin(revenue, costs)

            result = {
                "net_profit": net_profit,
                "revenue": revenue,
                "costs": costs,
                "margin_percentage": margin["margin_percentage"],
                "calculation_date": datetime.now().isoformat(),
                "currency": "USD",  # Default currency
            }

            # Apply exchange rates if provided
            if exchange_rates:
                for currency, rate in exchange_rates.items():
                    result[f"net_profit_{currency.lower()}"] = net_profit * rate

            logger.info(
                "Net profit calculated",
                operation="calculate_net_profit",
                net_profit=float(net_profit),
            )
            return result

        except Exception as e:
            logger.error(
                "Error calculating net profit",
                operation="calculate_net_profit",
                error_type=type(e).__name__,
            )
            raise

    def calculate_margin(self, revenue: Decimal, costs: Decimal) -> Dict[str, Any]:
        """
        Calculate profit margin with division by zero handling.

        Args:
            revenue: Total revenue
            costs: Total costs

        Returns:
            Dict containing margin percentage and metadata

        Example:
            >>> calc = FinancialCalculator()
            >>> result = calc.calculate_margin(
            ...     revenue=Decimal('100000'),
            ...     costs=Decimal('75000')
            ... )
            >>> print(result['margin_percentage'])  # 25.00
        """
        try:
            if revenue < 0 or costs < 0:
                raise ValueError("Revenue and costs must be non-negative")

            if revenue == 0:
                return {
                    "margin_percentage": Decimal("0"),
                    "margin_decimal": Decimal("0"),
                    "gross_profit": Decimal("0"),
                    "revenue": revenue,
                    "costs": costs,
                    "warning": "Revenue is zero - margin calculation not meaningful",
                }

            gross_profit = revenue - costs
            margin_decimal = gross_profit / revenue
            margin_percentage = (margin_decimal * 100).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

            return {
                "margin_percentage": margin_percentage,
                "margin_decimal": margin_decimal,
                "gross_profit": gross_profit,
                "revenue": revenue,
                "costs": costs,
            }

        except Exception as e:
            logger.error(
                "Error calculating margin",
                operation="calculate_margin",
                error_type=type(e).__name__,
            )
            raise

    def calculate_roi(
        self, initial_investment: Decimal, returns: Decimal, time_period: int
    ) -> Dict[str, Any]:
        """
        Calculate Return on Investment (ROI) with annualized metrics.

        Args:
            initial_investment: Initial investment amount
            returns: Total returns received
            time_period: Time period in months

        Returns:
            Dict containing ROI metrics

        Example:
            >>> calc = FinancialCalculator()
            >>> result = calc.calculate_roi(
            ...     initial_investment=Decimal('10000'),
            ...     returns=Decimal('12000'),
            ...     time_period=12
            ... )
            >>> print(result['roi_percentage'])  # 20.00
        """
        try:
            if initial_investment <= 0:
                raise ValueError("Initial investment must be positive")

            if time_period <= 0:
                raise ValueError("Time period must be positive")

            # Basic ROI calculation
            roi_decimal = (returns - initial_investment) / initial_investment
            roi_percentage = (roi_decimal * 100).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

            # Annualized ROI
            years = Decimal(str(time_period)) / 12
            if years > 0:
                annualized_roi = (
                    (returns / initial_investment) ** (1 / float(years)) - 1
                ) * 100
                annualized_roi = Decimal(str(annualized_roi)).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
            else:
                annualized_roi = roi_percentage

            return {
                "roi_percentage": roi_percentage,
                "roi_decimal": roi_decimal,
                "annualized_roi": annualized_roi,
                "initial_investment": initial_investment,
                "returns": returns,
                "net_gain": returns - initial_investment,
                "time_period_months": time_period,
                "time_period_years": years,
            }

        except Exception as e:
            logger.error(
                "Error calculating ROI",
                operation="calculate_roi",
                error_type=type(e).__name__,
            )
            raise

    def calculate_cashflow_forecast(
        self,
        historical_data: List[Dict[str, Any]],
        periods: int,
        method: str = "linear",
    ) -> Dict[str, Any]:
        """
        Calculate cash flow forecast using various methods.

        Args:
            historical_data: List of historical cash flow data points
            periods: Number of future periods to forecast
            method: Forecasting method ('linear', 'exponential', 'moving_average')

        Returns:
            Dict containing forecast data and confidence metrics

        Example:
            >>> historical = [
            ...     {'date': '2024-01-01', 'amount': 10000},
            ...     {'date': '2024-02-01', 'amount': 12000},
            ...     {'date': '2024-03-01', 'amount': 11000}
            ... ]
            >>> result = calc.calculate_cashflow_forecast(historical, 3)
        """
        try:
            if not historical_data:
                raise ValueError("Historical data cannot be empty")

            if periods <= 0:
                raise ValueError("Periods must be positive")

            # Convert to pandas DataFrame for easier manipulation
            df = pd.DataFrame(historical_data)
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date")

            amounts = df["amount"].values

            if method == "linear":
                forecast = self._linear_forecast(amounts, periods)
            elif method == "exponential":
                forecast = self._exponential_forecast(amounts, periods)
            elif method == "moving_average":
                forecast = self._moving_average_forecast(amounts, periods)
            else:
                raise ValueError(f"Unsupported forecasting method: {method}")

            # Calculate confidence intervals (simplified)
            std_dev = np.std(amounts)
            confidence_interval = 1.96 * std_dev  # 95% confidence

            forecast_data = []
            for i, value in enumerate(forecast):
                forecast_data.append(
                    {
                        "period": i + 1,
                        "forecasted_amount": float(value),
                        "lower_bound": float(value - confidence_interval),
                        "upper_bound": float(value + confidence_interval),
                    }
                )

            return {
                "method": method,
                "periods": periods,
                "forecast": forecast_data,
                "historical_mean": float(np.mean(amounts)),
                "historical_std": float(std_dev),
                "confidence_level": 0.95,
                "calculation_date": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(
                "Error calculating cash flow forecast",
                operation="calculate_cashflow_forecast",
                error_type=type(e).__name__,
            )
            raise

    def _linear_forecast(self, data: np.ndarray, periods: int) -> np.ndarray:
        """Linear trend forecasting."""
        x = np.arange(len(data))
        coeffs = np.polyfit(x, data, 1)

        future_x = np.arange(len(data), len(data) + periods)
        return np.polyval(coeffs, future_x)

    def _exponential_forecast(self, data: np.ndarray, periods: int) -> np.ndarray:
        """Exponential smoothing forecasting."""
        alpha = 0.3  # Smoothing parameter
        forecast = [data[0]]

        # Calculate exponential smoothing for historical data
        for i in range(1, len(data)):
            forecast.append(alpha * data[i] + (1 - alpha) * forecast[i - 1])

        # Extend forecast for future periods
        last_forecast = forecast[-1]
        future_forecast = [last_forecast] * periods

        return np.array(future_forecast)

    def _moving_average_forecast(
        self, data: np.ndarray, periods: int, window: int = 3
    ) -> np.ndarray:
        """Moving average forecasting."""
        if len(data) < window:
            window = len(data)

        moving_avg = np.mean(data[-window:])
        return np.array([moving_avg] * periods)

    def calculate_break_even_point(
        self,
        fixed_costs: Decimal,
        variable_cost_per_unit: Decimal,
        price_per_unit: Decimal,
    ) -> Dict[str, Any]:
        """
        Calculate break-even point in units and revenue.

        Args:
            fixed_costs: Total fixed costs
            variable_cost_per_unit: Variable cost per unit
            price_per_unit: Selling price per unit

        Returns:
            Dict containing break-even analysis
        """
        try:
            if price_per_unit <= variable_cost_per_unit:
                raise ValueError(
                    "Price per unit must be greater than variable cost per unit"
                )

            contribution_margin = price_per_unit - variable_cost_per_unit
            break_even_units = fixed_costs / contribution_margin
            break_even_revenue = break_even_units * price_per_unit

            return {
                "break_even_units": break_even_units.quantize(Decimal("0.01")),
                "break_even_revenue": break_even_revenue.quantize(Decimal("0.01")),
                "contribution_margin": contribution_margin,
                "contribution_margin_ratio": (
                    contribution_margin / price_per_unit * 100
                ).quantize(Decimal("0.01")),
                "fixed_costs": fixed_costs,
                "variable_cost_per_unit": variable_cost_per_unit,
                "price_per_unit": price_per_unit,
            }

        except Exception as e:
            logger.error(
                "Error calculating break-even point",
                operation="calculate_break_even",
                error_type=type(e).__name__,
            )
            raise
