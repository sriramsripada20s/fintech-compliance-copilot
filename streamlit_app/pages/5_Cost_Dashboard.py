"""
pages/5_Cost_Dashboard.py — Cortex AI credit usage and spend tracking.

STUB: page structure and role gating in place. This is the cheapest page
to make fully functional next — it's pure read-only SQL against
ACCOUNT_USAGE views already validated manually throughout Phases 1-6
(METERING_DAILY_HISTORY, CORTEX_*_USAGE_HISTORY).
"""

import sys
import os
import streamlit as st

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from utils.access_control import check_access, get_session, get_current_role

st.set_page_config(page_title="Cost Dashboard — Compliance Copilot", page_icon="💰", layout="wide")

check_access("cost_dashboard")

st.title("💰 Cost Dashboard")
st.caption(f"Role: {get_current_role()}")

st.info(
    "🚧 STUB — will show daily credit usage broken out by service type "
    "(AI_FUNCTIONS, WAREHOUSE_METERING, etc.) using the same queries "
    "already validated manually: METERING_DAILY_HISTORY, "
    "CORTEX_ANALYST_USAGE_HISTORY, CORTEX_SEARCH_DAILY_USAGE_HISTORY."
)

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Today's AI credits", "—", help="STUB")
with col2:
    st.metric("This week's total spend", "—", help="STUB")
with col3:
    st.metric("Avg. cost per Agent query", "—", help="STUB")

st.divider()
st.caption("Daily credit trend chart — STUB")
# TODO:
# session = get_session()
# df = session.sql("""
#     SELECT usage_date, service_type, credits_used
#     FROM SNOWFLAKE.ACCOUNT_USAGE.METERING_DAILY_HISTORY
#     WHERE usage_date >= DATEADD(day, -30, CURRENT_DATE())
#     ORDER BY usage_date
# """).to_pandas()
# st.line_chart(df, x="USAGE_DATE", y="CREDITS_USED", color="SERVICE_TYPE")
