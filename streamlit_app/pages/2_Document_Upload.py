"""
pages/2_Document_Upload.py — Document Upload & Pipeline Trigger Page (Phase 3 & 7 Integration)

Overview:
Interface for uploading raw PDF documents (KYC forms, bank statements, compliance policies)
into the automated document ingestion pipeline (`FINTECH_COPILOT.DOCS.DOC_STAGE`).

Technical Architecture Notes:
  1. Server-Side Stage Upload: Uses `session.file.put_stream()` with an in-memory `io.BytesIO` 
     buffer to write uploaded file bytes directly into Snowflake's internal stage `@DOCS.DOC_STAGE` 
     without needing a local filesystem.
  2. Directory Refresh: Triggers `ALTER STAGE REFRESH` immediately after write so stage 
     directory tables recognize the new file without waiting for periodic background tasks.
  3. On-Demand Pipeline Execution: Provides an "EXECUTE TASK" option to manually fire 
     `TASK_PARSE_NEW_DOCS`, allowing users to process uploaded files instantly rather than 
     waiting for the 30-minute scheduled polling cycle.
  4. Real-Time Status Tracking: Joins stage DIRECTORY metadata with `DOCS.PROCESSED_DOCS` to 
     display a live processing status table for recent uploads.

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

# Page introduction & pipeline workflow explanation
st.write(
    "Upload KYC forms, bank statements, or compliance policy documents. "
    "Files land in `DOCS.DOC_STAGE` and are automatically parsed, extracted, "
    "redacted, and chunked by the Phase 3 pipeline — either within 30 minutes "
    "(the scheduled task interval) or immediately if you trigger it manually below."
)

# File uploader widget accepting PDF files
uploaded_file = st.file_uploader(
    "Choose a PDF document",
    type=["pdf"],
    help="Uploaded directly to the internal stage; picked up automatically by the pipeline.",
)

# ------------------------------------------------------------------------
# Document Upload & Manual Task Execution Logic
# Handles memory streaming into stage and optional task trigger
# ------------------------------------------------------------------------
if uploaded_file is not None:
    st.write(f"Selected: `{uploaded_file.name}` ({uploaded_file.size:,} bytes)")

    # Button to execute Stream Put into Stage
    if st.button("Upload to stage", type="primary"):
        try:
            # 1. Read uploaded file bytes into an in-memory Byte stream
            file_bytes = uploaded_file.getvalue()
            
            # 2. Upload byte stream directly into Snowflake internal stage
            session.file.put_stream(
                io.BytesIO(file_bytes),
                f"@{STAGE_NAME}/{uploaded_file.name}",
                auto_compress=False,
                overwrite=True,
            )
            st.success(f"✅ Uploaded `{uploaded_file.name}` to the stage.")

            # 3. Refresh stage directory metadata immediately for live tracking
            session.sql(f"ALTER STAGE {STAGE_NAME} REFRESH").collect()

        except Exception as e:
            st.error(f"⚠️ Upload failed: {e}")

    st.divider()
    
    # Optional button to bypass 30-minute task schedule and trigger root task immediately
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
# Live Status Dashboard
# Displays stage DIRECTORY files joined with processing status tracker
# ------------------------------------------------------------------------
st.subheader("Upload & processing status")

# Manual refresh button to trigger page rerun and re-fetch status table
if st.button("🔄 Refresh status"):
    st.rerun()


@st.cache_data(ttl=30)
def load_status():
    """
    Queries stage directory metadata left-joined with DOCS.PROCESSED_DOCS
    to display processing states for the 25 most recent files.
    Cached for 30 seconds (TTL = 30s) for responsive UI rendering.
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


# Safely load and display status DataFrame with fallback formatting
try:
    status_df = load_status()
    if not status_df.empty:
        # Format unprocessed status nulls with an informative status label
        status_df["PIPELINE_STATUS"] = status_df["PIPELINE_STATUS"].fillna("⏳ Not yet processed")
        st.dataframe(status_df, use_container_width=True)
    else:
        st.caption("No documents in the stage yet.")
except Exception as e:
    st.error(f"Could not load status: {e}")
