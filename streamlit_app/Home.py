"""
Home.py — Fintech Customer Intelligence & Compliance Copilot
Streamlit in Snowflake (SiS) entry point.

Role-aware landing page. Detects the caller's current role and shows a
navigation summary of what's available to them — mirrors the RBAC design
from Phases 1/4/5/6 (COMPLIANCE_INVESTIGATOR_ROLE sees everything,
SUPPORT_AGENT_ROLE sees a restricted subset).
"""

import streamlit as st
from snowflake.snowpark.context import get_active_session

st.set_page_config(
    page_title="Compliance Copilot",
    page_icon="🛡️",
    layout="wide",
)

session = get_active_session()
current_role = session.get_current_role().strip('"')

# ------------------------------------------------------------------------
# Role -> page access map. Kept in one place so every page can import this
# same logic instead of re-implementing role checks independently.
# ------------------------------------------------------------------------
ROLE_ACCESS = {
    "COMPLIANCE_INVESTIGATOR_ROLE": {
        "chat": True,
        "document_upload": True,
        "customer_360": True,
        "cost_dashboard": True,
        "eval_dashboard": True,
    },
    "SUPPORT_AGENT_ROLE": {
        "chat": True,              # agent inherits tool-level RBAC (Phase 6)
        "document_upload": False,
        "customer_360": False,
        "cost_dashboard": False,
        "eval_dashboard": False,
    },
    "CORTEX_ADMIN_ROLE": {
        "chat": True,
        "document_upload": True,
        "customer_360": True,
        "cost_dashboard": True,
        "eval_dashboard": True,
    },
}

access = ROLE_ACCESS.get(current_role, {k: False for k in ROLE_ACCESS["SUPPORT_AGENT_ROLE"]})

st.title("🛡️ Compliance Copilot")
st.caption("Fintech Customer Intelligence & Compliance Copilot")

st.info(f"Signed in as role: **{current_role}**")

st.markdown("### Available pages")

page_descriptions = {
    "chat": ("💬 Chat", "Ask questions — routed to structured analytics or document search automatically."),
    "document_upload": ("📄 Document Upload", "Upload KYC forms, statements, and policy documents for processing."),
    "customer_360": ("👤 Customer 360", "Full customer profile — transactions, disputes, fraud alerts, interaction history. Unifies structured + unstructured data for a single customer."),
    "cost_dashboard": ("💰 Cost Dashboard", "Cortex AI credit usage and spend tracking."),
    "eval_dashboard": ("📊 Eval Dashboard", "Agent evaluation scores and quality metrics over time."),
}

cols = st.columns(3)
for i, (key, (label, desc)) in enumerate(page_descriptions.items()):
    with cols[i % 3]:
        if access.get(key):
            st.success(f"**{label}**\n\n{desc}")
        else:
            st.error(f"**{label}** 🔒\n\n_Not available for your role._")

st.divider()
st.caption(
    "STUB — Home page skeleton. Each page below is a placeholder; "
    "functionality is being built out page by page."
)
