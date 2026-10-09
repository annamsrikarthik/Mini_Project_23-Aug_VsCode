# Lead Intelligence System

## End-to-end architecture

**Design date:** October 1, 2026  
**Primary stack:** Python + OpenAI API; PostgreSQL and Salesforce added later.  
**Scope:** Assignment first, FDE portfolio extensions second.

> Python owns qualification rules. OpenAI supports language and contextual tasks.
> The system produces outreach drafts; automatic email sending is not included.

---

## 1. Assignment architecture

**Built:** CSV intake, validation, scoring, decisions, JSON reports.  
**Planned:** Priority queue, batched outreach, output checks, richer reporting, 100-lead demonstration.

```mermaid
flowchart TD
    A["CSV input — built"] --> B["Python validation — built"]
    B -->|Invalid scoring fields| R["Human-review records — built"]
    B -->|Valid scoring fields| C["Python rubric scoring — built"]
    C -->|5–7| R
    C -->|1–4| X["Rejected records — built"]
    C -->|8–10| Q["Qualified records — built"]
    Q --> P["Priority ranking — planned"]
    P --> G["OpenAI outreach batches — planned"]
    K["Approved product facts and tone — planned"] --> G
    G --> V["Draft validation — planned"]
    V -->|Valid draft| O["Report assembly"]
    V -->|Failed after bounded retries| F["Draft failure recorded"]
    F --> O
    R --> O
    X --> O
    O --> S["Sales team: outreach queue and review list"]
```

Existing JSON reports contain scores and reasons. The final report assembly adds
ranked queues, drafts, aggregate statistics, and failure summaries.

### Qualification and ranking

- Score = 1 + company size (0 or 4) + source (0–3) + recency (0–2).
- Target company size: 20–500, inclusive; this is a campaign assumption.
- 8–10 qualified; 5–7 human review; 1–4 rejected for this campaign.
- Missing or invalid scoring information: review with a null score.
- Missing name, company, or industry: warning; do not invent details in drafts.
- Qualified leads rank by score descending, interaction date descending, then CSV order.
- Sample evaluation date: 2024-01-20, configurable through --as-of.

See project_approach.md for the complete points table.

### OpenAI request boundary

Send multiple qualified leads in each request, with stable lead identifiers, approved
product facts, tone instructions, and an explicit output schema. Match each response
to its input identifier. Validate completeness, duplicate identifiers, unsupported
claims, and missing-field handling.

Use a draft status separate from the qualification decision. An API timeout must
not turn a qualified lead into a rejected lead.

Start with a configured batch size such as five leads and adjust based on measured
request size and latency. This is application-level batching; it does not require
OpenAI's separate asynchronous Batch API.

---

## 2. Portfolio architecture

Everything in this view beyond the existing Python core is planned.

```mermaid
flowchart TD
    CSV["CSV / legacy extracts"] --> AD["Input adapters"]
    SF["Salesforce test environment"] --> AD
    SC["Scanned enquiries"] --> VI["OpenAI image extraction"]
    VI --> AD
    RP["RPA: source without an API"] --> AD
    AD --> API["Authenticated Python API"]
    API --> DB[("PostgreSQL: leads and runs")]
    API --> EV["Durable jobs / events"]
    EV --> WK["Python worker: validate, score, rank"]
    WK --> DB
    WK -->|Qualified| AI["Outreach workflow"]
    DOC["Approved product documents"] --> VS["OpenAI vector store / File Search"]
    VS --> AI
    AI --> OA["OpenAI Responses API"]
    OA --> CK["Validate drafts"]
    CK --> DB
    WK -->|Review required| HU["Sales review interface"]
    HU -->|Corrections or audited override| API
    DB --> REPORT["Reports and draft review"]
    REPORT --> SYNC["Controlled CRM synchronization"]
    SYNC --> SF
    DB --> CDC["Change capture — later lab"]
    CDC --> WH["Warehouse and SQL analytics"]
```

The outreach workflow starts as ordinary Python. The later Agents SDK exercise
coordinates retrieval, drafting, and checks through constrained tools. It reuses
the same scoring functions rather than implementing a second set of rules.

CRM synchronization updates designated output fields only. Prevent feedback loops
by distinguishing source changes from our own writebacks.

---

## 3. Components and responsibilities

| Component | Technology / choice | Responsibility |
| :--- | :--- | :--- |
| Entry point | Python CLI; built | Run the assignment locally |
| Rules | Python; built | Validate, score, explain |
| API layer | FastAPI proposed | Accept runs and expose results |
| Contract validation | Pydantic proposed | Validate API and model payloads |
| AI client | OpenAI Python SDK; planned | Request and validate draft batches |
| Retrieval | OpenAI File Search; extension | Retrieve approved product context |
| Orchestration | OpenAI Agents SDK; extension | Coordinate tools and checks |
| Operational storage | PostgreSQL; extension | Persist records, results, and audit history |
| CRM adapter | Salesforce REST API; extension | Read leads and synchronize approved fields |
| Events | Durable queue; provider undecided | Retry and decouple long-running work |
| iPaaS | Select when implementing | Manage an enterprise integration exercise |
| Legacy automation | One RPA platform; undecided | Collect data when no suitable API exists |
| Packaging | Docker proposed | Package the application consistently |
| Cloud | Provider undecided | Host API, workers, storage, and monitoring |

FastAPI, Pydantic, and Docker are proposed implementation choices, not installed or
completed components. No cloud resources are provisioned by this document.

---

## 4. Data model and interfaces

### Consistent lead record

Map every input into the same fields:

- Identity: lead_id, source_system, source_record_id.
- Original data: name, company, company_size, industry, source, last_interaction_date.
- Provenance: ingestion time, input row or document reference, schema version.

Do not use the person's name as a unique identifier. CSV rows need a run-scoped ID;
CRM records use their source-system identity. Retain the original input for audit.

### Proposed PostgreSQL tables

| Table | Main contents |
| :--- | :--- |
| leads | Canonical identity and current attributes |
| runs | Evaluation date, rubric version, status, timestamps |
| assessments | Run ID, lead ID, input snapshot, score, breakdown, decision, rank |
| outreach_drafts | Assessment ID, text, model/prompt version, references, draft status |
| review_actions | Reviewer, reason, correction or override, timestamp |
| processing_events | Attempts, errors, event IDs, correlation IDs |

Keep historical assessments immutable. Corrections create a new assessment or an
explicitly recorded human override. Never silently rewrite past decisions.

### Proposed API boundaries

- POST /runs: submit a batch or input reference; return a run identifier.
- GET /runs/{run_id}: processing status and counts.
- GET /runs/{run_id}/report: decisions, queues, reasons, and drafts.
- POST /leads/{lead_id}/reviews: authorized correction or override.

These are proposed interfaces. The assignment continues to work through the CLI.

---

## 5. Human review and failure recovery

### Human review

The assignment exports a review list. The portfolio version adds a review interface.
A reviewer can correct missing data or record a justified override. Valid corrected
data is evaluated again using the same versioned rules.

### Failure behavior

| Failure | Expected behavior |
| :--- | :--- |
| Missing CSV headers | Stop clearly before processing |
| Invalid lead fields | Preserve the record; route to review |
| API timeout or rate limit | Bounded retry with backoff; record unresolved failures |
| Missing, duplicate, or invalid model result | Reject the affected draft; retry or flag |
| Model refusal or incomplete response | Record draft status and continue other leads |
| Duplicate incoming event | Use idempotency tracking; avoid duplicate effects |
| Worker interruption | Resume persisted work without repeating completed side effects |
| Repeated event failure | Move to a failed-work queue for investigation |

Persist qualification results independently of drafting. Report whether a run
completed fully or with errors; do not hide failed drafts in success counts.

---

## 6. Deployment and operations

```mermaid
flowchart LR
    DEV["Developer: Git and tests"] --> BUILD["Build container"]
    BUILD --> HOST["Cloud: API and worker"]
    SEC["Secrets and service identities"] --> HOST
    HOST --> DB[("Managed PostgreSQL")]
    HOST --> QUEUE["Durable queue"]
    HOST --> OBJ["Input and report storage"]
    HOST --> EXT["OpenAI and Salesforce APIs"]
    HOST --> MON["Logs, metrics, alerts"]
```

Choose the hosting provider after confirming account access and project needs.
SQL credentials and API keys remain server-side. Restrict review and CRM-write
permissions. Treat lead text and retrieved documents as data, not instructions.

Record run IDs, rubric/prompt/model versions, latency, token usage, estimated cost,
error counts, review backlog, and draft-quality results. Avoid placing unnecessary
personal data or secrets in logs. Define retention for uploaded documents and runs.

Use regression checks before prompt or rubric changes, and retain a rollback path.
CDC and warehouse reporting are later learning extensions, not prerequisites for
processing 100 leads.

---

## 7. Build order and acceptance checks

1. **Existing core:** Preserve verified validation and scoring behavior.
2. **Priority/report:** Verify deterministic ordering and counts across all outcomes.
3. **OpenAI drafts:** Batch requests; ensure every draft maps to one qualified lead.
4. **Assignment evaluation:** Process 100+ records; exercise failures; finish README.
5. **SQL and API:** Persist runs and expose authenticated interfaces.
6. **Salesforce:** Test round-trip mapping and duplicate/loop prevention.
7. **RAG:** Check retrieval relevance and whether claims match supplied evidence.
8. **Agents:** Add tool orchestration without changing qualification authority.
9. **Multimodal:** Test extraction errors and validation of extracted fields.
10. **Cloud:** Deploy with secrets, access control, logs, and reproducible setup.
11. **Events/iPaaS/RPA:** Demonstrate reliable integration and a legacy workflow.
12. **CDC/analytics/operations:** Show traceable updates, monitoring, UAT, and handover.

**Known baseline:** 29 training leads and 20 testing leads. Testing decisions are
5 qualified, 11 review, and 4 rejected. Only 49 sample records currently exist.

---

## 8. JD coverage and limits

**JD_1:** Demonstrates Python, SQL, LLMs, RAG, agents, APIs, canonical data models,
automation, events, cloud, and operational practices. Use a later insurance intake
exercise for domain learning. A simulated legacy extract does not establish live
mainframe experience, and this portfolio does not substitute for years of delivery.

**JD_2:** Demonstrates transferable prototyping, multimodal, prompt, integration,
and evaluation skills. Gemini, Vertex AI, Google ADK, and Gemini Enterprise remain
separate hands-on gaps; OpenAI tools do not count as experience in those products.
Certifications remain separate milestones.

## References

- [Project approach](project_approach.md)
- [Training log](FDE_Training_Log.md)
- [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [OpenAI File Search](https://developers.openai.com/api/docs/guides/tools-file-search)
- [OpenAI Agents SDK](https://developers.openai.com/api/docs/guides/agents/sdk)
