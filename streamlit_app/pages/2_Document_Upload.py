"""
pages/2_Document_Upload.py — upload documents into the Phase 3 pipeline.

Wired to session.file.put_stream(), which writes the uploaded file's bytes
directly to @DOCS.DOC_STAGE — no local filesystem involved (SiS runs
server-side, there's no "local disk" in the traditional sense).

After upload, the file sits in the stage until the next scheduled run of
TASK_PARSE_NEW_DOCS (every 30 min) or a manual trigger. This page shows
both options and a live status table so the user can see when it's picked
up rather than wondering if the upload silently did nothing.
"""

import sys
import os
import io
import streamlit as st

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from utils.access_control import check_access, get_session, get_current_role
from utils.agent_client import call_agent, render_blocks

st.set_page_config(page_title="Document Upload — Compliance Copilot", page_icon="📄", layout="wide")

check_access("document_upload")

st.title("📄 Document Upload")
st.caption(f"Role: {get_current_role()}")

STAGE_NAME = "FINTECH_COPILOT.DOCS.DOC_STAGE"

session = get_session()

st.write(
    "Upload KYC forms, bank statements, or compliance policy documents. "
    "Files land in `DOCS.DOC_STAGE` and are automatically parsed, extracted, "
    "redacted, and chunked by the Phase 3 pipeline — either within 30 minutes "
    "(the scheduled task interval) or immediately if you trigger it manually below."
)

uploaded_file = st.file_uploader(
    "Choose a PDF document",
    type=["pdf"],
    help="Uploaded directly to the internal stage; picked up automatically by the pipeline.",
)

if uploaded_file is not None:
    st.write(f"Selected: `{uploaded_file.name}` ({uploaded_file.size:,} bytes)")

    if st.button("Upload to stage", type="primary"):
        try:
            file_bytes = uploaded_file.getvalue()
            session.file.put_stream(
                io.BytesIO(file_bytes),
                f"@{STAGE_NAME}/{uploaded_file.name}",
                auto_compress=False,
                overwrite=True,
            )
            st.success(f"✅ Uploaded `{uploaded_file.name}` to the stage.")

            # Refresh the directory table so it's immediately visible below,
            # without waiting for the next scheduled task run to notice it.
            session.sql(f"ALTER STAGE {STAGE_NAME} REFRESH").collect()

        except Exception as e:
            st.error(f"⚠️ Upload failed: {e}")

    st.divider()
    if st.button("⚡ Process now (skip the 30-minute wait)"):
        with st.spinner("Triggering pipeline..."):
            try:
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
st.subheader("Upload & processing status")

if st.button("🔄 Refresh status"):
    st.rerun()


@st.cache_data(ttl=30)
def load_status():
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

# ----------------------------------------------------------------------------
# Document summary + follow-up chat, for a processed file the user picks.
# Summary is a direct query against DOC_FIELDS/DOC_TEXT_REDACTED — NOT routed
# through the Agent — since we already know exactly which file we mean,
# a direct lookup is cheaper and more reliable than hoping Search retrieves
# the right chunk. The follow-up chat below DOES use the Agent, since open-
# ended questions genuinely need its reasoning/routing.
# ----------------------------------------------------------------------------
st.divider()
st.subheader("Document summary & follow-up questions")

if status_df is not None and not status_df.empty:
    processed_files = status_df[status_df["PIPELINE_STATUS"] != "⏳ Not yet processed"]["RELATIVE_PATH"].tolist()

    if not processed_files:
        st.caption("No documents have finished processing yet — check back after running the pipeline.")
    else:
        selected_file = st.selectbox("Select a processed document to summarize", processed_files)

        if selected_file:
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
                # Not a KYC doc (or no fields extracted) — fall back to
                # showing the redacted text directly.
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

            # ---- Follow-up chat, scoped to this document selection ----
            st.write("**Ask a follow-up question:**")

            doc_chat_key = f"doc_chat_{selected_file}"
            if doc_chat_key not in st.session_state:
                st.session_state[doc_chat_key] = {
                    "messages": [], "thread_id": None, "parent_message_id": None
                }

            for msg in st.session_state[doc_chat_key]["messages"]:
                with st.chat_message(msg["role"]):
                    if msg["role"] == "assistant" and isinstance(msg["content"], list):
                        render_blocks(msg["content"])
                    else:
                        st.markdown(msg["content"])

            followup = st.chat_input(
                f"Ask about {selected_file}...", key=f"input_{selected_file}"
            )
            if followup:
                st.session_state[doc_chat_key]["messages"].append(
                    {"role": "user", "content": followup}
                )
                with st.chat_message("user"):
                    st.markdown(followup)

                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        blocks, new_thread_id, new_parent_id = call_agent(
                            session,
                            f"Regarding the document {selected_file}: {followup}",
                            st.session_state[doc_chat_key]["thread_id"],
                            st.session_state[doc_chat_key]["parent_message_id"],
                        )
                        st.session_state[doc_chat_key]["thread_id"] = new_thread_id
                        st.session_state[doc_chat_key]["parent_message_id"] = new_parent_id
                    render_blocks(blocks)

                st.session_state[doc_chat_key]["messages"].append(
                    {"role": "assistant", "content": blocks}
                )
else:
    st.caption("Upload a document above to see its summary here once processed.")
