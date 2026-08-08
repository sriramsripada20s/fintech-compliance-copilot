"""
pages/1_Chat.py — multi-turn chat against COMPLIANCE_COPILOT_AGENT (Phase 6),
via SNOWFLAKE.CORTEX.DATA_AGENT_RUN.

Agent-calling and rendering logic lives in utils/agent_client.py, shared
with the follow-up chat on the Document Upload page.
"""

import sys
import os
import streamlit as st

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from utils.access_control import check_access, get_current_role, get_session
from utils.agent_client import call_agent, render_blocks

st.set_page_config(page_title="Chat — Compliance Copilot", page_icon="💬", layout="wide")

check_access("chat")

st.title("💬 Compliance Copilot Chat")
st.caption(f"Role: {get_current_role()}")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
if "parent_message_id" not in st.session_state:
    st.session_state.parent_message_id = None

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant" and isinstance(msg["content"], list):
            render_blocks(msg["content"])
        else:
            st.markdown(msg["content"])

if prompt := st.chat_input("Ask about transactions, disputes, fraud alerts, or policy..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            session = get_session()
            response_blocks, new_thread_id, new_parent_id = call_agent(
                session,
                prompt,
                st.session_state.thread_id,
                st.session_state.parent_message_id,
            )
            st.session_state.thread_id = new_thread_id
            st.session_state.parent_message_id = new_parent_id
        render_blocks(response_blocks)

    st.session_state.messages.append({"role": "assistant", "content": response_blocks})

st.divider()
if st.button("Clear conversation"):
    st.session_state.messages = []
    st.session_state.thread_id = None
    st.session_state.parent_message_id = None
    st.rerun()
