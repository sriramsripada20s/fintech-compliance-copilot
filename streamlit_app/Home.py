"""
Home.py — Fintech Customer Intelligence & Compliance Copilot
Streamlit in Snowflake (SiS) Landing Page & Entry Point

Overview:
Role-aware landing page for the Streamlit application.
Detects the active user's Snowflake role at runtime and dynamically renders 
a card-based navigation overview of accessible vs. restricted modules.

Role Access Rules (Enforces RBAC design from Phases 1, 4, 5, and 6):
  - COMPLIANCE_INVESTIGATOR_ROLE / CORTEX_ADMIN_ROLE: Full access to all 6 modules.
  - SUPPORT_AGENT_ROLE: Restricted access (Chat module only; administrative, 
    customer 360, and upload pages are locked).
"""

import streamlit as st
from snowflake.snowpark.context import get_active_session

# Set Streamlit page layout and browser tab configuration
st.set_page_config(
    page_title="Compliance Copilot",
    page_icon="🛡️",
    layout="wide",
)

# Fetch the active Snowpark session from the SiS execution environment
session = get_active_session()

# Identify the currently active Snowflake role (strip quotes for string matching)
current_role = session.get_current_role().strip('"')

# ------------------------------------------------------------------------
# Central Role Access Mapping (ROLE_ACCESS)
# Serves as the single source of truth for page-level access control.
# Imported across child pages to maintain consistent RBAC enforcement.
# ------------------------------------------------------------------------
ROLE_ACCESS = {
    "COMPLIANCE_INVESTIGATOR_ROLE": {
        "chat": True,
        "document_upload": True,
        "investigator_workspace": True,
        "customer_360": True,
        "cost_dashboard": True,
        "eval_dashboard": True,
    },
    "SUPPORT_AGENT_ROLE": {
        "chat": True,               # Agent inherits tool-level RBAC (Phase 6)
        "document_upload": False,
        "investigator_workspace": False,
        "customer_360": False,
        "cost_dashboard": False,
        "eval_dashboard": False,
    },
    "CORTEX_ADMIN_ROLE": {
        "chat": True,
        "document_upload": True,
        "investigator_workspace": True,
        "customer_360": True,
        "cost_dashboard": True,
        "eval_dashboard": True,
    },
}

# Resolve access permissions for the current role (defaults to all False for unknown roles)
access = ROLE_ACCESS.get(current_role, {k: False for k in ROLE_ACCESS["SUPPORT_AGENT_ROLE"]})

# ------------------------------------------------------------------------
# UI Rendering: App Header & Role Notification
# ------------------------------------------------------------------------
st.title("🛡️ Compliance Copilot")
st.caption("Fintech Customer Intelligence & Compliance Copilot")

# Display active role status badge
st.info(f"Signed in as role: **{current_role}**")

st.markdown("### Available pages")

# Master dictionary defining UI labels and descriptive text for all app modules
page_descriptions = {
    "chat": ("💬 Chat", "Ask questions — routed to structured analytics or document search automatically."),
    "document_upload": ("📄 Document Upload", "Upload KYC forms, statements, and policy documents for processing."),
    "investigator_workspace": ("🔍 Investigator Workspace", "Review flagged extractions and pipeline errors."),
    "customer_360": ("👤 Customer 360", "Full customer profile — transactions, disputes, fraud alerts, interaction history."),
    "cost_dashboard": ("💰 Cost Dashboard", "Cortex AI credit usage and spend tracking."),
    "eval_dashboard": ("📊 Eval Dashboard", "Agent evaluation scores and quality metrics over time."),
}

# ------------------------------------------------------------------------
# Dynamic Grid Display (3 Columns)
# Iterates through modules and displays accessible vs. locked feature cards
# ------------------------------------------------------------------------
cols = st.columns(3)
for i, (key, (label, desc)) in enumerate(page_descriptions.items()):
    # Distribute cards evenly across 3 columns using modulo arithmetic
    with cols[i % 3]:
        if access.get(key):
            # Render available page card (Green background)
            st.success(f"**{label}**\n\n{desc}")
        else:
            # Render restricted page card (Red background + Lock icon)
            st.error(f"**{label}** 🔒\n\n_Not available for your role._")

st.divider()
st.caption(
    "STUB — Home page skeleton. Each page below is a placeholder; "
    "functionality is being built out page by page."
)
