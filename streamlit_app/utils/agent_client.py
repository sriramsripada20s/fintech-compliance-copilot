"""
utils/agent_client.py — shared DATA_AGENT_RUN calling + response rendering.

Extracted from pages/1_Chat.py so any page can have an agent-powered chat
without duplicating the request/response handling logic. Callers manage
their own session_state keys for messages/thread_id (namespaced per page)
so multiple independent conversations don't collide.
"""

import json
import streamlit as st
import pandas as pd

AGENT_NAME = "FINTECH_COPILOT.AI.COMPLIANCE_COPILOT_AGENT"


def call_agent(session, user_text: str, thread_id=None, parent_message_id=None):
    """
    Calls DATA_AGENT_RUN with a new user message.

    Returns (blocks, new_thread_id, new_parent_message_id). Continuing a
    thread requires BOTH thread_id and parent_message_id — thread_id alone
    is not enough; DATA_AGENT_RUN rejects a second message on an existing
    thread with "parent_message_id cannot be null" if it's omitted. The
    caller must store and pass back both on every subsequent call.
    """
    content = [{"type": "text", "text": user_text}]
    message = {"role": "user", "content": content}

    request_body = {"messages": [message]}
    if thread_id is not None:
        request_body["thread_id"] = thread_id
    if parent_message_id is not None:
        request_body["parent_message_id"] = parent_message_id

    request_json = json.dumps(request_body)

    query = """
        SELECT SNOWFLAKE.CORTEX.DATA_AGENT_RUN(
            ?,
            ?,
            TRUE
        ) AS response
    """

    try:
        result = session.sql(query, params=[AGENT_NAME, request_json]).collect()
        raw_response = result[0]["RESPONSE"]
        parsed = json.loads(raw_response)
    except Exception as e:
        return [{"type": "text", "text": f"⚠️ Error calling agent: {e}"}], thread_id, parent_message_id

    metadata = parsed.get("metadata", {})
    new_thread_id = metadata.get("thread_id", thread_id)
    new_parent_message_id = metadata.get("assistant_message_id", parent_message_id)

    blocks = []
    for block in parsed.get("content", []):
        btype = block.get("type")
        if btype == "text":
            blocks.append({"type": "text", "text": block["text"]})
        elif btype == "table":
            blocks.append({"type": "table", "table": block["table"]})
        elif btype == "chart":
            blocks.append({"type": "chart", "chart": block["chart"]})

    if not blocks:
        blocks = [{"type": "text", "text": "*(No renderable content in agent response.)*"}]
        blocks.append({"type": "debug", "raw": parsed})

    return blocks, new_thread_id, new_parent_message_id


def render_blocks(blocks):
    """Renders a list of content blocks — text as markdown (with $ escaped
    to avoid Streamlit's LaTeX math-mode parsing), table as a dataframe,
    chart as a Vega-Lite spec, debug as a collapsed raw-JSON expander."""
    for block in blocks:
        if block["type"] == "text":
            safe_text = block["text"].replace("$", "\\$")
            st.markdown(safe_text)

        elif block["type"] == "table":
            t = block["table"]
            result_set = t.get("result_set", {})
            data = result_set.get("data", [])
            row_type = result_set.get("resultSetMetaData", {}).get("rowType", [])
            columns = [c["name"] for c in row_type]
            if data and columns:
                df = pd.DataFrame(data, columns=columns)
                if t.get("title"):
                    st.caption(t["title"])
                st.dataframe(df, use_container_width=True)

        elif block["type"] == "chart":
            chart_spec_raw = block["chart"].get("chart_spec")
            if chart_spec_raw:
                try:
                    spec = json.loads(chart_spec_raw)
                    st.vega_lite_chart(spec, use_container_width=True)
                except Exception as e:
                    st.caption(f"⚠️ Could not render chart: {e}")

        elif block["type"] == "debug":
            with st.expander("🔧 Debug: raw agent response (shown because no text/table/chart block was found)"):
                st.json(block["raw"])
