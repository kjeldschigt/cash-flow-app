# Cash Flow App
Internal dashboard for sales, costs, forecasts, loan, and integrations.

## Setup
1. Create venv: python -m venv .venv
2. Activate: source .venv/bin/activate
3. Install: pip install -r requirements.txt
4. Copy env: cp .env.example .env (add your keys)
5. Run: streamlit run app.py

## Features
- Dashboard: Metrics (revenue, costs, net, margin).
- Sales vs Cash: Reconciliation.
- Costs: Breakdown with FX.
- Scenarios: 5-year projections.
- Loan: HUB tracking.
- Integrations: Airtable/Stripe stubs.

## Deployment
Use Streamlit Cloud: Upload repo, set app.py as entrypoint.
Or AWS/EC2: Install Python, run as service.