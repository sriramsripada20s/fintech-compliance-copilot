"""
pages/5_Cost_Dashboard.py — Cortex AI Credit Usage & Warehouse Spend Dashboard

Overview:
Cost tracking dashboard for monitoring Snowflake credit consumption and compute cost.
Queries Snowflake system metadata views (`ACCOUNT_USAGE`) to track daily consumption 
across AI services and virtual warehouses.

Key Queries & Views:
  1. `SNOWFLAKE.ACCOUNT_USAGE.METERING_DAILY_HISTORY`: Tracks daily credits by service type.
  2. `SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY`: Tracks daily credits per virtual warehouse.

Technical Note:
ACCOUNT_USAGE latency can lag real-time activity by 45 minutes to 3 hours.
The page includes an explicit disclaimer so users understand recent usage timing.

Access Control:
Restricted strictly to roles with `cost_dashboard` permission 
(COMPLIANCE_INVESTIGATOR_ROLE and CORTEX_ADMIN_ROLE).
"""

import sys
import os
import streamlit as st
import pandas as pd

# Append parent directory to Python path to import root-level utility modules
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from utils.access_control import check_access, get_session, get_current_role

# Configure Streamlit page settings and browser tab metadata
st.set_page_config(page_title="Cost Dashboard — Compliance Copilot", page_icon="💰", layout="wide")

# Enforce access control — halts execution if active role lacks permission for 'cost_dashboard'
check_access("cost_dashboard")

# Render page title, active role badge, and data latency disclaimer
st.title("💰 Cost Dashboard")
st.caption(f"Role: {get_current_role()}")
st.info(
    "ℹ️ Data source: `SNOWFLAKE.ACCOUNT_USAGE`. This can lag real-time "
    "activity by up to a few hours — very recent usage may not appear yet."
)

# Acquire Snowpark session from Streamlit runtime context
session = get_session()


@st.cache_data(ttl=300)
def load_daily_credits():
    """
    Queries METERING_DAILY_HISTORY to fetch overall daily credit usage by service type.
    Cached for 5 minutes (TTL = 300s) to prevent redundant queries.
    """
    query = """
        SELECT
            usage_date,
            service_type,
            SUM(credits_used) AS credits_used
        FROM SNOWFLAKE.ACCOUNT_USAGE.METERING_DAILY_HISTORY
        WHERE usage_date >= DATEADD(day, -14, CURRENT_DATE())
        GROUP BY usage_date, service_type
        ORDER BY usage_date
    """
    return session.sql(query).to_pandas()


@st.cache_data(ttl=300)
def load_warehouse_credits():
    """
    Queries WAREHOUSE_METERING_HISTORY to break down daily credit consumption per virtual warehouse.
    Cached for 5 minutes (TTL = 300s).
    """
    query = """
        SELECT
            warehouse_name,
            DATE(start_time) AS usage_date,
            SUM(credits_used) AS credits_used
        FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
        WHERE start_time >= DATEADD(day, -14, CURRENT_DATE())
        GROUP BY warehouse_name, usage_date
        ORDER BY usage_date
    """
    return session.sql(query).to_pandas()


# Safely execute daily credit query with error handling fallback
try:
    daily_df = load_daily_credits()
except Exception as e:
    st.error(f"Could not load METERING_DAILY_HISTORY: {e}")
    daily_df = pd.DataFrame()

# Safely execute warehouse metering query with error handling fallback
try:
    wh_df = load_warehouse_credits()
except Exception as e:
    st.error(f"Could not load WAREHOUSE_METERING_HISTORY: {e}")
    wh_df = pd.DataFrame()

# ------------------------------------------------------------------------
# Top-Line Summary KPI Cards (3 Columns)
# Computes current daily totals, 7-day totals, and 14-day warehouse usage
# ------------------------------------------------------------------------
col1, col2, col3 = st.columns(3)

if not daily_df.empty:
    latest_date = daily_df["USAGE_DATE"].max()
    today_total = daily_df[daily_df["USAGE_DATE"] == latest_date]["CREDITS_USED"].sum()
    last_7d_total = daily_df[daily_df["USAGE_DATE"] >= latest_date - pd.Timedelta(days=7)]["CREDITS_USED"].sum()
    with col1:
        st.metric("Most recent day's credits", f"{today_total:,.2f}")
    with col2:
        st.metric("Last 7 days total", f"{last_7d_total:,.2f}")
else:
    with col1:
        st.metric("Most recent day's credits", "—")
    with col2:
        st.metric("Last 7 days total", "—")

if not wh_df.empty:
    fintech_wh_total = wh_df[wh_df["WAREHOUSE_NAME"] == "FINTECH_COPILOT_WH"]["CREDITS_USED"].sum()
    with col3:
        st.metric("FINTECH_COPILOT_WH — 14 day total", f"{fintech_wh_total:,.2f}")
else:
    with col3:
        st.metric("FINTECH_COPILOT_WH — 14 day total", "—")

st.divider()

# ------------------------------------------------------------------------
# Visualization 1: Daily Credit Trend by Service Type
# Pivots raw data to render a stacked bar chart showing spend categories
# ------------------------------------------------------------------------
st.subheader("Daily credits by service type")
if not daily_df.empty:
    pivot = daily_df.pivot_table(
        index="USAGE_DATE", columns="SERVICE_TYPE", values="CREDITS_USED", fill_value=0
    )
    st.bar_chart(pivot)
    with st.expander("Raw data"):
        st.dataframe(daily_df, use_container_width=True)
else:
    st.caption("No data available — check ACCOUNT_USAGE access privileges.")

# ------------------------------------------------------------------------
# Visualization 2: Warehouse Breakdown
# Pivots raw data to isolate warehouse compute usage over time
# ------------------------------------------------------------------------
st.subheader("Credits by warehouse")
if not wh_df.empty:
    wh_pivot = wh_df.pivot_table(
        index="USAGE_DATE", columns="WAREHOUSE_NAME", values="CREDITS_USED", fill_value=0
    )
    st.bar_chart(wh_pivot)
    with st.expander("Raw data"):
        st.dataframe(wh_df, use_container_width=True)
else:
    st.caption("No warehouse data available.")

st.divider()

# Cost optimization tip for warehouse task polling costs
st.caption(
    "💡 Tip: if credits look high, check the Warehouse breakdown above first — "
    "frequent task polling (document pipeline, Streamlit Git sync) accumulates "
    "warehouse compute even at small query volumes. Consider suspending tasks "
    "you're not actively using: `ALTER TASK <name> SUSPEND;`"
)
