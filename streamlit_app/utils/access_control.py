"""
utils/access_control.py — shared role-gating logic for all pages.

Import and call check_access(page_key) at the top of every page under
pages/. Keeps the ROLE_ACCESS map in exactly one place instead of copy-
pasted across 6 files.
"""

import streamlit as st
from snowflake.snowpark.context import get_active_session

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
        "chat": True,
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

DEFAULT_ACCESS = {k: False for k in ROLE_ACCESS["SUPPORT_AGENT_ROLE"]}


def get_session():
    return get_active_session()


def get_current_role() -> str:
    session = get_session()
    return session.get_current_role().strip('"')


def check_access(page_key: str) -> bool:
    """
    Call at the top of a page. Stops execution with st.stop() if the
    current role doesn't have access to page_key. Returns True if access
    is granted (so callers can `if not check_access(...): return` in
    functions, though top-level st.stop() usually makes that unnecessary).
    """
    role = get_current_role()
    access = ROLE_ACCESS.get(role, DEFAULT_ACCESS)

    if not access.get(page_key, False):
        st.error(
            f"🔒 Access denied. Role **{role}** does not have permission "
            f"to view this page."
        )
        st.stop()

    return True
