import streamlit as st
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.theme_manager import get_current_theme, apply_theme
from src.services.settings_service import get_setting, set_setting, get_all_settings
try:
    from src.ui.enhanced_auth import require_auth, get_current_user
    AUTH_AVAILABLE = True
except Exception:
    AUTH_AVAILABLE = False
    # Fallback stubs (dev mode only)
    def require_auth(min_role=None):
        return True
    def get_current_user():
        return {"email": "dev@example.com"}
from src.models.user import UserRole
from src.services.error_handler import ErrorHandler, handle_error
from src.container import get_bank_service
from datetime import date
import traceback
from src.services.airtable_import_service import (
    import_leads,
    import_bookings,
    fetch_all_leads,
    fetch_all_bookings,
    save_leads_to_db,
    save_bookings_to_db,
    parse_csv_leads,
    parse_csv_bookings,
    parse_csv_leads_with_diagnostics,
    parse_csv_bookings_with_diagnostics,
)
from src.config.settings import Settings
from src.repositories.base import DatabaseConnection

# UserRole fallback for development mode
if AUTH_AVAILABLE is False:
    UserRole = type("UserRole", (), {"ADMIN": "ADMIN"})

# Development override: always allow access even if session is missing
try:
    current_user = get_current_user()
except Exception:
    current_user = None

if not current_user:
    # In development mode fallback to a fake admin user
    current_user = {"email": "dev@example.com", "role": "ADMIN"}
    AUTH_AVAILABLE = False

st.title("⚙️ Settings")

# Create main navigation tabs
user_role = getattr(current_user, 'role', UserRole.ADMIN) if AUTH_AVAILABLE else UserRole.ADMIN
if user_role == UserRole.ADMIN:
    tab1, tab2, tab3 = st.tabs(
        ["🎛️ Application Settings", "🔌 Service Integrations", "📊 System Info"]
    )
else:
    tab1, tab3 = st.tabs(["🎛️ Application Settings", "📊 System Info"])
    tab2 = None

# Service Integrations Tab (Admin only)
if tab2 and user_role == UserRole.ADMIN:
    with tab2:
        if AUTH_AVAILABLE:
            try:
                from src.ui.enhanced_service_integrations import (
                    render_enhanced_service_integrations,
                )
                render_enhanced_service_integrations()
            except Exception as e:
                st.info("🔧 API Key Management UI is not available (error loading module).")
                if st.checkbox("Show technical details"):
                    st.code(f"Error: {str(e)}")
        else:
            st.info("🔧 API Key Management is disabled in local development mode (no session middleware).")

# Application Settings Tab
with tab1:
    # Theme toggle
    current_theme = get_current_theme()
    theme_options = {"Light": "light", "Dark": "dark"}
    selected_theme = st.radio(
        "Select Theme",
        options=list(theme_options.keys()),
        index=list(theme_options.keys()).index(
            "Light" if current_theme == "light" else "Dark"
        ),
    )
    if st.button("Apply Theme"):
        apply_theme(theme_options[selected_theme])

st.divider()

# Load existing settings from database
try:
    saved_settings = get_all_settings()
except Exception as e:
    error_handler = ErrorHandler()
    error_handler.handle_error(e, "Failed to load settings")
    saved_settings = {}

    # Cost Defaults Section
    st.subheader("💸 Cost Defaults")
    with st.container():
        st.write("Set default values for cost calculations and FX rates")

        col1, col2 = st.columns(2)

        with col1:
            # Cost-related defaults
            google_ads = st.number_input(
                "Google Ads (Monthly)",
                value=float(saved_settings.get("google_ads", 5000.0)),
                min_value=0.0,
                step=100.0,
                help="Default monthly Google Ads spend",
            )
            if google_ads != saved_settings.get("google_ads", 5000.0):
                set_setting("google_ads", google_ads)

            huub_principal = st.number_input(
                "Huub Principal Payment",
                value=float(saved_settings.get("huub_principal", 10000.0)),
                min_value=0.0,
                step=500.0,
                help="Default Huub principal payment",
            )
            if huub_principal != saved_settings.get("huub_principal", 10000.0):
                set_setting("huub_principal", huub_principal)

            huub_interest = st.number_input(
                "Huub Interest Payment",
                value=float(saved_settings.get("huub_interest", 2000.0)),
                min_value=0.0,
                step=100.0,
                help="Default Huub interest payment",
            )
            if huub_interest != saved_settings.get("huub_interest", 2000.0):
                set_setting("huub_interest", huub_interest)

        with col2:
            # FX rates
            usd_cad_rate = st.number_input(
                "USD/CAD Exchange Rate",
                value=float(saved_settings.get("usd_cad_rate", 1.35)),
                min_value=0.0,
                step=0.01,
                help="Default USD to CAD exchange rate",
            )
            if usd_cad_rate != saved_settings.get("usd_cad_rate", 1.35):
                set_setting("usd_cad_rate", usd_cad_rate)

            occupancy = st.number_input(
                "Default Occupancy %",
                value=float(saved_settings.get("occupancy", 75.0)),
                min_value=0.0,
                max_value=100.0,
                step=0.1,
                help="Default occupancy rate for calculations",
            )
            if occupancy != saved_settings.get("occupancy", 75.0):
                set_setting("occupancy", occupancy)

            total_leads = st.number_input(
                "Default Total Leads",
                value=int(saved_settings.get("total_leads", 100)),
                min_value=0,
                step=1,
                help="Default total leads count",
            )
            if total_leads != saved_settings.get("total_leads", 100):
                set_setting("total_leads", total_leads)

            mql = st.number_input(
                "Marketing Qualified Leads (MQL)",
                value=int(saved_settings.get("mql", 50)),
                min_value=0,
                step=1,
                help="Default MQL count",
            )
            if mql != saved_settings.get("mql", 50):
                set_setting("mql", mql)

            sql = st.number_input(
                "Sales Qualified Leads (SQL)",
                value=int(saved_settings.get("sql", 25)),
                min_value=0,
                step=1,
                help="Default SQL count",
            )
            if sql != saved_settings.get("sql", 25):
                set_setting("sql", sql)

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
                value=float(saved_settings.get("costa_usd", 19000.0)),
                min_value=0.0,
                step=100.0,
                help="Monthly operational costs in USD",
            )
        with col2:
            costa_crc = st.number_input(
                "Costa Rica Cost (CRC)",
                value=float(saved_settings.get("costa_crc", 38000000.0)),
                min_value=0.0,
                step=1000.0,
                help="Monthly operational costs in Costa Rican Colones",
            )

    # Hong Kong Operations
    st.write("**🇭🇰 Hong Kong Operations:**")
    hk_usd = st.number_input(
        "Hong Kong Cost (USD)",
        value=float(saved_settings.get("hk_usd", 40000.0)),
        min_value=0.0,
        step=100.0,
        help="Monthly operational costs in USD",
    )

    # Financial Settings
    st.write("**💳 Financial Settings:**")
    col1, col2 = st.columns(2)
    with col1:
        stripe_fee = st.number_input(
            "Stripe Processing Fee %",
            value=float(saved_settings.get("stripe_fee", 4.2)),
            min_value=0.0,
            max_value=10.0,
            step=0.1,
            help="Payment processing fee percentage",
        )
        huub_principal = st.number_input(
            "Huub Loan Principal",
            value=float(saved_settings.get("huub_principal", 1250000.0)),
            min_value=0.0,
            step=1000.0,
            help="Outstanding loan principal amount",
        )
    with col2:
        huub_interest = st.number_input(
            "Huub Loan Interest (Monthly)",
            value=float(saved_settings.get("huub_interest", 18750.0)),
            min_value=0.0,
            step=100.0,
            help="Monthly interest payment",
        )
        google_ads = st.number_input(
            "Google Ads Spend (USD)",
            value=float(saved_settings.get("google_ads", 27500.0)),
            min_value=0.0,
            step=100.0,
            help="Monthly advertising spend",
        )


# Save cost configurations to session state (only if defined)
if "costa_usd" in locals():
    st.session_state.costa_usd = costa_usd
if "costa_crc" in locals():
    st.session_state.costa_crc = costa_crc
if "hk_usd" in locals():
    st.session_state.hk_usd = hk_usd
if "stripe_fee" in locals():
    st.session_state.stripe_fee = stripe_fee
if "huub_principal" in locals():
    st.session_state.huub_principal = huub_principal
if "huub_interest" in locals():
    st.session_state.huub_interest = huub_interest
if "google_ads" in locals():
    st.session_state.google_ads = google_ads

# Settings summary
st.subheader("Current Settings Summary")

col1, col2, col3 = st.columns(3)

with col1:
    st.write("**Business Metrics:**")
    st.write(f"• Occupancy: {st.session_state.get('occupancy', 'N/A')}%")
    st.write(f"• Total Leads: {st.session_state.get('total_leads', 'N/A')}")
    st.write(f"• MQL: {st.session_state.get('mql', 'N/A')}")

with col2:
    st.write("**Regional Costs:**")
    st.write(f"• Costa Rica USD: ${st.session_state.get('costa_usd', 0):,.0f}")
    st.write(f"• Costa Rica CRC: ₡{st.session_state.get('costa_crc', 0):,.0f}")
    st.write(f"• Hong Kong USD: ${st.session_state.get('hk_usd', 0):,.0f}")

with col3:
    st.write("**Financial Settings:**")
    st.write(f"• Stripe Fee: {st.session_state.get('stripe_fee', 0)}%")
    st.write(f"• Huub Principal: ${st.session_state.get('huub_principal', 0):,.0f}")
    st.write(f"• Huub Interest: ${st.session_state.get('huub_interest', 0):,.0f}")
    st.write(f"• Google Ads: ${st.session_state.get('google_ads', 0):,.0f}")

# Save Changes Section
st.subheader("💾 Save Changes")
st.write(
    "Persist all settings to database and session state for use across the application"
)

col1, col2, col3 = st.columns([1, 1, 2])

with col1:
    if st.button("Save Changes", type="primary"):
        try:
            # Get values from session state with fallbacks
            hk_usd = st.session_state.get("hk_usd", 0)
            costa_usd = st.session_state.get("costa_usd", 0)
            
            # Prepare settings data
            settings_data = {
                "theme": st.session_state.get("theme", "light"),
                "occupancy": occupancy,
                "total_leads": total_leads,
                "mql": mql,
                "sql": sql,
                "costa_usd": costa_usd,
                "costa_crc": costa_crc,
                "hk_usd": hk_usd,
                "stripe_fee": stripe_fee,
                "huub_principal": huub_principal,
                "huub_interest": huub_interest,
                "google_ads": google_ads,
            }

            # Save to database
            from src.services.settings_service import save_settings_to_db

            save_settings_to_db(settings_data)
            st.success("Settings saved successfully to database!")
            
        except Exception as e:
            from src.services.error_handler import ErrorHandler
            error_handler = ErrorHandler()
            error_handler.handle_error(e, "Failed to save settings")

# Update session state after save attempt (only if those variables exist)
if "costa_usd" in locals():
    st.session_state.costa_usd = costa_usd
if "hk_usd" in locals():
    st.session_state.hk_usd = hk_usd

with col2:
    if st.button("Reset to Defaults", type="secondary"):
        # Reset all values to defaults
        st.session_state.clear()
        st.success("Settings reset to defaults!")
        st.session_state.settings_reset = True

with col3:
    if st.session_state.get("settings_saved", False):
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
        data_retention = st.number_input(
            "Data retention (days)", value=365, min_value=30, max_value=2555
        )
        cache_timeout = st.number_input(
            "Cache timeout (minutes)", value=30, min_value=1, max_value=1440
        )

    st.session_state.auto_save = auto_save
    st.session_state.backup_enabled = backup_enabled
    st.session_state.data_retention = data_retention
    st.session_state.cache_timeout = cache_timeout

    st.write("**API Configuration:**")

    api_timeout = st.number_input(
        "API timeout (seconds)", value=30, min_value=5, max_value=300
    )
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
            "theme": st.session_state.get("theme", "light"),
            "business_metrics": {
                "occupancy": occupancy,
                "total_leads": total_leads,
                "mql": mql,
                "sql": sql,
            },
            "cost_config": {
                "costa_usd": costa_usd,
                "costa_crc": costa_crc,
                "hk_usd": hk_usd,
                "stripe_fee": stripe_fee,
                "huub_principal": huub_principal,
                "huub_interest": huub_interest,
                "google_ads": google_ads,
            },
        }

        st.download_button(
            label="Download settings.json",
            data=json.dumps(export_data, indent=2),
            file_name="cash_flow_settings.json",
            mime="application/json",
        )

with col2:
    uploaded_file = st.file_uploader("Import Settings", type=["json"])
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
                st.session_state.settings_imported = True

        except Exception as e:
            st.error(f"Error importing settings: {str(e)}")

# 📥 Data Imports (Admin only)
if user_role == UserRole.ADMIN:
    st.subheader("📥 Data Imports")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Import Leads (Airtable → LeadsModel)"):
            try:
                records, summary = import_leads()
                st.success(f"Imported {len(records)} leads")
                st.info(
                    f"Raw: {summary['total_raw']}, After filter: {summary['after_mql_sql_filter']}, Deduped: {summary['deduped']}"
                )
                for src, cnt in sorted(summary.get('utm_sources', {}).items(), key=lambda x: -x[1]):
                    st.write(f"• {src}: {cnt}")
                st.session_state.last_leads_import_summary = summary
                st.session_state.last_leads_records = records
            except Exception as e:
                handle_error(e, "Failed to import leads from Airtable", context="import_leads")

        has_leads = bool(st.session_state.get("last_leads_records"))
        if not has_leads:
            st.info("Run an import first to enable saving to DB.")
        if st.button("Save Leads to DB", disabled=not has_leads):
            try:
                res = save_leads_to_db(st.session_state.get("last_leads_records", []))
                st.success(f"Leads saved. Inserted: {res.get('inserted', 0)}, Updated: {res.get('updated', 0)}")
            except Exception as e:
                handle_error(e, "Failed to save leads to DB", context="save_leads_to_db")

    with col2:
        if st.button("Import Bookings (Airtable → BookingModel)"):
            try:
                records, summary = import_bookings()
                st.success(f"Imported {len(records)} bookings")
                st.info(
                    f"Raw: {summary['total_raw']}, Deduped: {summary['deduped']}"
                )
                met1, met2 = st.columns(2)
                with met1:
                    st.metric("Total Amount", f"${summary['total_amount']:,.2f}")
                with met2:
                    st.metric("Total Guests", summary['guests_total'])
                st.session_state.last_bookings_import_summary = summary
                st.session_state.last_bookings_records = records
            except Exception as e:
                handle_error(e, "Failed to import bookings from Airtable", context="import_bookings")

        has_bookings = bool(st.session_state.get("last_bookings_records"))
        if not has_bookings:
            st.info("Run an import first to enable saving to DB.")
        if st.button("Save Bookings to DB", disabled=not has_bookings):
            try:
                res = save_bookings_to_db(st.session_state.get("last_bookings_records", []))
                st.success(f"Bookings saved. Inserted: {res.get('inserted', 0)}, Updated: {res.get('updated', 0)}")
            except Exception as e:
                handle_error(e, "Failed to save bookings to DB", context="save_bookings_to_db")

    st.divider()
    st.caption("Leads CSV expected headers (case-insensitive): email, created_at (or created/date/date_added), mql or mql_yes, sql or sql_yes, utm_source, utm_medium, utm_campaign. Dates can be in most common formats; they will be parsed and normalized to YYYY-MM-DD.")
    leads_csv = st.file_uploader("Upload Leads CSV", type=["csv"], key="leads_csv_uploader")
    if leads_csv is not None:
        try:
            leads_records, leads_diag = parse_csv_leads_with_diagnostics(leads_csv)
            st.session_state.last_leads_records = leads_records
            st.success(f"Parsed {len(leads_records)} lead rows from CSV (deduped). Preview below.")

            # Summary metrics before saving
            total_leads = len(leads_records)
            mql_count = sum(1 for r in leads_records if getattr(r, "is_mql", False))
            sql_count = sum(1 for r in leads_records if getattr(r, "is_sql", False))
            distinct_emails = len({getattr(r, "email", None) for r in leads_records if getattr(r, "email", None)})

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Parsed", total_leads)
            c2.metric("MQL Count", mql_count)
            c3.metric("SQL Count", sql_count)
            c4.metric("Distinct Emails", distinct_emails)

            with st.expander("Parsing Diagnostics (Leads)"):
                st.write(f"Delimiter: {leads_diag.get('delimiter', '?')}")
                st.write("Headers:")
                st.code("\n".join(leads_diag.get('headers', [])) or "-")
                dropped = leads_diag.get("dropped", {})
                colA, colB, colC, colD = st.columns(4)
                colA.metric("Rows Read", leads_diag.get("total_rows", 0))
                colB.metric("Missing Email", dropped.get("missing_email", 0))
                colC.metric("Invalid Date", dropped.get("invalid_date", 0))
                colD.metric("Header Missing", dropped.get("header_not_found", 0))
                st.metric("Groups After Dedupe", leads_diag.get("groups_after_dedupe", 0))
                m1, m2 = st.columns(2)
                m1.metric("MQL After Dedupe", leads_diag.get("mql_true_after_dedupe", 0))
                m2.metric("SQL After Dedupe", leads_diag.get("sql_true_after_dedupe", 0))
                if leads_diag.get("missing_headers"):
                    st.error("Missing required headers: " + ", ".join(leads_diag.get("missing_headers", [])))

            preview = [
                {
                    "email": r.email,
                    "created_at": r.created_date.isoformat(),
                    "mql_yes": bool(r.is_mql),
                    "sql_yes": bool(r.is_sql),
                    "utm_source": r.utm_source,
                    "utm_medium": r.utm_medium,
                    "utm_campaign": r.utm_campaign,
                }
                for r in leads_records[:10]
            ]
            st.dataframe(preview, use_container_width=True)

            if st.button("Save Uploaded Leads to DB"):
                try:
                    res = save_leads_to_db(st.session_state.get("last_leads_records", []))
                    st.success(
                        f"Leads saved. Inserted: {res.get('inserted', 0)}, Updated: {res.get('updated', 0)}"
                    )
                    st.session_state.last_leads_records = []
                except Exception as e:
                    err = ErrorHandler()
                    err.handle_error(e, "csv_import")
                    st.error("Failed to save uploaded leads to DB. See logs for details.")
        except Exception as e:
            err = ErrorHandler()
            err.handle_error(e, "csv_import")
            st.error("Failed to parse Leads CSV. Please check the file format and try again.")

    st.divider()
    st.caption("Bookings CSV expected headers (case-insensitive): booking_id, booking_date (or date/created_at), arrival_date (or arrival), departure_date (or departure), guests, amount, email (optional). Dates can be in most common formats; they will be parsed and normalized to YYYY-MM-DD.")
    bookings_csv = st.file_uploader("Upload Bookings CSV", type=["csv"], key="bookings_csv_uploader")
    if bookings_csv is not None:
        try:
            bookings_records, bookings_diag = parse_csv_bookings_with_diagnostics(bookings_csv)
            st.session_state.last_bookings_records = bookings_records
            st.success(f"Parsed {len(bookings_records)} booking rows from CSV (deduped). Preview below.")

            # Optional quick summary for bookings
            total_b = len(bookings_records)
            with_email = sum(1 for r in bookings_records if getattr(r, "email", None))
            without_email = total_b - with_email
            dates = [r.booking_date for r in bookings_records if getattr(r, "booking_date", None)]
            min_date = min(dates).isoformat() if dates else "-"
            max_date = max(dates).isoformat() if dates else "-"

            b1, b2, b3, b4 = st.columns(4)
            b1.metric("Total Parsed", total_b)
            b2.metric("With Email", with_email)
            b3.metric("Without Email", without_email)
            b4.metric("Booking Date Range", f"{min_date} → {max_date}")

            with st.expander("Parsing Diagnostics (Bookings)"):
                st.write(f"Delimiter: {bookings_diag.get('delimiter', '?')}")
                st.write("Headers:")
                st.code("\n".join(bookings_diag.get('headers', [])) or "-")
                dropped = bookings_diag.get("dropped", {})
                colA, colB = st.columns(2)
                colA.metric("Rows Read", bookings_diag.get("total_rows", 0))
                colB.metric("Duplicates in File", bookings_diag.get("duplicates_in_file", 0))
                d1, d2 = st.columns(2)
                d1.metric("Missing ID", dropped.get("missing_id", 0))
                d2.metric("Invalid Booking Date", dropped.get("invalid_booking_date", 0))

            preview_b = [
                {
                    "booking_id": r.booking_id,
                    "booking_date": r.booking_date.isoformat() if getattr(r, "booking_date", None) else None,
                    "arrival_date": r.arrival_date.isoformat() if getattr(r, "arrival_date", None) else None,
                    "departure_date": r.departure_date.isoformat() if getattr(r, "departure_date", None) else None,
                    "guests": int(getattr(r, "guests", 0) or 0),
                    "amount": float(getattr(r, "amount", 0.0) or 0.0),
                    "email": getattr(r, "email", None),
                }
                for r in bookings_records[:10]
            ]
            st.dataframe(preview_b, use_container_width=True)

            if st.button("Save Uploaded Bookings to DB"):
                try:
                    res = save_bookings_to_db(st.session_state.get("last_bookings_records", []))
                    st.success(
                        f"Bookings saved. Inserted: {res.get('inserted', 0)}, Updated: {res.get('updated', 0)}"
                    )
                    st.session_state.last_bookings_records = []
                except Exception as e:
                    err = ErrorHandler()
                    err.handle_error(e, "csv_import")
                    st.error("Failed to save uploaded bookings to DB. See logs for details.")
        except Exception as e:
            err = ErrorHandler()
            err.handle_error(e, "csv_import")
            st.error("Failed to parse Bookings CSV. Please check the file format and try again.")

    st.divider()
    st.subheader("🧨 Danger Zone — Reset Database")
    try:
        db_path = Settings().database.absolute_path
        st.caption(f"Current DB path: {db_path}")
    except Exception:
        db_path = None
        st.caption("Current DB path: (unavailable)")
    confirm_reset = st.checkbox("I understand this will delete ALL data and recreate empty tables.")
    if st.button("Reset Database", type="secondary", disabled=not confirm_reset):
        try:
            # Ensure all connections are closed before removing the file
            try:
                DatabaseConnection().close_all_connections()
            except Exception:
                pass
            if db_path and os.path.exists(db_path):
                os.remove(db_path)
            # Recreate schema
            from src.repositories.ingest_repository import get_ingest_repository
            repo = get_ingest_repository()
            repo.create_tables_if_missing()
            st.success("Database reset complete. Fresh schema created.")
        except Exception as e:
            handle_error(e, "Failed to reset database", context="reset_db")
    # Historical Backfill
    with st.expander("Historical Backfill (All Time)"):
        st.info("This may take a while — all historical Airtable rows will be loaded.")
        colA, colB = st.columns(2)
        with colA:
            if st.button("Backfill Leads (All Time)"):
                try:
                    records = fetch_all_leads()
                    res = save_leads_to_db(records)
                    st.success(
                        f"Leads backfill complete. Inserted: {res.get('inserted', 0)}, Updated: {res.get('updated', 0)}"
                    )
                except Exception as e:
                    handle_error(e, "Failed to backfill leads from Airtable", context="backfill_leads")
        with colB:
            if st.button("Backfill Bookings (All Time)"):
                try:
                    records = fetch_all_bookings()
                    res = save_bookings_to_db(records)
                    st.success(
                        f"Bookings backfill complete. Inserted: {res.get('inserted', 0)}, Updated: {res.get('updated', 0)}"
                    )
                except Exception as e:
                    handle_error(e, "Failed to backfill bookings from Airtable", context="backfill_bookings")

    # Last Import recaps
    if 'last_leads_import_summary' in st.session_state:
        st.caption("Last Leads Import")
        s = st.session_state.last_leads_import_summary
        st.write(
            f"Raw: {s.get('total_raw', 0)}, After filter: {s.get('after_mql_sql_filter', 0)}, Deduped: {s.get('deduped', 0)}"
        )
        if s.get('utm_sources'):
            st.write("UTM Sources:")
            for src, cnt in sorted(s['utm_sources'].items(), key=lambda x: -x[1]):
                st.write(f"• {src}: {cnt}")

    if 'last_bookings_import_summary' in st.session_state:
        st.caption("Last Bookings Import")
        s = st.session_state.last_bookings_import_summary
        st.write(
            f"Raw: {s.get('total_raw', 0)}, Deduped: {s.get('deduped', 0)}"
        )
        met1, met2 = st.columns(2)
        with met1:
            st.metric("Total Amount", f"${s.get('total_amount', 0.0):,.2f}")
        with met2:
            st.metric("Total Guests", int(s.get('guests_total', 0)))

# 🏦 Bank Accounts & Opening Balances
st.subheader("🏦 Bank Accounts & Opening Balances")
bank_service = get_bank_service()

try:
    accounts = bank_service.list_accounts()
except Exception as e:
    ErrorHandler().handle_error(e, "Failed to load bank accounts")
    accounts = []

list_names = [f"{a.get('name')} ({a.get('currency','USD')})" for a in accounts]
id_by_index = {idx: a.get("id") for idx, a in enumerate(accounts)}

colA, colB, colC = st.columns(3)

with colA:
    st.markdown("**Add / Edit Account**")
    with st.form("bank_account_form"):
        edit_idx = st.selectbox("Select existing (optional)", options=["- New Account -"] + list_names, index=0)
        data: dict = {}
        if edit_idx != "- New Account -":
            sel_i = list_names.index(edit_idx)
            selected = accounts[sel_i]
            data.update(selected)
        name = st.text_input("Name", value=data.get("name", ""))
        currency = st.text_input("Currency", value=data.get("currency", "USD"))
        bank_name = st.text_input("Bank Name", value=data.get("bank_name", ""))
        last4 = st.text_input("Last4 (optional)", value=data.get("last4", ""))
        is_active = st.checkbox("Active", value=bool(data.get("is_active", 1)))
        submitted = st.form_submit_button("Save Account")
        if submitted:
            try:
                payload = {
                    "id": data.get("id"),
                    "name": name.strip(),
                    "currency": currency.strip() or "USD",
                    "bank_name": bank_name.strip() or None,
                    "last4": last4.strip() or None,
                    "is_active": bool(is_active),
                }
                acct_id = bank_service.upsert_account(payload)
                st.success(f"Account saved (id: {acct_id[:8]})")
                st.rerun()
            except Exception as e:
                ErrorHandler().handle_error(e, "Failed to save account")

with colB:
    st.markdown("**Set Opening Balance**")
    with st.form("opening_balance_form"):
        if accounts:
            idx = st.selectbox("Account", options=list_names, index=0)
            sel_id = id_by_index[list_names.index(idx)]
        else:
            sel_id = None
            st.info("Create an account first.")
        as_of = st.date_input("As of date", value=date.today())
        opening = st.number_input("Opening balance", value=0.0, step=0.01)
        submitted = st.form_submit_button("Save Opening Balance", disabled=not bool(accounts))
        if submitted and sel_id:
            try:
                bank_service.set_opening_balance(sel_id, as_of, float(opening))
                st.success("Opening balance saved")
            except Exception as e:
                ErrorHandler().handle_error(e, "Failed to save opening balance")

with colC:
    st.markdown("**Add Adjustment**")
    with st.form("bank_adjustment_form"):
        if accounts:
            idx = st.selectbox("Account", options=list_names, index=0, key="adj_acct")
            sel_id = id_by_index[list_names.index(idx)]
        else:
            sel_id = None
            st.info("Create an account first.")
        adj_date = st.date_input("Date", value=date.today(), key="adj_date")
        amount = st.number_input("Amount (+/-)", value=0.0, step=0.01, key="adj_amount")
        category = st.selectbox("Category", options=["bank_fee", "correction", "other"], key="adj_cat")
        reason = st.text_input("Reason", key="adj_reason")
        memo = st.text_input("Memo (optional)", key="adj_memo")
        submitted = st.form_submit_button("Add Adjustment", disabled=not bool(accounts))
        if submitted and sel_id:
            try:
                bank_service.add_adjustment(
                    {
                        "bank_account_id": sel_id,
                        "date": adj_date,
                        "amount": float(amount),
                        "category": category,
                        "reason": reason,
                        "memo": memo or None,
                    }
                )
                st.success("Adjustment added")
            except Exception as e:
                ErrorHandler().handle_error(e, "Failed to add adjustment")

# Balances Preview
try:
    from pandas import DataFrame
    balances = bank_service.balance_for_all_accounts(date.today())
    if balances:
        st.markdown("**Balances Preview (Today)**")
        df = DataFrame(balances)[[
            "name",
            "currency",
            "opening_balance",
            "inflows",
            "outflows",
            "adjustments_total",
            "current_balance",
        ]]
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No bank accounts yet.")
except Exception as e:
    ErrorHandler().handle_error(e, "Failed to load balances preview")

# System Info Tab
with tab3:
    st.header("📊 System Information")

    # Application info
    st.subheader("🏗️ Application")
    col1, col2 = st.columns(2)

    with col1:
        st.metric("Application", "Cash Flow Dashboard")
        st.metric("Version", "2.1.0")
        st.metric(
            "Environment",
            (
                "Production"
                if st.session_state.get("production", False)
                else "Development"
            ),
        )

    with col2:
        st.metric("User Role", user_role.name if AUTH_AVAILABLE else "ADMIN (Dev Mode)")
        st.metric("Session Active", "Yes" if current_user else "No")
        st.metric("Theme", current_theme.title())

    # Security features
    if current_user and user_role == UserRole.ADMIN:
        st.subheader("🔐 Security Features")
        security_features = [
            "✅ Role-based access control (RBAC)",
            "✅ Encrypted API key storage",
            "✅ Session-based authentication",
            "✅ PII detection and masking",
            "✅ Audit logging",
            "✅ Secure memory management",
            "✅ CSRF protection",
            "✅ Input validation and sanitization",
        ]

        for feature in security_features:
            st.markdown(feature)

    # Database info
    st.subheader("🗄️ Database")
    try:
        from src.services.key_vault import get_key_vault_service

        # In dev mode, current_user might be a plain dict
        user_id = getattr(current_user, "id", None) or current_user.get("email", "dev")
        vault_service = get_key_vault_service(
            session_id=st.session_state.get("session_id", "default"),
            user_id=user_id,
        )
        api_keys = vault_service.list_api_keys()

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Active API Keys", len([k for k in api_keys if k.is_active]))
            st.metric("Total Keys", len(api_keys))

        with col2:
            services = set(k.service_type for k in api_keys if k.is_active)
            st.metric("Connected Services", len(services))
            if services:
                st.caption(f"Services: {', '.join(services)}")
    except Exception as e:
        st.error(f"Unable to load database info: {str(e)}")
        vault_service = None

    # Cache statistics (Admin only)
    if current_user and user_role == UserRole.ADMIN:
        st.subheader("💾 Cache Statistics")
        if vault_service:
            try:
                cache_stats = vault_service.get_cache_stats()

                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Cached Keys", cache_stats["cached_keys"])
                    st.metric("Session ID", cache_stats["session_id"][:8] + "...")

                with col2:
                    st.metric(
                        "Cache Timeout", f"{cache_stats['cache_timeout_minutes']:.0f} min"
                    )
                    if st.button("🧹 Clear Cache"):
                        vault_service.clear_cache()
                        st.success("Cache cleared successfully")
                        st.rerun()
            except Exception as e:
                st.error(f"Unable to load cache statistics: {str(e)}")
        else:
            st.info("Cache statistics not available (vault service unavailable)")

