"""
utils/agent_client.py — Shared Cortex Agent Client & Multi-Modal Rendering Client

Overview:
Reusable helper module for executing Cortex Agent queries (`COMPLIANCE_COPILOT_AGENT`) 
and rendering multi-modal response payloads across any Streamlit page.

Key Architecture Features:
  1. Centralized Agent Invocations: Wraps `SNOWFLAKE.CORTEX.DATA_AGENT_RUN` execution 
     into a reusable `call_agent()` function.
  2. Multi-turn Session Management: Returns updated `thread_id` values alongside content 
     blocks, allowing callers to maintain page-specific or document-specific conversation threads.
  3. Filtered Multi-Modal Rendering: `render_blocks()` converts parsed JSON blocks into 
     Markdown text (with dollar-sign LaTeX escaping), Pandas DataFrames (tables), 
     Vega-Lite charts, or collapsible JSON debug expanders.
"""

import json
import streamlit as st
import pandas as pd

# Fully qualified Snowflake Cortex Agent name
AGENT_NAME = "FINTECH_COPILOT.AI.COMPLIANCE_COPILOT_AGENT"


def call_agent(session, user_text: str, thread_id=None):
    """
    Calls DATA_AGENT_RUN via Snowpark with a user prompt and optional thread ID.

    Parameters:
      - session: Active Snowpark session context.
      - user_text (str): User prompt or question string.
      - thread_id (str, optional): Active conversation thread ID for multi-turn context.

    Returns:
      - (blocks, new_thread_id):
          * blocks (list[dict]): Filtered list of renderable content blocks.
          * new_thread_id (str): Updated thread ID to be stored by the caller.
    """
    # Build request payload structure required by DATA_AGENT_RUN
    request_body = {
        "messages": [
            {"role": "user", "content": [{"type": "text", "text": user_text}]}
        ]
    }
    
    # Attach existing thread ID if continuing a multi-turn conversation
    if thread_id is not None:
        request_body["thread_id"] = thread_id

    request_json = json.dumps(request_body)

    # SQL query calling the Cortex Agent function wrapper
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
        # Return structured error block on execution failure while preserving existing thread_id
        return [{"type": "text", "text": f"⚠️ Error calling agent: {e}"}], thread_id

    # Extract thread ID from response metadata (falls back to existing thread_id if absent)
    metadata = parsed.get("metadata", {})
    new_thread_id = metadata.get("thread_id", thread_id)

    # Filter content payload: retain user-facing blocks (text, table, chart)
    # and filter out internal agent reasoning steps (thinking, tool_use, tool_result)
    blocks = []
    for block in parsed.get("content", []):
        btype = block.get("type")
        if btype == "text":
            blocks.append({"type": "text", "text": block["text"]})
        elif btype == "table":
            blocks.append({"type": "table", "table": block["table"]})
        elif btype == "chart":
            blocks.append({"type": "chart", "chart": block["chart"]})

    # Fallback: Attach a debug block if no standard display blocks were generated
    if not blocks:
        blocks = [{"type": "text", "text": "*(No renderable content in agent response.)*"}]
        blocks.append({"type": "debug", "raw": parsed})

    return blocks, new_thread_id


def render_blocks(blocks):
    """
    Renders structured response content blocks into native Streamlit UI components:
      - Text   -> Streamlit Markdown (escapes $ to prevent LaTeX math parsing)
      - Table  -> Pandas DataFrame rendered as Streamlit Dataframe
      - Chart  -> Vega-Lite Chart
      - Debug  -> Collapsible expander displaying raw JSON
    """
    for block in blocks:
        if block["type"] == "text":
            # Escape single dollar signs to prevent Streamlit's Markdown engine 
            # from treating financial figures (e.g., "$2,500...$5,000") as inline LaTeX equations
            safe_text = block["text"].replace("$", "\\$")
            st.markdown(safe_text)

        elif block["type"] == "table":
            t = block["table"]
            result_set = t.get("result_set", {})
            data = result_set.get("data", [])
            row_type = result_set.get("resultSetMetaData", {}).get("rowType", [])
            columns = [c["name"] for c in row_type]
            
            # Convert raw JSON result_set into a formatted Pandas DataFrame
            if data and columns:
                df = pd.DataFrame(data, columns=columns)
                if t.get("title"):
                    st.caption(t["title"])
                st.dataframe(df, use_container_width=True)

        elif block["type"] == "chart":
            chart_spec_raw = block["chart"].get("chart_spec")
            if chart_spec_raw:
                try:
                    # Parse and render Vega-Lite visualization spec
                    spec = json.loads(chart_spec_raw)
                    st.vega_lite_chart(spec, use_container_width=True)
                except Exception as e:
                    st.caption(f"⚠️ Could not render chart: {e}")

        elif block["type"] == "debug":
            # Render raw JSON expander for troubleshooting unexpected response formats
            with st.expander("🔧 Debug: raw agent response (shown because no text/table/chart block was found)"):
                st.json(block["raw"])
