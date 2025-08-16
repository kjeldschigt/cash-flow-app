import pandas as pd
import streamlit as st
from .storage import load_fx_rates

def get_fx_rates():
    """Get FX rates data"""
    return load_fx_rates()

def get_monthly_rate(month, scenario='Base_CRC_USD'):
    """Get FX rate for specific month and scenario"""
    fx_df = get_fx_rates()
    rate_row = fx_df[fx_df['Month'] == month]
    if not rate_row.empty:
        return rate_row[scenario].iloc[0]
    return 520  # Default fallback rate

def convert_crc_to_usd(crc_amount, rate):
    """Convert CRC to USD using given rate"""
    return crc_amount / rate

def get_rate_scenarios():
    """Get available rate scenarios"""
    return ['Low_CRC_USD', 'Base_CRC_USD', 'High_CRC_USD']

def get_yearly_fx_rates():
    """Get per-year FX rate inputs for projections"""
    years = [1, 2, 3, 4, 5]
    default_rates = [502, 510, 520, 520, 530]
    
    fx_rates = {}
    for i, year in enumerate(years):
        fx_rates[year] = st.number_input(
            f"CRC/USD Year {year}", 
            value=default_rates[i],
            min_value=400.0,
            max_value=700.0,
            step=1.0,
            key=f"fx_year_{year}"
        )
    
    return fx_rates

def convert_crc_costs_by_year(crc_amount, year_fx_rates):
    """Convert CRC costs using year-specific FX rates"""
    conversions = {}
    for year, rate in year_fx_rates.items():
        conversions[year] = crc_amount / rate
    return conversions

def calculate_fx_impact_table(crc_amount, year_fx_rates, base_year=1):
    """Calculate FX impact table showing costs under each rate with deltas"""
    conversions = convert_crc_costs_by_year(crc_amount, year_fx_rates)
    base_amount = conversions[base_year]
    
    impact_data = []
    for year in sorted(year_fx_rates.keys()):
        usd_amount = conversions[year]
        delta = usd_amount - base_amount
        delta_pct = (delta / base_amount * 100) if base_amount > 0 else 0
        
        impact_data.append({
            'Year': year,
            'FX Rate (CRC/USD)': year_fx_rates[year],
            'Cost (USD)': usd_amount,
            'Delta vs Year 1': delta,
            'Delta %': f"{delta_pct:+.1f}%"
        })
    
    return pd.DataFrame(impact_data)

def apply_fx_conversion(df, rate_column='Base_CRC_USD', crc_column='Costs_CRC'):
    """Apply FX conversion to dataframe"""
    fx_df = get_fx_rates()
    
    # Create a copy to avoid modifying original
    result_df = df.copy()
    
    # Extract month from Date column for matching
    result_df['Month'] = result_df['Date'].dt.strftime('%Y-%m')
    
    # Merge with FX rates
    merged = pd.merge(result_df, fx_df, on='Month', how='left')
    
    # Apply conversion
    if crc_column in merged.columns:
        merged['Costs_USD_From_CRC'] = merged[crc_column] / merged[rate_column]
    
    # Clean up temporary columns
    merged = merged.drop('Month', axis=1)
    
    return merged
