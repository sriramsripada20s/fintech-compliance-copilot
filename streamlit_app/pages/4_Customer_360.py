"""
pages/4_Customer_360.py — Customer 360 Profile View (Phase 1 & Mart Layer Integration)

Overview:
Unified Customer 360 profile view for compliance investigators and administrators.
Consolidates relational mart tables into a single interactive view for an individual customer.

Key Data Sources (MARTS Schema):
  1. Profile Attributes (`DIM_CUSTOMERS`): Risk tier, KYC status, region, demographic data.
  2. Transaction History (`FCT_TRANSACTIONS`): Recent customer purchase/transfer activity.
  3. Dispute History (`FCT_DISPUTES`): Opened/resolved payment disputes and reason codes.
  4. Fraud Alerts (`FCT_FRAUD_ALERTS`): Triggered risk model alerts and model scores.
  5. Interaction Summary (`CUSTOMER_INTERACTION_SUMMARY`): AI-generated customer timeline.

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

# Enforce access control — halts execution if active role lacks permission for 'customer_360'
check_access("customer_360")

# Render page title and current user role badge
st.title("👤 Customer 360")
st.caption(f"Role: {get_current_role()}")

# Text input widget to accept target customer UUID
customer_id = st.text_input("Customer ID", placeholder="e.g. a UUID from DIM_CUSTOMERS")

# Render profile details if a Customer ID has been entered
if customer_id:
    # Placeholder indicator for Snowpark query integration
    st.info("🚧 STUB — will pull and display, for the given customer_id:")
    st.markdown(
        """
        - Profile summary (`DIM_CUSTOMERS`) — risk tier, KYC status, region
        - Transaction history (`FCT_TRANSACTIONS`)
        - Dispute history (`FCT_DISPUTES`)
        - Fraud alerts (`FCT_FRAUD_ALERTS`)
        - AI-generated interaction summary (`CUSTOMER_INTERACTION_SUMMARY`)
        """
    )
    
    # TODO: Connect Snowpark session to fetch live customer record across mart tables
    # session = get_session()
    # profile = session.sql("SELECT * FROM MARTS.DIM_CUSTOMERS WHERE customer_id = ?", params=[customer_id]).to_pandas()
    # (Note: Always use parameterized binding rather than f-string interpolation for security)
else:
    st.write("Enter a customer ID above to view their profile.")
