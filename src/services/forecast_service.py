"""
Advanced Forecasting Service
Provides multiple forecasting methods with confidence intervals and risk analysis.
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class ForecastMethod(Enum):
    """Forecasting method enumeration"""

    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    SEASONAL = "seasonal"
    MONTE_CARLO = "monte_carlo"


class ScenarioType(Enum):
    """Scenario analysis types"""

    BEST_CASE = "best_case"
    WORST_CASE = "worst_case"
    MOST_LIKELY = "most_likely"


@dataclass
class ForecastResult:
    """Forecast result container"""

    method: ForecastMethod
    periods: int
    forecasted_values: List[float]
    confidence_intervals: List[Tuple[float, float]]
    scenarios: Dict[ScenarioType, List[float]]
    metadata: Dict[str, Any]


class ForecastService:
    """Advanced forecasting service with multiple methods and risk analysis."""

    def __init__(self):
        self.confidence_level = 0.95
        self.monte_carlo_iterations = 10000

    def generate_forecast(
        self,
        historical_data: List[Dict[str, Any]],
        periods: int,
        method: ForecastMethod = ForecastMethod.LINEAR,
        include_scenarios: bool = True,
        include_monte_carlo: bool = False,
    ) -> ForecastResult:
        """
        Generate comprehensive forecast with multiple analysis methods.

        Args:
            historical_data: Historical data points with 'date' and 'value' keys
            periods: Number of periods to forecast
            method: Primary forecasting method
            include_scenarios: Whether to include scenario analysis
            include_monte_carlo: Whether to include Monte Carlo simulation

        Returns:
            ForecastResult with comprehensive forecast data
        """
        try:
            if not historical_data:
                raise ValueError("Historical data cannot be empty")

            # Prepare data
            df = self._prepare_data(historical_data)
            values = df["value"].values

            # Generate primary forecast
            if method == ForecastMethod.LINEAR:
                forecast = self._linear_forecast(values, periods)
            elif method == ForecastMethod.EXPONENTIAL:
                forecast = self._exponential_smoothing(values, periods)
            elif method == ForecastMethod.SEASONAL:
                forecast = self._seasonal_forecast(df, periods)
            else:
                forecast = self._linear_forecast(values, periods)

            # Calculate confidence intervals
            confidence_intervals = self._calculate_confidence_intervals(
                values, forecast, periods
            )

            # Generate scenarios
            scenarios = {}
            if include_scenarios:
                scenarios = self._generate_scenarios(values, forecast, periods)

            # Monte Carlo simulation
            if include_monte_carlo:
                monte_carlo_results = self._monte_carlo_simulation(values, periods)
                scenarios[ScenarioType.MONTE_CARLO] = monte_carlo_results

            # Metadata
            metadata = {
                "historical_mean": float(np.mean(values)),
                "historical_std": float(np.std(values)),
                "trend_slope": self._calculate_trend_slope(values),
                "seasonality_detected": self._detect_seasonality(values),
                "forecast_accuracy_score": self._calculate_accuracy_score(values),
                "calculation_timestamp": datetime.now().isoformat(),
            }

            return ForecastResult(
                method=method,
                periods=periods,
                forecasted_values=forecast.tolist(),
                confidence_intervals=confidence_intervals,
                scenarios=scenarios,
                metadata=metadata,
            )

        except Exception as e:
            logger.error(f"Error generating forecast: {str(e)}")
            raise

    def _prepare_data(self, historical_data: List[Dict[str, Any]]) -> pd.DataFrame:
        """Prepare and validate historical data."""
        df = pd.DataFrame(historical_data)

        # Ensure required columns
        if "date" not in df.columns or "value" not in df.columns:
            raise ValueError("Historical data must contain 'date' and 'value' columns")

        # Convert and sort by date
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)

        # Handle missing values
        df["value"] = df["value"].fillna(df["value"].mean())

        return df

    def _linear_forecast(self, values: np.ndarray, periods: int) -> np.ndarray:
        """Linear trend forecasting using least squares regression."""
        x = np.arange(len(values))
        coeffs = np.polyfit(x, values, 1)

        future_x = np.arange(len(values), len(values) + periods)
        return np.polyval(coeffs, future_x)

    def _exponential_smoothing(
        self, values: np.ndarray, periods: int, alpha: float = 0.3
    ) -> np.ndarray:
        """Exponential smoothing with trend (Holt's method)."""
        if len(values) < 2:
            return np.array([values[-1]] * periods)

        # Initialize
        level = values[0]
        trend = values[1] - values[0]
        beta = 0.1  # Trend smoothing parameter

        # Smooth historical data
        for i in range(1, len(values)):
            prev_level = level
            level = alpha * values[i] + (1 - alpha) * (level + trend)
            trend = beta * (level - prev_level) + (1 - beta) * trend

        # Generate forecast
        forecast = []
        for h in range(1, periods + 1):
            forecast.append(level + h * trend)

        return np.array(forecast)

    def _seasonal_forecast(self, df: pd.DataFrame, periods: int) -> np.ndarray:
        """Seasonal forecasting using decomposition."""
        values = df["value"].values

        # Simple seasonal decomposition
        if len(values) < 12:  # Not enough data for seasonality
            return self._linear_forecast(values, periods)

        # Detect seasonal period (assume monthly data)
        seasonal_period = min(12, len(values) // 2)

        # Calculate seasonal indices
        seasonal_indices = []
        for i in range(seasonal_period):
            seasonal_values = values[i::seasonal_period]
            if len(seasonal_values) > 0:
                seasonal_indices.append(np.mean(seasonal_values))

        if not seasonal_indices:
            return self._linear_forecast(values, periods)

        # Deseasonalize data
        deseasonalized = []
        for i, value in enumerate(values):
            seasonal_idx = i % len(seasonal_indices)
            if seasonal_indices[seasonal_idx] != 0:
                deseasonalized.append(value / seasonal_indices[seasonal_idx])
            else:
                deseasonalized.append(value)

        # Forecast deseasonalized trend
        trend_forecast = self._linear_forecast(np.array(deseasonalized), periods)

        # Reseasonalize forecast
        forecast = []
        for i, trend_value in enumerate(trend_forecast):
            seasonal_idx = (len(values) + i) % len(seasonal_indices)
            forecast.append(trend_value * seasonal_indices[seasonal_idx])

        return np.array(forecast)

    def _calculate_confidence_intervals(
        self, historical: np.ndarray, forecast: np.ndarray, periods: int
    ) -> List[Tuple[float, float]]:
        """Calculate confidence intervals for forecast."""
        # Calculate prediction error standard deviation
        if len(historical) > 1:
            residuals = np.diff(historical)
            std_error = np.std(residuals)
        else:
            std_error = np.std(historical) if len(historical) > 0 else 0

        # Z-score for 95% confidence
        z_score = 1.96

        intervals = []
        for i, value in enumerate(forecast):
            # Error increases with forecast horizon
            error_multiplier = np.sqrt(i + 1)
            margin_of_error = z_score * std_error * error_multiplier

            lower_bound = value - margin_of_error
            upper_bound = value + margin_of_error

            intervals.append((float(lower_bound), float(upper_bound)))

        return intervals

    def _generate_scenarios(
        self, historical: np.ndarray, base_forecast: np.ndarray, periods: int
    ) -> Dict[ScenarioType, List[float]]:
        """Generate best case, worst case, and most likely scenarios."""
        historical_std = np.std(historical)
        historical_mean = np.mean(historical)

        # Calculate growth rates
        if len(historical) > 1:
            growth_rates = np.diff(historical) / historical[:-1]
            avg_growth = np.mean(growth_rates)
            std_growth = np.std(growth_rates)
        else:
            avg_growth = 0
            std_growth = 0.1

        scenarios = {}

        # Best case: +1 std deviation growth
        best_case = []
        current_value = historical[-1] if len(historical) > 0 else base_forecast[0]
        for i in range(periods):
            growth_factor = 1 + avg_growth + std_growth
            current_value *= growth_factor
            best_case.append(float(current_value))
        scenarios[ScenarioType.BEST_CASE] = best_case

        # Worst case: -1 std deviation growth
        worst_case = []
        current_value = historical[-1] if len(historical) > 0 else base_forecast[0]
        for i in range(periods):
            growth_factor = 1 + avg_growth - std_growth
            current_value *= max(0.1, growth_factor)  # Prevent negative values
            worst_case.append(float(current_value))
        scenarios[ScenarioType.WORST_CASE] = worst_case

        # Most likely: base forecast
        scenarios[ScenarioType.MOST_LIKELY] = base_forecast.tolist()

        return scenarios

    def _monte_carlo_simulation(
        self, historical: np.ndarray, periods: int
    ) -> List[float]:
        """Monte Carlo simulation for risk analysis."""
        if len(historical) < 2:
            return (
                [float(historical[0])] * periods
                if len(historical) > 0
                else [0] * periods
            )

        # Calculate historical statistics
        returns = np.diff(historical) / historical[:-1]
        mean_return = np.mean(returns)
        std_return = np.std(returns)

        # Run Monte Carlo simulation
        simulations = []
        for _ in range(self.monte_carlo_iterations):
            simulation = [historical[-1]]

            for _ in range(periods):
                # Generate random return
                random_return = np.random.normal(mean_return, std_return)
                next_value = simulation[-1] * (1 + random_return)
                simulation.append(max(0, next_value))  # Prevent negative values

            simulations.append(simulation[1:])  # Exclude initial value

        # Calculate percentiles for each period
        simulations = np.array(simulations)
        percentiles = []

        for period in range(periods):
            period_values = simulations[:, period]
            percentile_50 = np.percentile(period_values, 50)
            percentiles.append(float(percentile_50))

        return percentiles

    def _calculate_trend_slope(self, values: np.ndarray) -> float:
        """Calculate trend slope using linear regression."""
        if len(values) < 2:
            return 0.0

        x = np.arange(len(values))
        slope, _ = np.polyfit(x, values, 1)
        return float(slope)

    def _detect_seasonality(self, values: np.ndarray) -> bool:
        """Simple seasonality detection."""
        if len(values) < 24:  # Need at least 2 years of monthly data
            return False

        # Check for repeating patterns (simplified)
        seasonal_period = 12
        if len(values) >= seasonal_period * 2:
            first_year = values[:seasonal_period]
            second_year = values[seasonal_period : seasonal_period * 2]

            correlation = np.corrcoef(first_year, second_year)[0, 1]
            return correlation > 0.5

        return False

    def _calculate_accuracy_score(self, values: np.ndarray) -> float:
        """Calculate forecast accuracy score based on historical data."""
        if len(values) < 4:
            return 0.5  # Default moderate accuracy

        # Use last 25% of data for validation
        split_point = int(len(values) * 0.75)
        train_data = values[:split_point]
        test_data = values[split_point:]

        # Generate forecast for test period
        test_forecast = self._linear_forecast(train_data, len(test_data))

        # Calculate MAPE (Mean Absolute Percentage Error)
        mape = np.mean(np.abs((test_data - test_forecast) / test_data)) * 100

        # Convert to accuracy score (0-1)
        accuracy = max(0, 1 - mape / 100)
        return float(accuracy)
