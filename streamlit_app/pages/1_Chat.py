"""
pages/1_Chat.py — Multi-turn Chat Interface via `SNOWFLAKE.CORTEX.DATA_AGENT_RUN`

Overview:
Production Streamlit chat interface connected to `COMPLIANCE_COPILOT_AGENT`.

Technical Architecture Note:
The direct Cortex Agents REST API endpoint requires a container runtime. 
Inside Streamlit in Snowflake (SiS) warehouses, we invoke the SQL-callable wrapper 
`SNOWFLAKE.CORTEX.DATA_AGENT_RUN` via Snowpark, eliminating the need for external 
REST clients or manual bearer token management.

Key Enhancements & Features:
  1. Multi-turn Session Management: Persists `thread_id` across turns for contextual conversation.
  2. Multi-Modal Response Rendering: Converts JSON blocks into Markdown text, Pandas DataFrames, 
     and Vega-Lite charts.
  3. Formatting Safeguard: Escapes dollar signs (`$ -> \$`) in text blocks to prevent Streamlit's 
     Markdown engine from accidentally treating financial amounts as LaTeX math expressions.
  4. Fallback Diagnostics: Includes a debug expander block if no user-facing content blocks are returned.
"""

import sys
import os
import json
import streamlit as st

# Append parent directory to Python path to import root-level utility modules
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from utils.access_control import check_access, get_current_role, get_session

# Configure Streamlit page settings and browser tab metadata
st.set_page_config(page_title="Chat — Compliance Copilot", page_icon="💬", layout="wide")

# Enforce access control — halts page execution if active role lacks permission for 'chat'
check_access("chat")

# Render page title and current user role badge
st.title("💬 Compliance Copilot Chat")
st.caption(f"Role: {get_current_role()}")

# Fully qualified target Cortex Agent name
AGENT_NAME = "FINTECH_COPILOT.AI.COMPLIANCE_COPILOT_AGENT"

# Initialize conversation message history and agent thread ID in session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None


def call_agent(user_text: str):
    """
    Executes DATA_AGENT_RUN via Snowpark with the user's latest prompt.
    
    Returns a list of renderable content blocks (text, table, chart, debug) 
    rather than plain text, preserving multi-modal responses from Cortex Agent tools.
    """
    session = get_session()

    # Build the JSON payload required by DATA_AGENT_RUN
    request_body = {
        "messages": [
            {"role": "user", "content": [{"type": "text", "text": user_text}]}
        ]
    }
    
    # Attach existing thread ID if continuing an ongoing multi-turn conversation
    if st.session_state.thread_id is not None:
        request_body["thread_id"] = st.session_state.thread_id

    request_json = json.dumps(request_body)

    # Parameterized SQL query wrapper to invoke the Cortex Agent function
    query = """
        SELECT SNOWFLAKE.CORTEX.DATA_AGENT_RUN(
            ?,
            ?,
            TRUE
        ) AS response
    """

    try:
        # Execute query via Snowpark session using bound parameter arguments
        result = session.sql(query, params=[AGENT_NAME, request_json]).collect()
        raw_response = result[0]["RESPONSE"]
        parsed = json.loads(raw_response)
    except Exception as e:
        return [{"type": "text", "text": f"⚠️ Error calling agent: {e}"}]

    # Update session thread ID if provided in metadata for multi-turn continuity
    metadata = parsed.get("metadata", {})
    if "thread_id" in metadata:
        st.session_state.thread_id = metadata["thread_id"]

    # Filter response payload: retain user-facing content blocks (text, table, chart)
    # and drop internal reasoning blocks (thinking, tool_use, suggested_queries)
    blocks = []
    for block in parsed.get("content", []):
        btype = block.get("type")
        if btype == "text":
            blocks.append({"type": "text", "text": block["text"]})
        elif btype == "table":
            blocks.append({"type": "table", "table": block["table"]})
        elif btype == "chart":
            blocks.append({"type": "chart", "chart": block["chart"]})

    # Fallback handling: if no standard display blocks are found, attach a raw JSON debug block
    if not blocks:
        blocks = [{"type": "text", "text": "*(No renderable content in agent response.)*"}]
        blocks.append({"type": "debug", "raw": parsed})

    return blocks


def render_blocks(blocks):
    """
    Renders structured content blocks into appropriate Streamlit UI components:
      - Text   -> Markdown (with LaTeX dollar sign escaping)
      - Table  -> Pandas DataFrame
      - Chart  -> Vega-Lite Chart
      - Debug  -> Expander with raw JSON payload
    """
    for block in blocks:
        if block["type"] == "text":
            # Escape single dollar signs to prevent Streamlit Markdown from treating 
            # currency figures (e.g., "$25,012...$1,968") as inline LaTeX equations
            safe_text = block["text"].replace("$", "\\$")
            st.markdown(safe_text)

        elif block["type"] == "table":
            t = block["table"]
            result_set = t.get("result_set", {})
            data = result_set.get("data", [])
            row_type = result_set.get("resultSetMetaData", {}).get("rowType", [])
            columns = [c["name"] for c in row_type]
            
            # Convert raw result_set array into a formatted Pandas DataFrame
            if data and columns:
                import pandas as pd
                df = pd.DataFrame(data, columns=columns)
                if t.get("title"):
                    st.caption(t["title"])
                st.dataframe(df, use_container_width=True)

        elif block["type"] == "chart":
            chart_spec_raw = block["chart"].get("chart_spec")
            if chart_spec_raw:
                try:
                    # Parse and display Vega-Lite visualization spec
                    spec = json.loads(chart_spec_raw)
                    st.vega_lite_chart(spec, use_container_width=True)
                except Exception as e:
                    st.caption(f"⚠️ Could not render chart: {e}")

        elif block["type"] == "debug":
            # Render collapsible JSON expander for troubleshooting unparsed payloads
            with st.expander("🔧 Debug: raw agent response (shown because no text/table/chart block was found)"):
                st.json(block["raw"])


# ------------------------------------------------------------------------
# Chat History Rendering
# Re-displays prior conversation turns stored in session state
# ------------------------------------------------------------------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant" and isinstance(msg["content"], list):
            render_blocks(msg["content"])
        else:
            st.markdown(msg["content"])

# Handle new prompt input from user
if prompt := st.chat_input("Ask about transactions, disputes, fraud alerts, or policy..."):
    # 1. Add user prompt to conversation history and render immediately
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Call Cortex Agent and render returned content blocks
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response_blocks = call_agent(prompt)
        render_blocks(response_blocks)

    # 3. Append assistant response blocks to session history
    st.session_state.messages.append({"role": "assistant", "content": response_blocks})

st.divider()

# Reset button to clear conversation history and active agent thread session
if st.button("Clear conversation"):
    st.session_state.messages = []
    st.session_state.thread_id = None
    st.rerun()
