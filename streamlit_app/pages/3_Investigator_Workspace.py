"""
pages/3_Investigator_Workspace.py — Investigator Review Workspace (Phase 3 Integration)

Overview:
Human-in-the-loop review workspace for compliance investigators and administrators.
Surfaces exception records and quality control flags generated during Phase 3 document automation.

Key Modules:
  1. Review Queue (`DOCS.REVIEW_QUEUE`): Tracks documents that parsed successfully 
     but triggered quality warnings (e.g., missing critical KYC fields or empty text).
  2. Extraction Errors (`DOCS.EXTRACTION_ERRORS`): Logs system-level pipeline 
     failures and exceptions caught during AI parsing/extraction tasks.

Access Control:
Restricted strictly to roles with `investigator_workspace` permission 
(COMPLIANCE_INVESTIGATOR_ROLE and CORTEX_ADMIN_ROLE).
"""

import sys
import os
import streamlit as st

# Append parent directory to Python path to import root-level utility modules
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from utils.access_control import check_access, get_session, get_current_role

# Configure Streamlit page settings and browser tab metadata
st.set_page_config(page_title="Investigator Workspace — Compliance Copilot", page_icon="🔍", layout="wide")

# Enforce access control — halts execution if active role lacks permission for 'investigator_workspace'
check_access("investigator_workspace")

# Render page title and current user role badge
st.title("🔍 Investigator Workspace")
st.caption(f"Role: {get_current_role()}")

# ------------------------------------------------------------------------
# Navigation Tabs: Split exception workflow into Review Queue vs. System Errors
# ------------------------------------------------------------------------
tab_review, tab_errors = st.tabs(["Review Queue", "Extraction Errors"])

# Tab 1: Business Logic & Quality Validation Queue
with tab_review:
    st.write("Documents that processed successfully but have suspicious or missing data — needs a human look.")
    
    # Placeholder indicator for Snowpark query integration
    st.info("🚧 STUB — will query `DOCS.REVIEW_QUEUE WHERE status = 'OPEN'` and display as a table with a resolve action.")
    
    # TODO: Connect Snowpark session to fetch live review records
    # session = get_session()
    # df = session.sql("SELECT * FROM DOCS.REVIEW_QUEUE WHERE status = 'OPEN' ORDER BY flagged_at DESC").to_pandas()
    # st.dataframe(df)

# Tab 2: System Exceptions & Pipeline Failure Logs
with tab_errors:
    st.write("Documents that failed outright at some pipeline stage.")
    
    # Placeholder indicator for Snowpark query integration
    st.info("🚧 STUB — will query `DOCS.EXTRACTION_ERRORS` and display as a table.")
    
    # TODO: Connect Snowpark session to fetch runtime pipeline errors
    # df = session.sql("SELECT * FROM DOCS.EXTRACTION_ERRORS ORDER BY attempted_at DESC").to_pandas()
    # st.dataframe(df)
