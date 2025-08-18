"""
Unit tests for financial calculation functions
"""

import pytest
from decimal import Decimal
from datetime import datetime, date
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from services.financial_calculator import (
    calculate_profit_margin, calculate_cash_flow, calculate_roi,
    calculate_growth_rate, convert_currency, calculate_compound_interest,
    calculate_present_value, calculate_future_value, calculate_break_even,
    validate_financial_input, format_currency
)

class TestFinancialCalculator:
    """Test suite for financial calculation functions"""
    
    def test_calculate_profit_margin_positive(self):
        """Test profit margin calculation with positive values"""
        revenue = 1000
        costs = 800
        margin = calculate_profit_margin(revenue, costs)
        assert margin == 20.0
    
    def test_calculate_profit_margin_zero_revenue(self):
        """Test profit margin with zero revenue"""
        revenue = 0
        costs = 100
        margin = calculate_profit_margin(revenue, costs)
        assert margin == 0.0
    
    def test_calculate_profit_margin_negative_profit(self):
        """Test profit margin with negative profit"""
        revenue = 800
        costs = 1000
        margin = calculate_profit_margin(revenue, costs)
        assert margin == -25.0
    
    def test_calculate_profit_margin_precision(self):
        """Test profit margin calculation precision"""
        revenue = 1000.33
        costs = 750.25
        margin = calculate_profit_margin(revenue, costs)
        expected = ((revenue - costs) / revenue) * 100
        assert abs(margin - expected) < 0.01
    
    def test_calculate_cash_flow_basic(self):
        """Test basic cash flow calculation"""
        inflows = [1000, 1200, 1100]
        outflows = [800, 900, 850]
        net_flow = calculate_cash_flow(inflows, outflows)
        assert net_flow == 750  # (1000+1200+1100) - (800+900+850)
    
    def test_calculate_cash_flow_empty_lists(self):
        """Test cash flow with empty lists"""
        net_flow = calculate_cash_flow([], [])
        assert net_flow == 0
    
    def test_calculate_cash_flow_unequal_lengths(self):
        """Test cash flow with unequal length lists"""
        inflows = [1000, 1200]
        outflows = [800, 900, 850]
        net_flow = calculate_cash_flow(inflows, outflows)
        assert net_flow == -350  # 2200 - 2550
    
    def test_calculate_roi_positive(self):
        """Test ROI calculation with positive return"""
        initial_investment = 1000
        final_value = 1200
        roi = calculate_roi(initial_investment, final_value)
        assert roi == 20.0
    
    def test_calculate_roi_zero_investment(self):
        """Test ROI with zero initial investment"""
        with pytest.raises(ValueError, match="Initial investment cannot be zero"):
            calculate_roi(0, 1000)
    
    def test_calculate_roi_negative_return(self):
        """Test ROI with negative return"""
        initial_investment = 1000
        final_value = 800
        roi = calculate_roi(initial_investment, final_value)
        assert roi == -20.0
    
    def test_calculate_growth_rate_positive(self):
        """Test growth rate calculation"""
        old_value = 1000
        new_value = 1200
        periods = 1
        growth_rate = calculate_growth_rate(old_value, new_value, periods)
        assert growth_rate == 20.0
    
    def test_calculate_growth_rate_multiple_periods(self):
        """Test growth rate over multiple periods"""
        old_value = 1000
        new_value = 1440  # 20% growth over 2 periods
        periods = 2
        growth_rate = calculate_growth_rate(old_value, new_value, periods)
        assert abs(growth_rate - 20.0) < 0.1  # Compound annual growth rate
    
    def test_calculate_growth_rate_zero_old_value(self):
        """Test growth rate with zero old value"""
        with pytest.raises(ValueError, match="Old value cannot be zero"):
            calculate_growth_rate(0, 1000, 1)
    
    def test_convert_currency_basic(self):
        """Test basic currency conversion"""
        amount = 100
        from_currency = "USD"
        to_currency = "EUR"
        exchange_rates = {"USD": 1.0, "EUR": 0.85}
        
        converted = convert_currency(amount, from_currency, to_currency, exchange_rates)
        assert converted == 85.0
    
    def test_convert_currency_same_currency(self):
        """Test currency conversion with same currency"""
        amount = 100
        currency = "USD"
        exchange_rates = {"USD": 1.0}
        
        converted = convert_currency(amount, currency, currency, exchange_rates)
        assert converted == 100.0
    
    def test_convert_currency_missing_rate(self):
        """Test currency conversion with missing exchange rate"""
        amount = 100
        exchange_rates = {"USD": 1.0}
        
        with pytest.raises(ValueError, match="Exchange rate not found"):
            convert_currency(amount, "USD", "EUR", exchange_rates)
    
    def test_calculate_compound_interest(self):
        """Test compound interest calculation"""
        principal = 1000
        rate = 0.05  # 5%
        periods = 2
        compounding_frequency = 1  # Annual
        
        result = calculate_compound_interest(principal, rate, periods, compounding_frequency)
        expected = 1000 * (1 + 0.05/1) ** (1 * 2)
        assert abs(result - expected) < 0.01
    
    def test_calculate_compound_interest_monthly(self):
        """Test compound interest with monthly compounding"""
        principal = 1000
        rate = 0.12  # 12% annual
        periods = 1
        compounding_frequency = 12  # Monthly
        
        result = calculate_compound_interest(principal, rate, periods, compounding_frequency)
        expected = 1000 * (1 + 0.12/12) ** (12 * 1)
        assert abs(result - expected) < 0.01
    
    def test_calculate_present_value(self):
        """Test present value calculation"""
        future_value = 1100
        discount_rate = 0.10
        periods = 1
        
        pv = calculate_present_value(future_value, discount_rate, periods)
        expected = 1100 / (1 + 0.10) ** 1
        assert abs(pv - expected) < 0.01
    
    def test_calculate_future_value(self):
        """Test future value calculation"""
        present_value = 1000
        interest_rate = 0.10
        periods = 1
        
        fv = calculate_future_value(present_value, interest_rate, periods)
        expected = 1000 * (1 + 0.10) ** 1
        assert abs(fv - expected) < 0.01
    
    def test_calculate_break_even_basic(self):
        """Test break-even calculation"""
        fixed_costs = 10000
        variable_cost_per_unit = 5
        price_per_unit = 15
        
        break_even = calculate_break_even(fixed_costs, variable_cost_per_unit, price_per_unit)
        expected = fixed_costs / (price_per_unit - variable_cost_per_unit)
        assert break_even == expected
    
    def test_calculate_break_even_zero_margin(self):
        """Test break-even with zero contribution margin"""
        fixed_costs = 10000
        variable_cost_per_unit = 15
        price_per_unit = 15
        
        with pytest.raises(ValueError, match="Price per unit must be greater than variable cost"):
            calculate_break_even(fixed_costs, variable_cost_per_unit, price_per_unit)
    
    def test_validate_financial_input_positive(self):
        """Test financial input validation with positive number"""
        assert validate_financial_input(100.50) == True
        assert validate_financial_input("100.50") == True
    
    def test_validate_financial_input_negative(self):
        """Test financial input validation with negative number"""
        assert validate_financial_input(-100) == False
        assert validate_financial_input("-100") == False
    
    def test_validate_financial_input_zero(self):
        """Test financial input validation with zero"""
        assert validate_financial_input(0) == True
        assert validate_financial_input("0") == True
    
    def test_validate_financial_input_invalid(self):
        """Test financial input validation with invalid input"""
        assert validate_financial_input("abc") == False
        assert validate_financial_input(None) == False
        assert validate_financial_input("") == False
    
    def test_format_currency_usd(self):
        """Test USD currency formatting"""
        formatted = format_currency(1234.56, "USD")
        assert formatted == "$1,234.56"
    
    def test_format_currency_eur(self):
        """Test EUR currency formatting"""
        formatted = format_currency(1234.56, "EUR")
        assert formatted == "€1,234.56"
    
    def test_format_currency_negative(self):
        """Test negative currency formatting"""
        formatted = format_currency(-1234.56, "USD")
        assert formatted == "-$1,234.56"
    
    def test_format_currency_zero(self):
        """Test zero currency formatting"""
        formatted = format_currency(0, "USD")
        assert formatted == "$0.00"

class TestFinancialCalculatorEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_large_numbers(self):
        """Test calculations with very large numbers"""
        large_revenue = 1e12  # 1 trillion
        large_costs = 8e11   # 800 billion
        
        margin = calculate_profit_margin(large_revenue, large_costs)
        assert margin == 20.0
    
    def test_small_numbers(self):
        """Test calculations with very small numbers"""
        small_revenue = 0.01
        small_costs = 0.008
        
        margin = calculate_profit_margin(small_revenue, small_costs)
        assert margin == 20.0
    
    def test_decimal_precision(self):
        """Test calculations with high precision decimals"""
        revenue = Decimal('1000.123456789')
        costs = Decimal('800.987654321')
        
        # Convert to float for calculation
        margin = calculate_profit_margin(float(revenue), float(costs))
        expected = ((float(revenue) - float(costs)) / float(revenue)) * 100
        assert abs(margin - expected) < 0.000001
    
    def test_infinity_handling(self):
        """Test handling of infinity values"""
        with pytest.raises((ValueError, OverflowError)):
            calculate_compound_interest(float('inf'), 0.05, 1, 1)
    
    def test_nan_handling(self):
        """Test handling of NaN values"""
        with pytest.raises((ValueError, TypeError)):
            calculate_profit_margin(float('nan'), 100)

class TestFinancialCalculatorIntegration:
    """Integration tests combining multiple calculations"""
    
    def test_complete_financial_analysis(self, financial_data_samples):
        """Test complete financial analysis workflow"""
        revenues = financial_data_samples['revenues']
        costs = financial_data_samples['costs']
        
        # Calculate multiple metrics
        total_revenue = sum(revenues)
        total_costs = sum(costs)
        profit_margin = calculate_profit_margin(total_revenue, total_costs)
        net_cash_flow = calculate_cash_flow(revenues, costs)
        roi = calculate_roi(total_costs, total_revenue)
        
        # Validate results
        assert profit_margin > 0
        assert net_cash_flow > 0
        assert roi > 0
        assert total_revenue > total_costs
    
    def test_currency_conversion_workflow(self, financial_data_samples):
        """Test multi-currency financial calculations"""
        exchange_rates = financial_data_samples['exchange_rates']
        
        # Convert revenues to different currencies
        usd_revenue = 1000
        eur_revenue = convert_currency(usd_revenue, 'USD', 'EUR', exchange_rates)
        gbp_revenue = convert_currency(usd_revenue, 'USD', 'GBP', exchange_rates)
        
        # Validate conversions
        assert eur_revenue < usd_revenue  # EUR is worth less
        assert gbp_revenue < usd_revenue  # GBP is worth less
        assert eur_revenue > gbp_revenue  # EUR is worth more than GBP
    
    def test_time_series_calculations(self, financial_data_samples):
        """Test calculations over time series data"""
        revenues = financial_data_samples['revenues']
        
        # Calculate period-over-period growth rates
        growth_rates = []
        for i in range(1, len(revenues)):
            growth_rate = calculate_growth_rate(revenues[i-1], revenues[i], 1)
            growth_rates.append(growth_rate)
        
        # Validate growth rates
        assert len(growth_rates) == len(revenues) - 1
        assert all(isinstance(rate, (int, float)) for rate in growth_rates)

@pytest.mark.performance
class TestFinancialCalculatorPerformance:
    """Performance tests for financial calculations"""
    
    def test_bulk_calculations_performance(self, performance_monitor):
        """Test performance of bulk calculations"""
        performance_monitor.start()
        
        # Perform many calculations
        for i in range(10000):
            calculate_profit_margin(1000 + i, 800 + i)
        
        performance_monitor.assert_max_duration(1.0)  # Should complete in < 1 second
    
    def test_currency_conversion_performance(self, performance_monitor):
        """Test currency conversion performance"""
        exchange_rates = {f'CURR{i}': 1.0 + (i * 0.1) for i in range(100)}
        
        performance_monitor.start()
        
        # Perform many conversions
        for i in range(1000):
            from_curr = f'CURR{i % 50}'
            to_curr = f'CURR{(i + 1) % 50}'
            convert_currency(100, from_curr, to_curr, exchange_rates)
        
        performance_monitor.assert_max_duration(0.5)  # Should complete in < 0.5 seconds
