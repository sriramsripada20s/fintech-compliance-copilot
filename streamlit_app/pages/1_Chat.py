"""
pages/1_Chat.py — Compliance Copilot Chat Interface (Phase 6 Integration)

Overview:
Multi-turn conversational chat interface powered by Snowflake Cortex Agent (`COMPLIANCE_COPILOT_AGENT`).

Key Features:
  1. Access Control: Imports central RBAC check (`check_access("chat")`) to enforce role gating.
  2. Multi-turn Session State: Maintains full conversation history in `st.session_state.messages`.
  3. Interactive UI: Native Streamlit chat components (`st.chat_message`, `st.chat_input`) with 
     a "Clear conversation" utility to reset state.

Note on Integration:
This file serves as the UI skeleton. The stubbed response block will be replaced with direct 
Cortex Agent REST API calls passing the full `messages` history payload.
"""

import sys
import os
import streamlit as st

# Append parent directory to Python path to import root-level utility modules
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from utils.access_control import check_access, get_current_role

# Configure Streamlit page settings and browser tab metadata
st.set_page_config(page_title="Chat — Compliance Copilot", page_icon="💬", layout="wide")

# Enforce access control — redirects or halts execution if active role lacks permission for 'chat'
check_access("chat")

# Render page title and current user role badge
st.title("💬 Compliance Copilot Chat")
st.caption(f"Role: {get_current_role()}")

# ------------------------------------------------------------------------
# Conversation History Management (Session State)
# Initializes and persists chat history across rerun cycles.
# Full conversation array is formatted to match the Cortex Agent API requirement.
# ------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

# Re-render all existing conversation messages from session state
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ------------------------------------------------------------------------
# Chat Input & User Prompt Handler
# Listens for user text input and appends user/assistant messages to session state.
# ------------------------------------------------------------------------
if prompt := st.chat_input("Ask about transactions, disputes, fraud alerts, or policy..."):
    # 1. Append user prompt to message history array
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # 2. Render user message in chat container
    with st.chat_message("user"):
        st.markdown(prompt)

    # 3. Render assistant response container
    with st.chat_message("assistant"):
        # Placeholder indicator for Agent REST integration
        # Target Endpoint: POST /api/v2/databases/FINTECH_COPILOT/schemas/AI/agents/COMPLIANCE_COPILOT_AGENT:run
        st.info(
            "🚧 STUB — this will call COMPLIANCE_COPILOT_AGENT once the "
            "REST integration is wired up. Your message was received but "
            "not yet sent to the agent."
        )
        
        stub_response = (
            "*(stub response — agent integration pending)*"
        )
        st.markdown(stub_response)

    # 4. Append assistant response to message history array
    st.session_state.messages.append({"role": "assistant", "content": stub_response})

st.divider()

# ------------------------------------------------------------------------
# Utility: Reset Conversation History
# Clears persistent session state and triggers a page rerun.
# ------------------------------------------------------------------------
if st.button("Clear conversation"):
    st.session_state.messages = []
    st.rerun()
