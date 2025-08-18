"""
Unit tests for FinancialCalculator class

This module contains comprehensive unit tests for the FinancialCalculator class,
covering all financial calculations and edge cases.
"""

from __future__ import annotations

import pytest
import pandas as pd
import numpy as np
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, date, timedelta
from typing import Dict, Any, List

from src.services.financial_calculator import FinancialCalculator
from src.models import Cost, RecurringCost, CostCategory, Payment, PaymentStatus

# Test data
TEST_COSTS = [
    Cost(
        date=date(2023, 1, 1),
        category=CostCategory.TECHNOLOGY,
        amount_usd=Decimal('99.99'),
        description="Test cost 1"
    ),
    Cost(
        date=date(2023, 2, 1),
        category=CostCategory.OFFICE,
        amount_usd=Decimal('150.50'),
        description="Test cost 2"
    )
]

TEST_RECURRING_COSTS = [
    RecurringCost(
        name="Monthly Subscription",
        category=CostCategory.TECHNOLOGY,
        currency="USD",
        amount_expected=Decimal('29.99'),
        recurrence="monthly",
        next_due_date=date(2023, 4, 1)
    )
]

# Fixtures
@pytest.fixture
def calculator() -> FinancialCalculator:
    """Fixture that provides a FinancialCalculator instance."""
    return FinancialCalculator()

@pytest.fixture
def sample_costs() -> List[Cost]:
    """Fixture that provides sample Cost objects for testing."""
    return TEST_COSTS

@pytest.fixture
def sample_recurring_costs() -> List[RecurringCost]:
    """Fixture that provides sample RecurringCost objects for testing."""
    return TEST_RECURRING_COSTS

class TestFinancialCalculatorBasic:
    """Test suite for basic financial calculations"""
    
    def test_calculate_net_profit(self, calculator: FinancialCalculator):
        """Test net profit calculation"""
        result = calculator.calculate_net_profit(
            revenue=Decimal('1000'),
            costs=Decimal('750')
        )
        assert result['net_profit'] == Decimal('250')
        assert result['margin_percentage'] == 25.0
    
    def test_calculate_margin_positive(self, calculator: FinancialCalculator):
        """Test margin calculation with positive values"""
        result = calculator.calculate_margin(
            revenue=Decimal('1000'),
            costs=Decimal('800')
        )
        assert result['margin_percentage'] == 20.0
        assert result['gross_profit'] == Decimal('200')
    
    def test_calculate_margin_zero_revenue(self, calculator: FinancialCalculator):
        """Test margin calculation with zero revenue"""
        result = calculator.calculate_margin(
            revenue=Decimal('0'),
            costs=Decimal('100')
        )
        assert result['margin_percentage'] == 0.0
    
    def test_currency_conversion(self, calculator: FinancialCalculator):
        """Test currency conversion with exchange rates"""
        amount = Decimal('100')
        exchange_rates = {'EUR': Decimal('0.85'), 'GBP': Decimal('0.75')}
        result = calculator.convert_currency(amount, exchange_rates)
        
        assert result['EUR'] == Decimal('85.00')
        assert result['GBP'] == Decimal('75.00')
        assert result['original_amount'] == amount
        assert result['original_currency'] == 'USD'
    
    def test_break_even_analysis(self, calculator: FinancialCalculator):
        """Test break-even point calculation"""
        result = calculator.calculate_break_even(
            fixed_costs=Decimal('10000'),
            price_per_unit=Decimal('100'),
            variable_cost_per_unit=Decimal('60')
        )
        assert result['break_even_units'] == 250
        assert result['break_even_sales'] == Decimal('25000')
        assert result['contribution_margin'] == Decimal('40.00')
        assert result['contribution_ratio'] == 0.4
    
    def test_calculate_cash_flow_basic(self, calculator: FinancialCalculator):
        """Test basic cash flow calculation"""
        inflows = [Decimal('1000'), Decimal('1200'), Decimal('1100')]
        outflows = [Decimal('800'), Decimal('900'), Decimal('850')]
        result = calculator.calculate_cash_flow(inflows, outflows)
        assert result['net_cash_flow'] == Decimal('750')  # (1000+1200+1100) - (800+900+850)
        assert result['total_inflows'] == Decimal('3300')
        assert result['total_outflows'] == Decimal('2550')
    
    def test_calculate_cash_flow_empty_lists(self, calculator: FinancialCalculator):
        """Test cash flow with empty input lists"""
        result = calculator.calculate_cash_flow([], [])
        assert result['net_cash_flow'] == Decimal('0')
        assert result['total_inflows'] == Decimal('0')
        assert result['total_outflows'] == Decimal('0')


class TestFinancialCalculatorCostAnalysis:
    """Test suite for cost analysis methods"""
    
    def test_analyze_costs_by_category(self, calculator: FinancialCalculator, sample_costs: List[Cost]):
        """Test cost analysis by category"""
        result = calculator.analyze_costs(sample_costs)
        
        assert 'by_category' in result
        assert 'TECHNOLOGY' in result['by_category']
        assert 'OFFICE' in result['by_category']
        assert result['by_category']['TECHNOLOGY'] == Decimal('99.99')
        assert result['by_category']['OFFICE'] == Decimal('150.50')
        assert result['total_costs'] == Decimal('250.49')
    
    def test_analyze_recurring_costs(self, calculator: FinancialCalculator, sample_recurring_costs: List[RecurringCost]):
        """Test recurring cost analysis"""
        result = calculator.analyze_recurring_costs(
            sample_recurring_costs,
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31)
        )
        
        assert 'total_annual_cost' in result
        assert 'by_category' in result
        assert 'TECHNOLOGY' in result['by_category']
        assert result['by_category']['TECHNOLOGY'] > Decimal('0')
        assert 'occurrences' in result
        assert len(result['occurrences']) > 0


class TestFinancialCalculatorTimeSeries:
    """Test suite for time series financial calculations"""
    
    def test_calculate_roi(self, calculator: FinancialCalculator):
        """Test return on investment calculation"""
        result = calculator.calculate_roi(
            initial_investment=Decimal('10000'),
            current_value=Decimal('15000')
        )
        assert result['roi'] == 0.5  # 50% ROI
        assert result['absolute_return'] == Decimal('5000')
    
    def test_calculate_growth_rate(self, calculator: FinancialCalculator):
        """Test growth rate calculation"""
        result = calculator.calculate_growth_rate(
            initial_value=Decimal('1000'),
            final_value=Decimal('1500'),
            periods=5
        )
        assert 'cagr' in result
        assert 'absolute_growth' in result
        assert result['absolute_growth'] == Decimal('500')
        assert result['growth_percentage'] == 50.0


class TestFinancialCalculatorEdgeCases:
    """Test edge cases and error handling"""
    
    def test_divide_by_zero_handling(self, calculator: FinancialCalculator):
        """Test handling of division by zero in margin calculations"""
        result = calculator.calculate_margin(
            revenue=Decimal('0'),
            costs=Decimal('100')
        )
        assert result['margin_percentage'] == 0.0
    
    def test_negative_values(self, calculator: FinancialCalculator):
        """Test handling of negative values in calculations"""
        with pytest.raises(ValueError):
            calculator.calculate_net_profit(
                revenue=Decimal('-1000'),
                costs=Decimal('500')
            )
        
        with pytest.raises(ValueError):
            calculator.calculate_net_profit(
                revenue=Decimal('1000'),
                costs=Decimal('-500')
            )


class TestFinancialCalculatorIntegration:
    """Integration tests for combined financial calculations"""
    
    def test_complete_financial_analysis(self, calculator: FinancialCalculator, sample_costs: List[Cost]):
        """Test a complete financial analysis workflow"""
        # Analyze costs
        cost_analysis = calculator.analyze_costs(sample_costs)
        
        # Calculate margins
        margin_analysis = calculator.calculate_margin(
            revenue=Decimal('10000'),
            costs=cost_analysis['total_costs']
        )
        
        # Calculate ROI
        roi_analysis = calculator.calculate_roi(
            initial_investment=Decimal('50000'),
            current_value=Decimal('75000')
        )
        
        # Verify all expected results are present
        assert 'total_costs' in cost_analysis
        assert 'margin_percentage' in margin_analysis
        assert 'roi' in roi_analysis
        
        # Additional assertions to verify relationships between calculations
        assert margin_analysis['gross_profit'] == Decimal('10000') - cost_analysis['total_costs']
        assert roi_analysis['absolute_return'] == Decimal('25000')
    
    def test_uneven_cash_flows(self, calculator: FinancialCalculator):
        """Test cash flow with uneven length lists"""
        inflows = [Decimal('1000'), Decimal('1200')]
        outflows = [Decimal('800'), Decimal('900'), Decimal('850')]
        result = calculator.calculate_cash_flow(inflows, outflows)
        assert result['net_cash_flow'] == Decimal('-350')  # (1000+1200) - (800+900+850)
        assert result['total_inflows'] == Decimal('2200')
        assert result['total_outflows'] == Decimal('2550')
    
    def test_roi_with_profit(self, calculator: FinancialCalculator):
        """Test ROI calculation with positive return"""
        result = calculator.calculate_roi(
            initial_investment=Decimal('1000'),
            current_value=Decimal('1200')
        )
        assert result['roi'] == 0.2  # 20% ROI
        assert result['absolute_return'] == Decimal('200')
    
    def test_roi_zero_investment(self, calculator: FinancialCalculator):
        """Test ROI with zero initial investment"""
        with pytest.raises(ValueError):
            calculator.calculate_roi(
                initial_investment=Decimal('0'),
                current_value=Decimal('1200')
            )


class TestFinancialCalculatorPerformance:
    """Performance tests for financial calculations"""
    
    @pytest.mark.performance
    def test_large_dataset_performance(self, calculator: FinancialCalculator):
        """Test performance with large datasets"""
        # Generate large test data
        large_costs = [
            Cost(
                date=date(2023, 1, 1) + timedelta(days=i),
                category=CostCategory.TECHNOLOGY,
                amount_usd=Decimal(str(100 + i)),
                description=f"Test cost {i}"
            ) for i in range(1000)
        ]
        
        # Time the analysis
        import time
        start_time = time.time()
        result = calculator.analyze_costs(large_costs)
        elapsed_time = time.time() - start_time
        
        assert 'total_costs' in result
        assert elapsed_time < 0.1  # Should process 1000 records in under 100ms
        
    @pytest.mark.performance
    def test_concurrent_calculations(self, calculator: FinancialCalculator):
        """Test concurrent calculation performance"""
        import concurrent.futures
        
        def run_calculation(i):
            return calculator.calculate_net_profit(
                revenue=Decimal('1000') + Decimal(str(i)),
                costs=Decimal('500') + Decimal(str(i))
            )
        
        # Run 100 calculations in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(run_calculation, i) for i in range(100)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        assert len(results) == 100
        assert all('net_profit' in r for r in results)
    
    def test_roi_negative_return(self, calculator: FinancialCalculator):
        """Test ROI with negative return"""
        result = calculator.calculate_roi(
            initial_investment=Decimal('1000'),
            current_value=Decimal('800')
        )
        assert result['roi'] == -0.2  # -20% ROI
        assert result['absolute_return'] == Decimal('-200')
    
    def test_roi_negative_investment(self, calculator: FinancialCalculator):
        """Test ROI with negative initial investment"""
        with pytest.raises(ValueError):
            calculator.calculate_roi(
                initial_investment=Decimal('-1000'),
                current_value=Decimal('1200')
            )
    def test_growth_rate_calculation(self, calculator: FinancialCalculator):
        """Test growth rate calculation"""
        result = calculator.calculate_growth_rate(
            initial_value=Decimal('1000'),
            final_value=Decimal('1200'),
            periods=1
        )
        assert result['growth_percentage'] == 20.0
        assert result['absolute_growth'] == Decimal('200')
        assert 'cagr' in result
    
    def test_growth_rate_multiple_periods(self, calculator: FinancialCalculator):
        """Test growth rate over multiple periods"""
        result = calculator.calculate_growth_rate(
            initial_value=Decimal('1000'),
            final_value=Decimal('1440'),  # 20% growth over 2 periods
            periods=2
        )
        assert abs(result['cagr'] - 20.0) < 0.1  # Compound annual growth rate
    
    def test_growth_rate_zero_initial_value(self, calculator: FinancialCalculator):
        """Test growth rate with zero initial value"""
        with pytest.raises(ValueError):
            calculator.calculate_growth_rate(
                initial_value=Decimal('0'),
                final_value=Decimal('1000'),
                periods=1
            )
    
    def test_compound_interest(self, calculator: FinancialCalculator):
        """Test compound interest calculation"""
        result = calculator.calculate_compound_interest(
            principal=Decimal('1000'),
            annual_rate=Decimal('0.05'),  # 5%
            years=2,
            compounding_frequency=1  # Annual
        )
        expected = Decimal('1102.50')  # 1000 * (1 + 0.05/1)^(1*2)
        assert abs(result['future_value'] - expected) < Decimal('0.01')
    
    def test_compound_interest_monthly(self, calculator: FinancialCalculator):
        """Test compound interest with monthly compounding"""
        result = calculator.calculate_compound_interest(
            principal=Decimal('1000'),
            annual_rate=Decimal('0.12'),  # 12% annual
            years=1,
            compounding_frequency=12  # Monthly
        )
        expected = Decimal('1126.83')  # 1000 * (1 + 0.12/12)^(12*1)
        assert abs(result['future_value'] - expected) < Decimal('0.01')
    
    def test_present_value(self, calculator: FinancialCalculator):
        """Test present value calculation"""
        result = calculator.calculate_present_value(
            future_value=Decimal('1100'),
            discount_rate=Decimal('0.10'),
            periods=1
        )
        expected = Decimal('1000.00')  # 1100 / (1 + 0.10)^1
        assert abs(result['present_value'] - expected) < Decimal('0.01')
        assert 'discount_factor' in result
    
    def test_future_value(self, calculator: FinancialCalculator):
        """Test future value calculation"""
        result = calculator.calculate_future_value(
            present_value=Decimal('1000'),
            rate=Decimal('0.10'),
            periods=1
        )
        expected = Decimal('1100.00')  # 1000 * (1 + 0.10)^1
        assert abs(result['future_value'] - expected) < Decimal('0.01')
        assert 'growth_factor' in result
    
    def test_break_even_analysis(self, calculator: FinancialCalculator):
        """Test break-even analysis"""
        result = calculator.calculate_break_even(
            fixed_costs=Decimal('10000'),
            price_per_unit=Decimal('100'),
            variable_cost_per_unit=Decimal('60')
        )
        assert result['break_even_units'] == 250  # 10000 / (100 - 60)
        assert result['break_even_sales'] == Decimal('25000.00')  # 250 * 100
        assert result['contribution_margin'] == Decimal('40.00')  # 100 - 60
        assert result['contribution_ratio'] == 0.4  # 40 / 100
    
    def test_break_even_zero_margin(self, calculator: FinancialCalculator):
        """Test break-even with zero contribution margin"""
        with pytest.raises(ValueError, match="Price per unit must be greater than variable cost per unit"):
            calculator.calculate_break_even(
                fixed_costs=Decimal('10000'),
                price_per_unit=Decimal('15'),
                variable_cost_per_unit=Decimal('15')  # Same as price, zero margin
            )
    
    def test_validate_financial_input(self, calculator: FinancialCalculator):
        """Test financial input validation"""
        # Test valid inputs
        assert calculator._validate_numeric(Decimal('100')) == Decimal('100')
        assert calculator._validate_numeric(100.5) == Decimal('100.5')
        assert calculator._validate_numeric('1000.50') == Decimal('1000.50')
        
        # Test zero
        assert calculator._validate_numeric(0) == Decimal('0')
        
        # Test invalid inputs
        with pytest.raises(ValueError, match="must be a number"):
            calculator._validate_numeric("not a number")
        
        # Test negative values (when not allowed)
        with pytest.raises(ValueError, match="must be non-negative"):
            calculator._validate_numeric(-100, allow_negative=False)
            
        # Test negative values (when allowed)
        assert calculator._validate_numeric(-100, allow_negative=True) == Decimal('-100')
    
    def test_currency_formatting(self, calculator: FinancialCalculator):
        """Test currency formatting"""
        # Test USD formatting
        assert calculator.format_currency(Decimal('1000'), 'USD') == "$1,000.00"
        assert calculator.format_currency(Decimal('1234.56'), 'USD') == "$1,234.56"
        
        # Test EUR formatting
        assert calculator.format_currency(Decimal('1000'), 'EUR') == "€1,000.00"
        
        # Test negative values
        assert calculator.format_currency(Decimal('-1000'), 'USD') == "-$1,000.00"
        
        # Test zero
        assert calculator.format_currency(Decimal('0'), 'USD') == "$0.00"
        
        # Test with different decimal places
        assert calculator.format_currency(Decimal('1000.5'), 'USD') == "$1,000.50"
        assert calculator.format_currency(Decimal('1000.555'), 'USD', decimal_places=3) == "$1,000.555"

class TestFinancialCalculatorEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_large_numbers(self, calculator: FinancialCalculator):
        """Test calculations with very large numbers"""
        # Test with very large numbers (1 trillion revenue, 800 billion costs)
        result = calculator.calculate_margin(
            revenue=Decimal('1000000000000'),  # 1 trillion
            costs=Decimal('800000000000')      # 800 billion
        )
        assert result['margin_percentage'] == 20.0  # 20% margin
        assert result['gross_profit'] == Decimal('200000000000')  # 200 billion
    
    def test_small_numbers(self, calculator: FinancialCalculator):
        """Test calculations with very small numbers"""
        # Test with very small numbers
        result = calculator.calculate_margin(
            revenue=Decimal('0.000001'),  # 1e-6
            costs=Decimal('0.0000008')    # 8e-7
        )
        assert abs(result['margin_percentage'] - 20.0) < 0.1  # 20% margin
    
    def test_decimal_precision(self, calculator: FinancialCalculator):
        """Test calculations with high precision decimals"""
        revenue = Decimal('1000.123456789')
        costs = Decimal('800.987654321')
        
        result = calculator.calculate_margin(
            revenue=revenue,
            costs=costs
        )
        expected = ((float(revenue) - float(costs)) / float(revenue)) * 100
        assert abs(result['margin_percentage'] - expected) < 0.000001
    
    def test_infinity_handling(self, calculator: FinancialCalculator):
        """Test handling of infinity values"""
        import math
        
        with pytest.raises(ValueError, match="must be finite"):
            calculator.calculate_margin(
                revenue=Decimal('Infinity'),
                costs=Decimal('1000')
            )
            
        with pytest.raises(ValueError, match="must be finite"):
            calculator.calculate_margin(
                revenue=Decimal('1000'),
                costs=Decimal('-Infinity')
            )
    
    def test_nan_handling(self, calculator: FinancialCalculator):
        """Test handling of NaN values"""
        with pytest.raises((ValueError, TypeError)):
            calculator.calculate_margin(
                revenue=float('nan'),
                costs=Decimal('1000')
            )
    @pytest.fixture
    def financial_data_samples(self):
        """Fixture providing sample financial data for testing"""
        return {
            'revenues': [Decimal('1000'), Decimal('1200'), Decimal('1100')],
            'costs': [Decimal('800'), Decimal('900'), Decimal('850')],
            'investments': [Decimal('5000'), Decimal('3000')],
            'current_values': [Decimal('5500'), Decimal('3500')]
        }
    
    def test_complete_financial_analysis(self, calculator: FinancialCalculator, financial_data_samples):
        """Test complete financial analysis workflow"""
        # Calculate basic metrics
        total_revenue = sum(financial_data_samples['revenues'])
        total_costs = sum(financial_data_samples['costs'])
        
        # Calculate profit margin
        margin_result = calculator.calculate_margin(
            revenue=total_revenue,
            costs=total_costs
        )
        
        # Calculate cash flow
        cash_flow_result = calculator.calculate_cash_flow(
            financial_data_samples['revenues'],
            financial_data_samples['costs']
        )
        
        # Calculate ROI for each investment
        roi_results = []
        for inv, curr_val in zip(financial_data_samples['investments'], 
                               financial_data_samples['current_values']):
            roi_results.append(calculator.calculate_roi(
                initial_investment=inv,
                current_value=curr_val
            ))
        
        # Verify all results are as expected
        assert margin_result['gross_profit'] == total_revenue - total_costs
        assert cash_flow_result['net_cash_flow'] == sum(financial_data_samples['revenues']) - sum(financial_data_samples['costs'])
        assert all('roi' in result for result in roi_results)
        roi = calculate_roi(total_costs, total_revenue)
        
        # Validate results
        assert margin_result['margin_percentage'] > 0
        assert cash_flow_result['net_cash_flow'] > 0
        assert all(result['roi'] > 0 for result in roi_results)
        assert total_revenue > total_costs
    
    def test_currency_conversion_workflow(self, calculator: FinancialCalculator):
        """Test multi-currency financial calculations"""
        # Set up test data
        amounts = [Decimal('100'), Decimal('200'), Decimal('300')]
        exchange_rates = {
            'USD': Decimal('1.0'),
            'EUR': Decimal('0.85'),
            'GBP': Decimal('0.75'),
            'JPY': Decimal('110.25')
        }
        
        # Test conversion to different currencies
        for target_currency in ['EUR', 'GBP', 'JPY']:
            result = calculator.convert_currency(
                amount=Decimal('100'),
                exchange_rates=exchange_rates
            )
            assert target_currency in result
            assert result[target_currency] > Decimal('0')
            
            # Verify the conversion rate was applied correctly
            expected = Decimal('100') * exchange_rates[target_currency]
            assert abs(result[target_currency] - expected) < Decimal('0.01')  # EUR is worth less
            
    def test_time_series_calculations(self, calculator: FinancialCalculator):
        """Test calculations over time series data"""
        import pandas as pd
        
        # Create a time series with 10% monthly growth
        months = 12
        initial_value = Decimal('1000')
        growth_rate = Decimal('0.10')  # 10% monthly growth
        
        # Generate time series data
        dates = pd.date_range(start='2023-01-01', periods=months, freq='M')
        values = [initial_value * (1 + growth_rate) ** i for i in range(months)]

class TestFinancialCalculatorPerformance:
    """Test performance of FinancialCalculator methods"""
    
    @pytest.mark.performance
    def test_bulk_calculations_performance(self, calculator: FinancialCalculator):
        """Test performance of bulk calculations"""
        import time
        
        # Test performance of margin calculations
        start_time = time.time()
        
        # Perform many calculations
        for i in range(10000):
            calculator.calculate_margin(
                revenue=Decimal('1000') + Decimal(str(i)),
                costs=Decimal('800') + Decimal(str(i))
            )
        
        elapsed = time.time() - start_time
        assert elapsed < 1.0, f"Bulk calculations took too long: {elapsed:.3f} seconds"
    
    @pytest.mark.performance
    def test_currency_conversion_performance(self, calculator: FinancialCalculator):
        """Test performance of currency conversions"""
        import time
        
        # Set up test data
        amount = Decimal('100')
        exchange_rates = {
            'USD': Decimal('1.0'),
            'EUR': Decimal('0.85'),
            'GBP': Decimal('0.75'),
            'JPY': Decimal('110.25')
        }
        
        start_time = time.time()
        
        # Perform many conversions
        for _ in range(10000):
            calculator.convert_currency(amount, exchange_rates)
        
        elapsed = time.time() - start_time
        assert elapsed < 0.5, f"Currency conversions took too long: {elapsed:.3f} seconds"
