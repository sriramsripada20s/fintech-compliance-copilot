# Fintech Customer Intelligence & Compliance Copilot
 
> A production-grade Snowflake GenAI + dbt project unifying structured transactional data and unstructured compliance documents behind a single RBAC-governed, AI-powered interface.

https://github.com/user-attachments/assets/2c383f6e-d687-42b2-ae1c-a055f4aa0340
---
 
## Technical Architecture Overview
 
| Layer | Technology / Feature |
| :--- | :--- |
| **Data Warehouse** | Snowflake (Trial Account) |
| **Transformation & Modeling** | dbt Core, deployed natively via Snowflake `DBT PROJECT` objects |
| **Structured AI (Text-to-SQL)** | Snowflake Cortex Analyst (Semantic Views, Verified Queries) |
| **Unstructured AI (RAG & Extraction)** | Snowflake Cortex Search, `AI_PARSE_DOCUMENT`, `AI_EXTRACT`, `AI_REDACT` |
| **Orchestration & Agentic AI** | Snowflake Cortex Agents (Multi-Tool Routing), GPA Framework Evaluations |
| **Generative & Analytical AI Functions** | `AI_CLASSIFY`, `AI_SENTIMENT`, `AI_SUMMARIZE_AGG` |
| **Automation & Pipeline Control** | Snowflake Streams + Tasks (Event-Driven, Stream-Gated Cost Guards) |
| **Application Layer** | Streamlit in Snowflake (SiS) (Warehouse Runtime Engine) |
| **Deployment & Continuous Integration** | Native Snowflake Git Integration (GitHub Integration, Pull-Based Auto-Sync) |
| **Governance & Observability** | Snowflake RBAC, Resource Monitors, Native Email Alerting Integrations |
| **Implementation Languages** | SQL, Python (Snowpark DataFrames, Streamlit) |


   **<img width="686" height="782" alt="image" src="https://github.com/user-attachments/assets/132f3e64-9e1b-43ae-afc1-ececd1c54f4b" />**

---
 
## Executive Summary & Business Problem
 
Fintech compliance, risk, and fraud investigation teams routinely operate across two isolated data siloes:
 
1. **Structured Transactional Data:** High-throughput relational tables containing transactions, disputes, fraud alert scores, and customer metadata.
2. **Unstructured Compliance Documents:** Unstructured PDF/image files including KYC application forms, utility bills, bank statements, and evolving regulatory policy frameworks.
Cross-referencing these sources currently requires manual lookup across different systems — a process that is slow, error-prone, costly, and difficult to audit.
 
### The Solution
 
This repository delivers an end-to-end, automated, and AI-governed compliance platform built natively inside Snowflake. The system:
 
- **Ingests and processes compliance documents automatically** — parsing, structured-field extraction, PII redaction, and semantic indexing occur without manual intervention
- **Answers natural-language questions that span both data modalities** — a single conversational interface resolves questions requiring structured aggregation, document retrieval, or both, orchestrated automatically
- **Enforces role-based access at the data layer**, not merely the presentation layer — a support agent and a compliance investigator querying the identical system receive genuinely different, correctly scoped results
- **Is fully cost-governed and observable** — every Cortex AI capability incurs metered, token-based spend, and this system tracks, gates, and alerts on that spend as a first-class concern, not an afterthought
---
 
## Data Sources & Schema Overview
 
Synthetic fintech data, generated deterministically (`Faker.seed(42)`) for reproducibility:
 
| Table | Row Count | Grain |
| :--- | :--- | :--- |
| `RAW.CUSTOMERS` | 2,000 | 1 row per customer |
| `RAW.TRANSACTIONS` | 20,000 | 1 row per transaction |
| `RAW.DISPUTES` | 600 | 1 row per disputed transaction |
| `RAW.SUPPORT_TICKETS` | 1,500 | 1 row per support ticket |
| `RAW.FRAUD_ALERTS` | 400 | 1 row per fraud alert |
 
Complemented by 10 synthetic compliance documents: 5 KYC identification forms, 3 regulatory policy documents, and 2 bank statements — one of which was deliberately rasterized into a genuinely image-only PDF to provide an authentic OCR-mode test case, rather than validating parsing logic against born-digital text alone.
 
**Schema architecture:**
`RAW` (landed data) → `STAGING` (dbt views, 1:1 cleaned) → `INTERMEDIATE` (joined models) → `MARTS` (fact/dimension tables, AI-enriched) → `DOCS` (document stage, parsed text, RBAC-tagged chunks) → `AI` (Cortex Search Service, Cortex Agent) → `APP` (Streamlit application, dbt project object).

---
 
## Data Governance & Security
 
- **Three-tier RBAC model:** `CORTEX_ADMIN_ROLE` (full administrative access), `COMPLIANCE_INVESTIGATOR_ROLE` (full structured data + Cortex Analyst + Cortex Search), `SUPPORT_AGENT_ROLE` (Cortex Search only, scoped to non-sensitive document categories)
- **Access control enforced at the data layer:** Cortex Search filters retrieval results by an `allowed_roles` array attribute at query time; Cortex Analyst access is independently gated via the `CORTEX_ANALYST_USER` database role grant — security that persists regardless of which client or interface issues the query
- **PII minimization by design:** `AI_REDACT` strips personally identifiable information from document text *before* it is chunked or indexed — raw, unmasked PII exists in exactly one location, the structured `DOC_FIELDS` extraction table, itself governed by the same RBAC model
- **Cost governance:** a Resource Monitor enforces a warehouse-level credit quota with tiered notification thresholds; native email alerting surfaces task failures without requiring an external monitoring service
**Insert:** RBAC proof-of-concept — `SUPPORT_AGENT_ROLE` search results alongside `COMPLIANCE_INVESTIGATOR_ROLE` search results for the identical query
 
---
 
## Phase 1 — Foundational Layer - Warehouses, dbt Layers - Staging, Intermediate, Mart
 
Established the medallion schema architecture, a right-sized auto-suspending warehouse, the RBAC role skeleton, synthetic seed data, and dbt staging models with comprehensive test coverage.
 
```sql
CREATE WAREHOUSE FINTECH_COPILOT_WH
  WAREHOUSE_SIZE = 'XSMALL'
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE;
 
CREATE SCHEMA RAW;
CREATE SCHEMA STAGING;
CREATE SCHEMA MARTS;
 
CREATE ROLE COMPLIANCE_INVESTIGATOR_ROLE;
CREATE ROLE SUPPORT_AGENT_ROLE;
```
 
```yaml
# dbt schema test example
- name: stg_customers
  columns:
    - name: customer_id
      tests: [unique, not_null]
    - name: risk_tier
      tests:
        - accepted_values:
            values: ['LOW', 'MEDIUM', 'HIGH']
```
 
**<img width="1753" height="822" alt="image" src="https://github.com/user-attachments/assets/3a2e5350-b2c9-4aa3-a5f1-a92c033c3e77" />**

**<img width="1412" height="737" alt="image" src="https://github.com/user-attachments/assets/da0e4b60-29f1-49f7-851c-c8988ced3b4b" />**


---
 
## Phase 2 — AI Functions
 
Applied `AI_CLASSIFY`, `AI_SENTIMENT`, `AI_REDACT`, and `AI_SUMMARIZE_AGG` to support ticket data as native dbt models. This phase surfaced a genuine optimizer-level defect: chaining an AI function's output directly into JSON path extraction within a single query silently corrupted results — resolved by enforcing explicit materialization boundaries.
 
```sql
-- Materialize the AI output first, in isolation
select
    ticket_id,
    AI_REDACT(message_text, ['NAME','EMAIL','PHONE_NUMBER','ADDRESS'])::varchar as redacted_text
from stg_support_tickets;
 
-- Classify and score sentiment in a separate downstream model
select
    ticket_id,
    AI_CLASSIFY(redacted_text, ['BILLING','FRAUD_DISPUTE','KYC_ACCOUNT',
        'TECHNICAL_ISSUE','GENERAL_INQUIRY','COMPLAINT']):labels[0]::varchar as ticket_category,
    AI_SENTIMENT(redacted_text):categories[0]:sentiment::varchar as sentiment
from int_support_tickets_redacted;
```
 
**FCT_SUPPORT_TICKETS` query result showing category, sentiment, and redacted text together**

**<img width="1720" height="557" alt="image" src="https://github.com/user-attachments/assets/17472671-e013-4e75-a568-d758795667b0" />**
 
---
 
## Phase 3 — Document Processing
 
Implemented `AI_PARSE_DOCUMENT` (both LAYOUT and OCR modes), `AI_EXTRACT`, and `AI_REDACT` within a fully automated five-task Streams + Tasks pipeline, complete with error logging and a human-review queue for exception handling.
 
```sql
-- LAYOUT mode for born-digital documents; OCR mode for scanned images
AI_PARSE_DOCUMENT(
    TO_FILE('@DOC_STAGE', relative_path),
    {'mode': CASE WHEN relative_path ILIKE '%scanned%' THEN 'OCR' ELSE 'LAYOUT' END}
)
 
-- Structured field extraction from unstructured text
AI_EXTRACT(
    text => extracted_text,
    responseFormat => {
        'full_name': 'What is the applicant''s full legal name?',
        'ssn': 'What is the applicant''s Social Security Number?'
    }
)
 
-- Root task fires only when the stream reports genuine new activity —
-- a zero-cost skip otherwise
CREATE TASK TASK_PARSE_NEW_DOCS
  SCHEDULE = '30 MINUTE'
  WHEN SYSTEM$STREAM_HAS_DATA('DOC_STAGE_STREAM')
AS ...
```
 
**TASK_HISTORY()` output confirming all five tasks succeeded in correct dependency order**
<img width="1316" height="662" alt="image" src="https://github.com/user-attachments/assets/9829fa92-1cdb-420b-bfc0-4e68a077199c" />

---
 
## Phase 4 — Cortex Search
 
Chunked redacted document text and tagged each chunk with an `allowed_roles` array, then indexed the result into a Cortex Search Service — unifying retrieval-augmented generation with role-based access control at the retrieval layer itself.
 
```sql
CREATE TABLE DOC_CHUNKS (
    chunk_id STRING, relative_path STRING, doc_type STRING,
    allowed_roles ARRAY, chunk_text STRING
);
 
CREATE CORTEX SEARCH SERVICE CS_COMPLIANCE_DOCS
  ON chunk_text
  ATTRIBUTES doc_type, relative_path, allowed_roles
  WAREHOUSE = FINTECH_COPILOT_WH
  TARGET_LAG = '1 hour'
  AS (SELECT chunk_id, relative_path, doc_type, allowed_roles, chunk_text FROM DOC_CHUNKS);
 
-- RBAC-filtered retrieval — the identical mechanism used by the application
SELECT SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
    'CS_COMPLIANCE_DOCS',
    '{"query": "KYC requirements", "filter": {"@contains": {"allowed_roles": "SUPPORT_AGENT_ROLE"}}}'
);
```
 **<img width="1742" height="660" alt="image" src="https://github.com/user-attachments/assets/7746caeb-b68e-46d4-8c5e-e1b0615aa03b" />**
---
 
## Phase 5 — Cortex Analyst
 
Constructed a Semantic View spanning customers, transactions, disputes, and fraud alerts — defining facts, dimensions, metrics, and relationships, augmented with Verified Queries to improve text-to-SQL accuracy on known question patterns.
 
```sql
CREATE SEMANTIC VIEW SV_FRAUD_OPS
  TABLES (
    cust AS DIM_CUSTOMERS PRIMARY KEY (customer_id),
    txn AS FCT_TRANSACTIONS PRIMARY KEY (txn_id)
  )
  RELATIONSHIPS (txn_to_cust AS txn (customer_id) REFERENCES cust (customer_id))
  METRICS (
    txn.flagged_volume AS SUM(CASE WHEN txn.is_flagged THEN txn.amount_fact ELSE 0 END)
      WITH SYNONYMS = ('total flagged transaction volume')
  )
  DIMENSIONS (cust.risk_tier);
```

> 📸 **Cortex Analyst generating correct SQL from a natural-language question**
> <img width="1690" height="852" alt="cortex_analyst" src="https://github.com/user-attachments/assets/17e9acca-65a6-48d4-b362-b047d2e6240b" />
 
---
 
## Phase 6 — Cortex Agent & Evaluation
 
Deployed a Cortex Agent orchestrating both the Analyst and Search tools, governed by explicit disambiguation instructions, and formally assessed using Snowflake's GPA (Goal-Plan-Action) evaluation framework.
 
```sql
CREATE AGENT COMPLIANCE_COPILOT_AGENT FROM SPECIFICATION $$
models:
  orchestration: auto
instructions:
  orchestration: >
    Route quantitative questions to FraudOpsAnalyst. Route policy questions
    to ComplianceSearch. "KYC status" is a DATA lookup; "KYC requirements"
    is a POLICY question — decide based on intent, not keyword matching.
tools:
  - tool_spec: {type: cortex_analyst_text_to_sql, name: FraudOpsAnalyst}
  - tool_spec: {type: cortex_search, name: ComplianceSearch}
tool_resources:
  FraudOpsAnalyst:
    semantic_view: FINTECH_COPILOT.MARTS.SV_FRAUD_OPS
    execution_environment: {type: warehouse, warehouse: FINTECH_COPILOT_WH}
$$;
```

<img width="1355" height="905" alt="compliance_agent" src="https://github.com/user-attachments/assets/337eadb9-1c48-4687-a51d-d028a0aa7f52" />


> 📸 **<img width="1745" height="603" alt="agent_eval" src="https://github.com/user-attachments/assets/f18133f1-dbcb-4ac5-ae17-3a0877485849" />**

---

### Key Evaluation Insight: Answer Correctness Masking a Routing Weakness

| Metric | Score | Operational Meaning |
| :--- | :---: | :--- |
| **Answer Correctness** | **0.97** | Final response accuracy against ground truth |
| **Logical Consistency** | **0.97** | Reasoning coherence across multi-step plans |
| **Tool Execution Accuracy** | **0.93** | Query syntax & execution accuracy once chosen |
| **Tool Selection Accuracy** | **0.65** | Correct tool selection (Analyst vs. Search) |

### Key Finding: Answer Correctness Can Mask a Routing Weakness
 
Reading all four metrics together — rather than any single score in isolation — reveals a pattern that a headline "97% accurate" number would completely hide:
 
- **Execution is excellent once a tool is picked** (0.93) — the agent writes valid SQL and retrieves the right document chunks almost every time.
- **Selecting the correct tool in the first place is the weak point** (0.65) — roughly 1 in 3 questions saw the agent reach for the wrong tool, or an unintended combination.
- **The answer still comes out right most of the time anyway** (0.97) — because the underlying model is capable enough to often produce a correct-sounding response even when it was routed imperfectly.

**In plain terms:** if you only measured "did the AI give the right answer," this system would look nearly perfect. Digging one layer deeper showed it was sometimes *getting lucky* — reaching a correct answer despite querying the wrong system, not because it queried the right one. In a compliance context, that distinction matters: a routing mistake that happens to produce a plausible answer today isn't guaranteed to do so on a harder question tomorrow.

**What could improve this, in simple terms — worth exploring later:** 

* **Expand Agent Sample Questions:** Add more question-to-tool example pairings (`sample_questions`) directly in the agent's configuration. This directly trains the agent on tool *selection*—the primary weak spot—rather than SQL generation.
* **Perform Error-by-Error Question Analysis:** Inspect the specific evaluation questions the agent got wrong one by one, rather than guessing at prompt fixes. *(Note: Adding Verified Queries to the semantic view improves SQL syntax accuracy once Analyst is chosen, but does not fix the initial routing decision).*
 
---
 
## Phase 7 — Streamlit Application
 
Delivered five fully operational application pages, deployed through native Snowflake Git integration — code changes propagate via `git push`, with no manual file transfer.
 
```sql
-- The Chat page invokes the Agent via DATA_AGENT_RUN. Note: the Cortex
-- Agents REST API is unavailable from Streamlit's warehouse runtime — a
-- real, documented platform constraint discovered during implementation.
SELECT SNOWFLAKE.CORTEX.DATA_AGENT_RUN(
    'FINTECH_COPILOT.AI.COMPLIANCE_COPILOT_AGENT',
    '{"messages": [{"role":"user","content":[{"type":"text","text":"..."}]}], "thread_id": ..., "parent_message_id": ...}',
    TRUE
);
 
-- Native Git-based deployment
CREATE GIT REPOSITORY COMPLIANCE_COPILOT_REPO
  API_INTEGRATION = GITHUB_API_INTEGRATION
  ORIGIN = 'https://github.com/<user>/fintech-compliance-copilot.git';
 
CREATE STREAMLIT COMPLIANCE_COPILOT_APP
  ROOT_LOCATION = '@COMPLIANCE_COPILOT_REPO/branches/main/streamlit_app'
  MAIN_FILE = 'Home.py';
```
 
> 📸 **Customer 360 page — structured data and the AI-generated interaction summary unified in a single view**
> 
> <img width="1838" height="880" alt="agent_streamlit" src="https://github.com/user-attachments/assets/17e657df-3639-4ad8-a8b2-d6cbcbdb9658" />

**Compliance Copilot Chat**
<img width="1847" height="800" alt="chat" src="https://github.com/user-attachments/assets/46acb22d-b9bf-4ed5-a04d-3c76242d84fc" />

**Document Upload**
<img width="1772" height="826" alt="doc_upload1" src="https://github.com/user-attachments/assets/2527e386-fcd7-46c0-9656-0493fcb72f0c" />

**Document Upload Response**
<img width="1750" height="656" alt="doc_upload2" src="https://github.com/user-attachments/assets/c64d11f3-85c2-4e3d-8b1b-73c92735099a" />

**Customer 360 - Compliance Agents Can enter User name on the Agent to view Overall Customer 360 Information**
<img width="1778" height="771" alt="customer360_1" src="https://github.com/user-attachments/assets/458e2ab0-ade5-4ab0-817d-ab796125b3f6" />

<img width="1738" height="881" alt="customer360_2" src="https://github.com/user-attachments/assets/56396e3f-d43c-4b81-9eee-777f0a13dab4" />

**Cost Dashboard**
<img width="1772" height="865" alt="cost_dashboard" src="https://github.com/user-attachments/assets/4fb8354d-64e5-4999-9f36-f98fe042c786" />

---

## Business Impact & Value Delivered

This architecture directly solves the core problem introduced at the outset: **unifying disconnected transactional data and unstructured compliance documents into a single, trusted system.** 

By bridging these two siloes, the project delivers four high-value outcomes:

* **Eliminates Manual Cross-Referencing**
  * **The Impact:** Investigators no longer need to switch between separate databases and PDF viewers to resolve complex fraud or dispute cases.
  * **How It Works:** A single natural-language query dynamically queries transaction histories, chargeback disputes, model risk scores, and regulatory policy documents simultaneously.

* **Converts Document Processing into a Zero-Touch Pipeline**
  * **The Impact:** Converts slow, manual KYC document reviews into an automated, real-time data flow.
  * **How It Works:** Uploaded PDFs and images are automatically parsed, field-extracted, PII-redacted, and indexed into Cortex Search within minutes. An automated human-in-the-loop exception queue surfaces edge cases for review instead of letting errors pass silently.

* **Enforces Security & RBAC at the Data Layer**
  * **The Impact:** Prevents accidental data exposure or privilege escalation at the engine level rather than relying on brittle UI code.
  * **How It Works:** Security permissions are baked directly into the Cortex Search index (`allowed_roles` attribute filters) and Cortex Analyst semantic layer grants. A support agent and a compliance investigator asking the **exact same question** automatically receive differently scoped, role-appropriate answers.

* **Replaces AI Speculation with Measurable Cost & Quality Controls**
  * **The Impact:** Turns Cortex AI token usage and response reliability into visible, controllable operational metrics.
  * **How It Works:** Built-in evaluation frameworks (GPA benchmark suite) measure tool routing and answer correctness before production rollout. Real-time `ACCOUNT_USAGE` cost dashboards track daily AI credit spend alongside automated resource monitors.

---

### Key Takeaway

In practical terms, an investigator can ask a single question—spanning a customer's payment history, dispute records, and specific KYC policy rules—and receive an accurate, correctly cited response in **seconds**. 

By combining **automated pipelines**, **data-layer governance**, and **rigorous quality benchmarking**, this system moves beyond a proof-of-concept into a production-ready enterprise solution built for trust and operational scale.
 
---


