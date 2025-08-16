import os
import pandas as pd
import pyairtable
from dotenv import load_dotenv

load_dotenv()

# Load environment variables
api_key = os.getenv('AIRTABLE_API_KEY')
base_id = os.getenv('AIRTABLE_BASE_ID')
table_name = os.getenv('AIRTABLE_TABLE_NAME')

def fetch_airtable():
    """Fetch data from Airtable and return DataFrame with status"""
    try:
        if not all([api_key, base_id, table_name]):
            return pd.DataFrame(), "Error: Missing Airtable credentials"
        
        # Initialize Airtable connection
        table = pyairtable.Table(api_key, base_id, table_name)
        
        # Fetch all records
        records = table.all()
        
        if not records:
            return pd.DataFrame(), "Error: No records found"
        
        # Convert to DataFrame
        df = pd.DataFrame([r['fields'] for r in records])
        
        # Extract leads/sales columns
        total_leads = len(df)
        
        # Count MQLs if Type column exists
        mql_count = 0
        if 'Type' in df.columns:
            mql_count = len(df[df['Type'] == 'MQL'])
        
        status = f"Connected - {total_leads} records, {mql_count} MQLs"
        return df, status
        
    except Exception as e:
        return pd.DataFrame(), f"Error: {str(e)}"

def get_airtable_data():
    """Fetch data from Airtable - fallback to mock data if connection fails"""
    df, status = fetch_airtable()
    
    if df.empty:
        # Return mock data as fallback
        return {
            'leads': [
                {'name': 'Company A', 'value': 15000, 'status': 'qualified'},
                {'name': 'Company B', 'value': 8500, 'status': 'contacted'},
                {'name': 'Company C', 'value': 22000, 'status': 'proposal'},
                {'name': 'Company D', 'value': 12000, 'status': 'negotiation'}
            ]
        }
    
    # Convert DataFrame to leads format
    leads = []
    for _, row in df.iterrows():
        lead = {
            'name': row.get('Company', row.get('Name', f'Lead {len(leads)+1}')),
            'value': row.get('Value', row.get('Deal_Size', 0)),
            'status': row.get('Status', row.get('Stage', 'unknown'))
        }
        leads.append(lead)
    
    return {'leads': leads}

def get_lead_metrics():
    """Get lead metrics summary"""
    data = get_airtable_data()
    leads = data['leads']
    
    total_value = sum(lead['value'] for lead in leads)
    qualified_count = len([lead for lead in leads if lead['status'] == 'qualified'])
    
    return {
        'total_leads': len(leads),
        'total_value': total_value,
        'qualified_leads': qualified_count,
        'avg_lead_value': total_value / len(leads) if leads else 0
    }
