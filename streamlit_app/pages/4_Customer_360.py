"""
pages/4_Customer_360.py — Unified Customer 360 Profile View (Structured + AI-Derived Unstructured Data)

Overview:
Core demonstration page unifying structured relational mart data with AI-derived unstructured data 
for a single customer in a single pane of glass.

Key Data Sources (MARTS Schema):
  1. Name Search & Customer Lookup (`DIM_CUSTOMERS`): Resolves human-entered names (ILIKE) 
     to a specific `customer_id` UUID without requiring manual ID entry.
  2. Customer Profile Attributes (`DIM_CUSTOMERS`): Risk tier, KYC status, region, contact details.
  3. AI Interaction Summary (`CUSTOMER_INTERACTION_SUMMARY`): AI-generated summary generated via 
     `AI_SUMMARIZE_AGG` over redacted customer support tickets (Phase 2).
  4. Financial Transactions (`FCT_TRANSACTIONS`): Recent payment transactions and fraud flags.
  5. Payment Disputes (`FCT_DISPUTES`): Opened/closed disputes, reason codes, and resolution timelines.
  6. Risk & Fraud Alerts (`FCT_FRAUD_ALERTS`): Triggered fraud alerts and AI model risk scores.

Access Control:
Restricted strictly to roles with `customer_360` permission 
(COMPLIANCE_INVESTIGATOR_ROLE and CORTEX_ADMIN_ROLE).
"""

import sys
import os
import streamlit as st

# Append parent directory to Python path to import root-level utility modules
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from utils.access_control import check_access, get_session, get_current_role

# Configure Streamlit page settings and browser tab metadata
st.set_page_config(page_title="Customer 360 — Compliance Copilot", page_icon="👤", layout="wide")

# Enforce access control — halts page execution if active role lacks permission for 'customer_360'
check_access("customer_360")

# Render page title, current user role badge, and thesis caption
st.title("👤 Customer 360")
st.caption(f"Role: {get_current_role()}")
st.caption(
    "Unifies structured data (transactions, disputes, fraud alerts) with "
    "AI-derived unstructured data (interaction summary) for one customer."
)

# Acquire active Snowpark session
session = get_session()

# ------------------------------------------------------------------------
# Step 1: Customer Name Search & ID Resolution
# Uses parameterized ILIKE queries against DIM_CUSTOMERS to resolve UUIDs
# ------------------------------------------------------------------------
search_term = st.text_input("Search customer by name", placeholder="e.g. Maria Gonzalez")

selected_customer_id = None
selected_label = None

if search_term:
    # Parameterized search across first_name, last_name, or concatenated full name
    search_query = """
        SELECT customer_id, first_name, last_name, region, risk_tier
        FROM FINTECH_COPILOT.MARTS.DIM_CUSTOMERS
        WHERE first_name ILIKE ? OR last_name ILIKE ?
           OR (first_name || ' ' || last_name) ILIKE ?
        LIMIT 20
    """
    like_term = f"%{search_term}%"
    matches = session.sql(
        search_query, params=[like_term, like_term, like_term]
    ).to_pandas()

    if matches.empty:
        st.caption("No customers found matching that name.")
    else:
        # Build dictionary mapping friendly user labels to customer UUIDs
        options = {
            f"{row['FIRST_NAME']} {row['LAST_NAME']} — {row['REGION']} ({row['RISK_TIER']})": row["CUSTOMER_ID"]
            for _, row in matches.iterrows()
        }
        selected_label = st.selectbox("Select a customer", list(options.keys()))
        selected_customer_id = options.get(selected_label)

# ------------------------------------------------------------------------
# Step 2: Customer Profile Dashboard (Executes once a customer is selected)
# ------------------------------------------------------------------------
if selected_customer_id:
    st.divider()

    # --------------------------------------------------------------------
    # 2A. Core Profile Metrics (DIM_CUSTOMERS)
    # --------------------------------------------------------------------
    profile_query = """
        SELECT first_name, last_name, email, phone, city, state, region,
               risk_tier, kyc_status, created_at
        FROM FINTECH_COPILOT.MARTS.DIM_CUSTOMERS
        WHERE customer_id = ?
    """
    profile = session.sql(profile_query, params=[selected_customer_id]).to_pandas()

    if not profile.empty:
        p = profile.iloc[0]
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Risk Tier", p["RISK_TIER"])
        col2.metric("KYC Status", p["KYC_STATUS"])
        col3.metric("Region", p["REGION"])
        col4.metric("Customer Since", str(p["CREATED_AT"])[:10])
        st.caption(f"📧 {p['EMAIL']}  |  📞 {p['PHONE']}  |  📍 {p['CITY']}, {p['STATE']}")

    # --------------------------------------------------------------------
    # 2B. AI-Generated Interaction Summary (Phase 2 Unstructured Analytics)
    # Displays synthesized support ticket timeline created via AI_SUMMARIZE_AGG
    # --------------------------------------------------------------------
    st.divider()
    st.subheader("🤖 AI-Generated Interaction Summary")
    st.caption("Built via AI_SUMMARIZE_AGG over this customer's redacted support ticket history (Phase 2)")

    summary_query = """
        SELECT interaction_summary, ticket_count
        FROM FINTECH_COPILOT.MARTS.CUSTOMER_INTERACTION_SUMMARY
        WHERE customer_id = ?
    """
    summary = session.sql(summary_query, params=[selected_customer_id]).to_pandas()

    if not summary.empty:
        s = summary.iloc[0]
        st.info(s["INTERACTION_SUMMARY"])
        st.caption(f"Based on {s['TICKET_COUNT']} support ticket(s)")
    else:
        st.caption(
            "No interaction summary available for this customer — either they "
            "have no support tickets, or their tickets weren't in the sample "
            "processed so far (see `ticket_sample_limit` in the dbt model)."
        )

    # --------------------------------------------------------------------
    # 2C. Transaction History (FCT_TRANSACTIONS)
    # --------------------------------------------------------------------
    st.divider()
    st.subheader("💳 Transactions")

    txn_query = """
        SELECT txn_id, amount, merchant, channel, txn_timestamp, is_flagged
        FROM FINTECH_COPILOT.MARTS.FCT_TRANSACTIONS
        WHERE customer_id = ?
        ORDER BY txn_timestamp DESC
        LIMIT 50
    """
    txns = session.sql(txn_query, params=[selected_customer_id]).to_pandas()

    if not txns.empty:
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Transactions", len(txns))
        col2.metric("Total Volume", f"${txns['AMOUNT'].sum():,.2f}")
        col3.metric("Flagged Transactions", int(txns["IS_FLAGGED"].sum()))
        st.dataframe(txns, use_container_width=True)
    else:
        st.caption("No transactions found for this customer.")

    # --------------------------------------------------------------------
    # 2D. Payment Disputes (FCT_DISPUTES)
    # --------------------------------------------------------------------
    st.subheader("⚖️ Disputes")
    disp_query = """
        SELECT dispute_id, txn_id, reason_code, dispute_status,
               dispute_opened_at, dispute_days_open
        FROM FINTECH_COPILOT.MARTS.FCT_DISPUTES
        WHERE customer_id = ?
        ORDER BY dispute_opened_at DESC
    """
    disputes = session.sql(disp_query, params=[selected_customer_id]).to_pandas()

    if not disputes.empty:
        st.dataframe(disputes, use_container_width=True)
    else:
        st.caption("No disputes on file for this customer.")

    # --------------------------------------------------------------------
    # 2E. Fraud Alerts (FCT_FRAUD_ALERTS)
    # --------------------------------------------------------------------
    st.subheader("🚨 Fraud Alerts")
    alert_query = """
        SELECT alert_id, alert_type, model_score, created_at, is_reviewed
        FROM FINTECH_COPILOT.MARTS.FCT_FRAUD_ALERTS
        WHERE customer_id = ?
        ORDER BY created_at DESC
    """
    alerts = session.sql(alert_query, params=[selected_customer_id]).to_pandas()

    if not alerts.empty:
        st.dataframe(alerts, use_container_width=True)
    else:
        st.caption("No fraud alerts on file for this customer.")

else:
    st.caption("Search for a customer above to view their full profile.")
