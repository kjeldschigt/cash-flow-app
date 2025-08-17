import os
import pandas as pd
import stripe
from dotenv import load_dotenv
from utils.error_handler import show_error, handle_api_error, ensure_dataframe_columns
from datetime import datetime, timedelta
import time

load_dotenv()

# Load Stripe API key
stripe.api_key = os.getenv('STRIPE_API_KEY')

def start_timestamp(range_type):
    """Calculate start timestamp for different date ranges"""
    now = datetime.now()
    
    if range_type.lower() == "ytd":
        start_date = datetime(now.year, 1, 1)
    elif range_type.lower() == "last 12m":
        start_date = now - timedelta(days=365)
    elif range_type.lower() == "qtd":
        quarter = (now.month - 1) // 3 + 1
        start_date = datetime(now.year, (quarter - 1) * 3 + 1, 1)
    elif range_type.lower() == "last 7d":
        start_date = now - timedelta(days=7)
    elif range_type.lower() == "ytd vs ly":
        start_date = datetime(now.year, 1, 1)
    else:
        start_date = datetime(now.year, 1, 1)  # Default to YTD
    
    return int(start_date.timestamp())

def fetch_stripe_payments(range_type="ytd"):
    """Fetch payments from Stripe with date range filtering"""
    try:
        if not stripe.api_key or stripe.api_key == 'sk_live_XXXXXXXX':
            return get_mock_stripe_data(range_type), "Error: Missing or invalid Stripe API key"
        
        # Get start timestamp for range
        start_ts = start_timestamp(range_type)
        
        # Fetch charges from Stripe
        charges = stripe.Charge.list(
            limit=100,
            created={'gte': start_ts}
        )
        
        if not charges.data:
            return pd.DataFrame(), "Error: No charges found"
        
        # Convert to DataFrame
        df = pd.DataFrame([{
            'amount': c['amount'] / 100,  # Convert from cents to dollars
            'date': datetime.fromtimestamp(c['created']),
            'status': c['status'],
            'currency': c['currency']
        } for c in charges.data])
        
        # Calculate metrics
        gross_volume = df['amount'].sum()
        fee_pct = 0.029  # Stripe standard fee ~2.9%
        net_sales = gross_volume * (1 - fee_pct)
        spend_per_customer = gross_volume / df.shape[0] if df.shape[0] > 0 else 0
        
        status = f"Connected - {len(df)} charges, ${gross_volume:,.0f} gross volume"
        return df, status
        
    except stripe.error.AuthenticationError as e:
        return handle_api_error(e, "Stripe", get_mock_stripe_data(range_type)), "Authentication Error: Check API key"
    except stripe.error.APIConnectionError as e:
        return handle_api_error(e, "Stripe", get_mock_stripe_data(range_type)), "Connection Error: Check internet connection"
    except Exception as e:
        return handle_api_error(e, "Stripe", get_mock_stripe_data(range_type)), f"Error: {str(e)}"

def get_mock_stripe_data(range_type="ytd"):
    """Generate mock Stripe data for testing"""
    now = datetime.now()
    start_date = datetime.fromtimestamp(start_timestamp(range_type))
    
    # Generate mock data points
    dates = pd.date_range(start=start_date, end=now, freq='D')
    mock_data = []
    
    for date in dates[-30:]:  # Last 30 days of range
        if date.weekday() < 5:  # Weekdays only
            amount = 1500 + (date.day * 50)  # Varying amounts
            mock_data.append({
                'amount': amount,
                'date': date,
                'status': 'succeeded',
                'currency': 'usd'
            })
    
    return pd.DataFrame(mock_data)

def get_stripe_payments():
    """Fetch payments from Stripe - fallback to mock data"""
    df, status = fetch_stripe_payments()
    
    if df.empty:
        # Return mock data as fallback
        return [
            {'payment_id': 'pi_1234', 'amount': 2500, 'currency': 'usd', 'status': 'succeeded'},
            {'payment_id': 'pi_5678', 'amount': 1800, 'currency': 'usd', 'status': 'succeeded'},
            {'payment_id': 'pi_9012', 'amount': 3200, 'currency': 'usd', 'status': 'pending'},
            {'payment_id': 'pi_3456', 'amount': 4100, 'currency': 'usd', 'status': 'succeeded'}
        ]
    
    # Convert DataFrame to list format for compatibility
    return df.to_dict('records')

def get_payment_metrics():
    """Get payment metrics summary"""
    payments = get_stripe_payments()
    
    succeeded_payments = [p for p in payments if p['status'] == 'succeeded']
    total_succeeded = sum(p['amount'] for p in succeeded_payments)
    
    return {
        'total_payments': len(payments),
        'succeeded_payments': len(succeeded_payments),
        'total_amount': total_succeeded,
        'avg_payment': total_succeeded / len(succeeded_payments) if succeeded_payments else 0
    }
