"""
pages/2_Document_Upload.py — upload documents into the Phase 3 pipeline.

STUB: page structure and role gating in place. Actual upload-to-stage
logic (session.file.put_stream or equivalent) not yet wired up.
"""

import sys
import os
import streamlit as st

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from utils.access_control import check_access, get_session, get_current_role

st.set_page_config(page_title="Document Upload — Compliance Copilot", page_icon="📄", layout="wide")

check_access("document_upload")

st.title("📄 Document Upload")
st.caption(f"Role: {get_current_role()}")

st.write(
    "Upload KYC forms, bank statements, or compliance policy documents. "
    "Files land in `DOCS.DOC_STAGE` and are automatically parsed, extracted, "
    "redacted, and chunked by the Phase 3 pipeline (typically within 30 minutes, "
    "or immediately if manually triggered)."
)

uploaded_file = st.file_uploader(
    "Choose a PDF document",
    type=["pdf"],
    help="Files are uploaded to the internal stage and picked up by the automated pipeline.",
)

if uploaded_file is not None:
    st.warning(
        "🚧 STUB — file selected but not yet uploaded to the stage. "
        "The actual `PUT` to `@DOCS.DOC_STAGE` is not wired up yet."
    )
    st.write(f"Selected file: `{uploaded_file.name}` ({uploaded_file.size:,} bytes)")

st.divider()
st.subheader("Recent uploads")
st.caption("STUB — will show the last N files from `DIRECTORY(@DOCS.DOC_STAGE)` with their processing status.")

session = get_session()
# TODO: query DIRECTORY(@DOCS.DOC_STAGE) joined against PROCESSED_DOCS to
# show upload + processing status in a table here.
