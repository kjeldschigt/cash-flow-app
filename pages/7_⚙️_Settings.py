import streamlit as st
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.storage import save_settings_to_db, load_settings

st.title("App Settings")

# Load existing settings from database
try:
    saved_settings = load_settings()
except:
    saved_settings = {}

# Theme Section
st.subheader("🎨 Theme")
with st.container():
    theme = st.selectbox(
        "Application Theme", 
        ["Light", "Dark"], 
        index=0 if saved_settings.get('theme', 'light') == 'light' else 1,
        help="Changes the visual theme across all pages"
    )
    
    if theme == "Light":
        st.session_state.theme = "light"
        st.markdown('''
        <style>
        .stApp { background-color: #FAFAFA; color: #333; }
        .stSidebar { background-color: #F0F2F6; }
        </style>
        ''', unsafe_allow_html=True)
    else:
        st.session_state.theme = "dark"
        st.markdown('''
        <style>
        .stApp { background-color: #0E1117; color: #FAFAFA; }
        .stSidebar { background-color: #262730; }
        </style>
        ''', unsafe_allow_html=True)
    
    st.info(f"Current theme: **{theme}** - Applied app-wide")

# Business Metrics Defaults Section
st.subheader("📊 Business Metrics Defaults")
with st.container():
    st.write("Set default values for business metrics used across dashboards")
    
    col1, col2 = st.columns(2)
    
    with col1:
        occupancy = st.number_input(
            "Default Occupancy %", 
            value=float(saved_settings.get('occupancy', 75.0)), 
            min_value=0.0, 
            max_value=100.0, 
            step=0.1,
            help="Default occupancy rate for calculations"
        )
        total_leads = st.number_input(
            "Default Total Leads", 
            value=int(saved_settings.get('total_leads', 100)), 
            min_value=0, 
            step=1,
            help="Default number of leads per period"
        )
    
    with col2:
        mql = st.number_input(
            "Marketing Qualified Leads (MQL)", 
            value=int(saved_settings.get('mql', 50)), 
            min_value=0, 
            step=1,
            help="Default MQL count"
        )
        sql = st.number_input(
            "Sales Qualified Leads (SQL)", 
            value=int(saved_settings.get('sql', 20)), 
            min_value=0, 
            step=1,
            help="Default SQL count"
        )

# Save business metrics to session state
st.session_state.occupancy = occupancy
st.session_state.total_leads = total_leads
st.session_state.mql = mql
st.session_state.sql = sql

# Cost Levers Section
st.subheader("💰 Cost Levers")
with st.container():
    st.write("Configure cost parameters used in Costs and Scenarios analysis")
    
    # Costa Rica Operations
    st.write("**🇨🇷 Costa Rica Operations:**")
    col1, col2 = st.columns(2)
    with col1:
        costa_usd = st.number_input(
            "Costa Rica Cost (USD)", 
            value=float(saved_settings.get('costa_usd', 19000.0)), 
            min_value=0.0, 
            step=100.0,
            help="Monthly operational costs in USD"
        )
    with col2:
        costa_crc = st.number_input(
            "Costa Rica Cost (CRC)", 
            value=float(saved_settings.get('costa_crc', 38000000.0)), 
            min_value=0.0, 
            step=1000.0,
            help="Monthly operational costs in Costa Rican Colones"
        )
    
    # Hong Kong Operations
    st.write("**🇭🇰 Hong Kong Operations:**")
    hk_usd = st.number_input(
        "Hong Kong Cost (USD)", 
        value=float(saved_settings.get('hk_usd', 40000.0)), 
        min_value=0.0, 
        step=100.0,
        help="Monthly operational costs in USD"
    )
    
    # Financial Settings
    st.write("**💳 Financial Settings:**")
    col1, col2 = st.columns(2)
    with col1:
        stripe_fee = st.number_input(
            "Stripe Processing Fee %", 
            value=float(saved_settings.get('stripe_fee', 4.2)), 
            min_value=0.0, 
            max_value=10.0, 
            step=0.1,
            help="Payment processing fee percentage"
        )
        huub_principal = st.number_input(
            "Huub Loan Principal", 
            value=float(saved_settings.get('huub_principal', 1250000.0)), 
            min_value=0.0, 
            step=1000.0,
            help="Outstanding loan principal amount"
        )
    with col2:
        huub_interest = st.number_input(
            "Huub Loan Interest (Monthly)", 
            value=float(saved_settings.get('huub_interest', 18750.0)), 
            min_value=0.0, 
            step=100.0,
            help="Monthly interest payment"
        )
        google_ads = st.number_input(
            "Google Ads Spend (USD)", 
            value=float(saved_settings.get('google_ads', 27500.0)), 
            min_value=0.0, 
            step=100.0,
            help="Monthly advertising spend"
        )

# Save cost configurations to session state
st.session_state.costa_usd = costa_usd
st.session_state.costa_crc = costa_crc
st.session_state.hk_usd = hk_usd
st.session_state.stripe_fee = stripe_fee
st.session_state.huub_principal = huub_principal
st.session_state.huub_interest = huub_interest
st.session_state.google_ads = google_ads

# Settings summary
st.subheader("Current Settings Summary")

col1, col2, col3 = st.columns(3)

with col1:
    st.write("**Business Metrics:**")
    st.write(f"• Occupancy: {occupancy}%")
    st.write(f"• Total Leads: {total_leads}")
    st.write(f"• MQL: {mql}")
    st.write(f"• SQL: {sql}")

with col2:
    st.write("**Regional Costs:**")
    st.write(f"• Costa Rica USD: ${costa_usd:,.0f}")
    st.write(f"• Costa Rica CRC: ₡{costa_crc:,.0f}")
    st.write(f"• Hong Kong USD: ${hk_usd:,.0f}")

with col3:
    st.write("**Financial Settings:**")
    st.write(f"• Stripe Fee: {stripe_fee}%")
    st.write(f"• Huub Principal: ${huub_principal:,.0f}")
    st.write(f"• Huub Interest: ${huub_interest:,.0f}")
    st.write(f"• Google Ads: ${google_ads:,.0f}")

# Save Changes Section
st.subheader("💾 Save Changes")
st.write("Persist all settings to database and session state for use across the application")

col1, col2, col3 = st.columns([1, 1, 2])

with col1:
    if st.button("Save Changes", type="primary"):
        try:
            # Prepare settings data
            settings_data = {
                'theme': st.session_state.get('theme', 'light'),
                'occupancy': occupancy,
                'total_leads': total_leads,
                'mql': mql,
                'sql': sql,
                'costa_usd': costa_usd,
                'costa_crc': costa_crc,
                'hk_usd': hk_usd,
                'stripe_fee': stripe_fee,
                'huub_principal': huub_principal,
                'huub_interest': huub_interest,
                'google_ads': google_ads
            }
            
            # Save to database
            save_settings_to_db(settings_data)
            st.success("Settings saved successfully to database!")
            st.session_state.settings_saved = True
            
        except Exception as e:
            st.error(f"Error saving settings: {str(e)}")

with col2:
    if st.button("Reset to Defaults", type="secondary"):
        # Reset all values to defaults
        st.session_state.clear()
        st.success("Settings reset to defaults!")
        st.rerun()

with col3:
    if st.session_state.get('settings_saved', False):
        st.success("✅ Settings are saved")
    else:
        st.info("💾 Changes not saved to database")

# Advanced Settings
with st.expander("Advanced Settings"):
    st.write("**Database Configuration:**")
    
    col1, col2 = st.columns(2)
    with col1:
        auto_save = st.checkbox("Auto-save changes", value=True)
        backup_enabled = st.checkbox("Enable daily backups", value=True)
    
    with col2:
        data_retention = st.number_input("Data retention (days)", value=365, min_value=30, max_value=2555)
        cache_timeout = st.number_input("Cache timeout (minutes)", value=30, min_value=1, max_value=1440)
    
    st.session_state.auto_save = auto_save
    st.session_state.backup_enabled = backup_enabled
    st.session_state.data_retention = data_retention
    st.session_state.cache_timeout = cache_timeout
    
    st.write("**API Configuration:**")
    
    api_timeout = st.number_input("API timeout (seconds)", value=30, min_value=5, max_value=300)
    max_retries = st.number_input("Max API retries", value=3, min_value=1, max_value=10)
    
    st.session_state.api_timeout = api_timeout
    st.session_state.max_retries = max_retries

# Export/Import Settings
st.subheader("Settings Management")

col1, col2 = st.columns(2)

with col1:
    if st.button("Export Settings", type="secondary"):
        import json
        
        export_data = {
            'theme': st.session_state.get('theme', 'light'),
            'business_metrics': {
                'occupancy': occupancy,
                'total_leads': total_leads,
                'mql': mql,
                'sql': sql
            },
            'cost_config': {
                'costa_usd': costa_usd,
                'costa_crc': costa_crc,
                'hk_usd': hk_usd,
                'stripe_fee': stripe_fee,
                'huub_principal': huub_principal,
                'huub_interest': huub_interest,
                'google_ads': google_ads
            }
        }
        
        st.download_button(
            label="Download settings.json",
            data=json.dumps(export_data, indent=2),
            file_name="cash_flow_settings.json",
            mime="application/json"
        )

with col2:
    uploaded_file = st.file_uploader("Import Settings", type=['json'])
    if uploaded_file is not None:
        try:
            import json
            settings = json.load(uploaded_file)
            
            if st.button("Apply Imported Settings"):
                # Apply imported settings to session state
                for key, value in settings.items():
                    if isinstance(value, dict):
                        for sub_key, sub_value in value.items():
                            st.session_state[sub_key] = sub_value
                    else:
                        st.session_state[key] = value
                
                st.success("Settings imported successfully!")
                st.rerun()
                
        except Exception as e:
            st.error(f"Error importing settings: {str(e)}")
