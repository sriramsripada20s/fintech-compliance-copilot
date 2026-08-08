"""
pages/2_Document_Upload.py — Document Ingestion, Summarization & Document-Scoped Chat

Overview:
End-to-end document management page for uploading raw PDF documents into the automated 
ingestion pipeline (`FINTECH_COPILOT.DOCS.DOC_STAGE`), viewing extracted field summaries, 
and conducting interactive follow-up Q&A on specific processed files using Cortex Agent.

Key Features & Architectural Flow:
  1. Server-Side Memory Streaming: Writes uploaded PDF bytes directly into `@DOCS.DOC_STAGE` 
     using `session.file.put_stream()` and `io.BytesIO`, avoiding local filesystem usage.
  2. Immediate Pipeline Execution: Offers an "EXECUTE TASK" option to manually trigger 
     `TASK_PARSE_NEW_DOCS` on demand instead of waiting for the 30-minute schedule.
  3. Real-Time Processing Status: Joins stage DIRECTORY metadata with `DOCS.PROCESSED_DOCS` 
     to render a live upload and parsing status dashboard.
  4. Direct Field/Content Summary: Bypasses AI search for file summaries by running direct 
     relational SQL queries against `DOC_FIELDS` (KYC records) or `DOC_TEXT_REDACTED` (General text).
  5. Document-Scoped Agent Chat: Integrates `utils.agent_client` to let users ask contextual 
     follow-up questions specifically prefixed for the chosen document.

Access Control:
Restricted strictly to roles with `document_upload` permission 
(COMPLIANCE_INVESTIGATOR_ROLE and CORTEX_ADMIN_ROLE).
"""

import sys
import os
import io
import streamlit as st

# Append parent directory to Python path to import root-level utility modules
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from utils.access_control import check_access, get_session, get_current_role
from utils.agent_client import call_agent, render_blocks

# Configure Streamlit page settings and browser tab metadata
st.set_page_config(page_title="Document Upload — Compliance Copilot", page_icon="📄", layout="wide")

# Enforce access control — halts page execution if active role lacks permission for 'document_upload'
check_access("document_upload")

# Render page title and current user role badge
st.title("📄 Document Upload")
st.caption(f"Role: {get_current_role()}")

# Fully qualified target stage path
STAGE_NAME = "FINTECH_COPILOT.DOCS.DOC_STAGE"

# Acquire Snowpark session from Streamlit runtime context
session = get_session()

# Page workflow overview
st.write(
    "Upload KYC forms, bank statements, or compliance policy documents. "
    "Files land in `DOCS.DOC_STAGE` and are automatically parsed, extracted, "
    "redacted, and chunked by the Phase 3 pipeline — either within 30 minutes "
    "(the scheduled task interval) or immediately if you trigger it manually below."
)

# File uploader widget accepting PDF documents
uploaded_file = st.file_uploader(
    "Choose a PDF document",
    type=["pdf"],
    help="Uploaded directly to the internal stage; picked up automatically by the pipeline.",
)

# ------------------------------------------------------------------------
# 1. Document Upload & Pipeline Execution Trigger
# Streams bytes into stage memory and offers an immediate task execution button
# ------------------------------------------------------------------------
if uploaded_file is not None:
    st.write(f"Selected: `{uploaded_file.name}` ({uploaded_file.size:,} bytes)")

    # Button to stream uploaded file into internal stage
    if st.button("Upload to stage", type="primary"):
        try:
            # Read file bytes into memory buffer
            file_bytes = uploaded_file.getvalue()
            
            # Stream bytes into Snowflake internal stage
            session.file.put_stream(
                io.BytesIO(file_bytes),
                f"@{STAGE_NAME}/{uploaded_file.name}",
                auto_compress=False,
                overwrite=True,
            )
            st.success(f"✅ Uploaded `{uploaded_file.name}` to the stage.")

            # Refresh stage directory metadata immediately for UI tracking
            session.sql(f"ALTER STAGE {STAGE_NAME} REFRESH").collect()

        except Exception as e:
            st.error(f"⚠️ Upload failed: {e}")

    st.divider()
    
    # Button to manually execute root automation task and bypass 30-minute schedule
    if st.button("⚡ Process now (skip the 30-minute wait)"):
        with st.spinner("Triggering pipeline..."):
            try:
                # Trigger root pipeline task on demand
                session.sql(
                    "EXECUTE TASK FINTECH_COPILOT.DOCS.TASK_PARSE_NEW_DOCS"
                ).collect()
                st.success(
                    "Pipeline triggered. Parsing/extraction/redaction/chunking "
                    "typically completes within 1-2 minutes — refresh the "
                    "status table below to check."
                )
            except Exception as e:
                st.error(f"⚠️ Could not trigger task: {e}")

st.divider()

# ------------------------------------------------------------------------
# 2. Upload & Processing Status Dashboard
# Displays stage DIRECTORY contents joined with processing status tracker
# ------------------------------------------------------------------------
st.subheader("Upload & processing status")

# Manual refresh button to reload processing status table
if st.button("🔄 Refresh status"):
    st.rerun()


@st.cache_data(ttl=30)
def load_status():
    """
    Queries stage directory metadata left-joined with DOCS.PROCESSED_DOCS
    to display processing states for the 25 most recent files.
    Cached for 30 seconds (TTL = 30s).
    """
    query = f"""
        SELECT
            d.relative_path,
            d.last_modified AS uploaded_at,
            p.status AS pipeline_status,
            p.processed_at
        FROM DIRECTORY(@{STAGE_NAME}) d
        LEFT JOIN FINTECH_COPILOT.DOCS.PROCESSED_DOCS p
            ON d.relative_path = p.file_path
        ORDER BY d.last_modified DESC
        LIMIT 25
    """
    return session.sql(query).to_pandas()


# Safely execute status query with error fallback
try:
    status_df = load_status()
    if not status_df.empty:
        status_df["PIPELINE_STATUS"] = status_df["PIPELINE_STATUS"].fillna("⏳ Not yet processed")
        st.dataframe(status_df, use_container_width=True)
    else:
        st.caption("No documents in the stage yet.")
        status_df = None
except Exception as e:
    st.error(f"Could not load status: {e}")
    status_df = None

# ------------------------------------------------------------------------
# 3. Direct Document Summary & Contextual Follow-Up Chat
# Direct relational query fetches extracted KYC fields or redacted text.
# The Cortex Agent handles contextual follow-up questions.
# ------------------------------------------------------------------------
st.divider()
st.subheader("Document summary & follow-up questions")

if status_df is not None and not status_df.empty:
    # Filter list to show only files that have completed processing
    processed_files = status_df[status_df["PIPELINE_STATUS"] != "⏳ Not yet processed"]["RELATIVE_PATH"].tolist()

    if not processed_files:
        st.caption("No documents have finished processing yet — check back after running the pipeline.")
    else:
        # Dropdown to select a processed file for summary and Q&A
        selected_file = st.selectbox("Select a processed document to summarize", processed_files)

        if selected_file:
            # 3A. Query extracted KYC fields from DOC_FIELDS
            summary_query = """
                SELECT full_name, date_of_birth, ssn, address, email, phone, id_type, id_number
                FROM FINTECH_COPILOT.DOCS.DOC_FIELDS
                WHERE relative_path = ?
            """
            fields_result = session.sql(summary_query, params=[selected_file]).to_pandas()

            if not fields_result.empty:
                st.write("**Extracted KYC fields:**")
                st.dataframe(fields_result, use_container_width=True)
            else:
                # 3B. Fallback: If not a KYC doc, fetch redacted text from DOC_TEXT_REDACTED
                text_query = """
                    SELECT redacted_text
                    FROM FINTECH_COPILOT.DOCS.DOC_TEXT_REDACTED
                    WHERE relative_path = ?
                """
                text_result = session.sql(text_query, params=[selected_file]).to_pandas()
                if not text_result.empty:
                    st.write("**Document content (redacted):**")
                    st.text(text_result.iloc[0]["REDACTED_TEXT"])
                else:
                    st.caption("No extracted fields or redacted text found for this document yet.")

            # ------------------------------------------------------------
            # 3C. Document-Scoped Interactive Chat
            # Uses document-specific session state key (`doc_chat_<filename>`)
            # ------------------------------------------------------------
            st.write("**Ask a follow-up question:**")

            doc_chat_key = f"doc_chat_{selected_file}"
            if doc_chat_key not in st.session_state:
                st.session_state[doc_chat_key] = {"messages": [], "thread_id": None}

            # Render existing chat history for the selected document
            for msg in st.session_state[doc_chat_key]["messages"]:
                with st.chat_message(msg["role"]):
                    if msg["role"] == "assistant" and isinstance(msg["content"], list):
                        render_blocks(msg["content"])
                    else:
                        st.markdown(msg["content"])

            # Input widget for document follow-up questions
            followup = st.chat_input(
                f"Ask about {selected_file}...", key=f"input_{selected_file}"
            )
            if followup:
                # 1. Save user prompt into document chat state
                st.session_state[doc_chat_key]["messages"].append(
                    {"role": "user", "content": followup}
                )
                with st.chat_message("user"):
                    st.markdown(followup)

                # 2. Invoke Cortex Agent with document-scoped prompt string
                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        blocks, new_thread_id = call_agent(
                            session,
                            f"Regarding the document {selected_file}: {followup}",
                            st.session_state[doc_chat_key]["thread_id"],
                        )
                        st.session_state[doc_chat_key]["thread_id"] = new_thread_id
                    render_blocks(blocks)

                # 3. Save assistant response blocks into document chat state
                st.session_state[doc_chat_key]["messages"].append(
                    {"role": "assistant", "content": blocks}
                )
else:
    st.caption("Upload a document above to see its summary here once processed.")
