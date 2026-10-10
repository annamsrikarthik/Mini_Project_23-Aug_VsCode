# My FDE Training Log

> **Current direction — October 11, 2026:** The original assignment is complete:
> the audited 100-lead run produced 35 qualified drafts, 36 human-review decisions,
> and 29 rejections with no drafting failures. The project is now in the first
> portfolio extension: PostgreSQL storage and SQL analytics. The local
> MiniProject_FDE database has seven related tables, business constraints, and
> operational indexes. Python-to-PostgreSQL connectivity is verified. A
> transactional JSON importer is implemented; its 100-lead dry run is the next
> verification step. Salesforce integration follows the database increment.

**Project started:** 2026-09-29
**Last updated:** 2026-10-11
**Python experience:** Comfortable writing small programs.
**Learning approach:** Guided project work, with explanations and small checks of understanding.

Keep this file and share its current contents in a new conversation so we can resume accurately.

## Current problem

Build the Mini Project Brief's Lead Intelligence System. The scenario describes approximately 1,200 inbound leads per month, with only approximately 60 qualified and contacted. Manual decisions take 8–12 minutes per lead.

The user selected Salesforce Trial Edition. Working interpretation: Salesforce CRM is the product prospective leads are interested in. Whether the user also wants to use a trial account as a connected platform remains to be clarified. No Salesforce integration is required by the brief.

## Project progress

- [x] Read and discuss the brief.
- [x] Discuss outreach, qualification rubrics, success criteria, and on-brand messaging.
- [x] Establish Python experience and create this log.
- [x] Define the assumed customer profile and product context.
- [x] Design 3–5 qualification factors and explicit scoring/decision rules.
- [x] Manually evaluate sample leads to check the rubric.
- [x] Implement CSV loading and validation.
- [x] Implement the local Ollama/Gemma API integration with batch processing.
- [x] Verify a live local run: 5 drafts, 3 calls, zero failures.
- [ ] Complete user/sales review and edit personalized drafts before use.
- [x] Produce decisions, reasons, priority ranks, and aggregate statistics.
- [x] Implement missing-data handling, safe API failures, and bounded retries.
- [x] Demonstrate 100 leads processed in one CLI run without manual intervention.
- [x] Prepare source code, sample data, output report, and a one-page README.
- [x] Design and create the seven-table PostgreSQL schema.
- [x] Add database constraints and operational indexes.
- [x] Verify Python connectivity to PostgreSQL with all seven tables present.
- [x] Implement the transactional PostgreSQL JSON importer.
- [ ] Run and verify the 100-lead PostgreSQL dry run.
- [ ] Commit the verified 100-lead database import.
- [ ] Build and validate SQL analytics queries.

## Constraints and evidence

- Required interface: command-line tool.
- Required fit score: 1–10.
- Required decisions: qualified, rejected, or review.
- Generate first-message drafts; automatic sending and follow-up scheduling are not required by the building section.
- Current original CSV counts: 29 training leads and 23 testing leads (52 total). The scale dataset adds 48 labeled synthetic rows. At `2024-01-20`, the 100-lead decisions are 35 qualified, 36 review, and 29 rejected.
- Missing company size produces a warning and zero size points; invalid size or missing/invalid source or date still requires review with a null score.
- Qualification criteria will be classroom assumptions, not Salesforce's official sales policy.

## Next learning step

Run postgres_store.py with --dry-run against outreach_100_demo.json. Verify
100 total occurrences, 35 qualified, 36 review, 29 rejected, two identity-review
occurrences, and 35 drafts while confirming that all changes are rolled back.
After that, commit the real import and build the SQL analytics queries.

## Historical learning checkpoint — initial validation

- Proposed campaign target: 20–500 employees; this is a classroom assumption.
- Proposed score: 1 baseline + company size (0 or 4) + source (0–3) + recency (0–2).
- Proposed thresholds: 8–10 qualified, 5–7 review, 1–4 rejected for this campaign.
- Sample evaluation date: 2024-01-20; CLI exposes --as-of to keep it configurable.
- Learner correctly prioritized Alice for target company size and demo interest.
- Learner correctly routed missing company size to human review. Clarified that missing evidence differs from a confirmed poor fit.
- main.py now loads CSV and validates size, mapped source, and date. Missing name/company/industry produces warnings separately.
- Validation results: training 29 ready, 0 review; testing 15 ready, 5 review, 2 records with warnings.
- Validation status ready_for_scoring is not a qualification decision. Scoring, LLM integration, and outreach drafting are still pending.

## Curriculum progress

Formal curriculum exercises have not been assessed. Project milestones above track practical work separately.

- [ ] Hurdle 1 — Extraordinary Problem
- [ ] Hurdle 2 — Eval
- [ ] Hurdle 3 — Generative Four
- [ ] Hurdle 4 — Sustaining Three

## Notes per hurdle

### Hurdle 1
- Running example: lead qualification and outreach drafting.
- Business context and target customer profile: pending.

### Hurdle 2
- Expected decisions and evaluation cases: pending.

### Hurdle 3
- Retrieval, context, memory, and feedback decisions: pending.

### Hurdle 4
- Plan for missing fields, failed API calls, rate limits, and human review.

## Scoring implementation checkpoint

- Implemented the three-factor rubric in main.py using score_lead and qualify_records.
- Score = 1 + size (0/4) + source (0–3) + recency (0–2).
- Qualified: 8–10; review: 5–7; rejected for this campaign: 1–4.
- Invalid scoring records get review and a null score, with validation reasons preserved.
- Tested Alice (10, qualified), Bob (3, rejected), webinar example (7, review), size/date boundaries, all scores 1–10, and incomplete-data review.
- Added qualification_training.json and qualification_testing.json using evaluation date 2024-01-20.
- Learner requested the rubric again after misclassifying the 100-employee example; reinforce that 100 lies within 20–500.
- Next: explain score_lead, then add outreach priority and plan the required batched LLM integration. No LLM or message generation is implemented yet.

## 2026-10-02 — Priority queue and richer summaries completed

- Added build_report in main.py; original lead order, scores, and reasons are retained.
- Added priority_queue, human_review, rejected_leads, per-lead priority_rank, and next_action.
- Ranking: score descending, date descending, CSV row ascending. Non-qualified ranks are null.
- Added qualified percentage, review reasons split by data vs score, and counted rejection factors.
- Rejection factors may overlap; the combined score, not one factor alone, determines rejection.
- Regenerated both qualification reports at evaluation date 2024-01-20.
- Training: 29 total, 14 qualified (48.28%), 7 review, 8 rejected.
- Testing: 20 total, 5 qualified (25%), 11 review (6 score, 5 data), 4 rejected.
- Verified exact testing queue, tie-breaks, unchanged decisions and source records, counts, rank isolation, and empty/single-decision inputs.
- Next: approved product context and batched OpenAI outreach integration. No email drafts or API calls yet.

## 2026-10-03 — OpenAI outreach integration

- Added optional --draft-outreach mode to main.py and separate outreach.py module.
- Discovery-only prompt uses known lead details; no unverified edition features.
- Qualified leads are sent in batches; drafts match by CSV row identifier.
- Preserved existing local scoring changes, including missing size = warning + zero points.
- Testing data now contains 23 user-maintained rows: 5 qualified, 13 review, 5 rejected at 2024-01-20.
- Added safe failure statuses, bounded retries, response validation, and offline tests.
- Existing business functions and qualification decisions are unchanged by the outreach integration.
- Added product_context.md, requirements.txt, run_outreach.ps1, and OUTREACH_SETUP.md.
- Live draft generation remains pending: OPENAI_API_KEY was not available in the agent environment.
- Next: privately configure an API key, run the first five qualified testing leads, and review actual output quality.

## 2026-10-05 — Local Gemma outreach verified

- User chose locally installed Ollama with `gemma3:4b`; local drafting needs no API key or paid API calls, and has no automatic cloud fallback.
- Live run with prompt `discovery-v4`: 5 drafts, 3 local calls, zero failures.
- Qualification remained unchanged: 23 testing leads, 5 qualified, 13 review, 5 rejected at `2024-01-20`.
- Controlled writing intent distinguishes a demo-request acknowledgement from neutral outreach, preventing raw source labels from suggesting prior conversations.
- Added exact company-name validation and targeted retry feedback when required personalization is missing.
- All five drafts were inspected for unsupported prior contact, sender employment claims, and promises. They remain unsent and require sales review; the missing-company lead has an awkward “from Consulting” greeting using its industry and needs editing.
- Offline suite: 20 tests, 18 passed and 2 optional OpenAI SDK tests skipped in the current environment; project-environment verification follows separately.
- Next: user/sales review and editing, then the 100-lead demonstration. RAG, agents, and cloud portfolio work remain separate planning steps.


## 2026-10-06 — Guided editorial review prepared

- Reviewed all five saved Gemma drafts against original lead fields and product_context.md.
- Prepared outreach_review.md with the original text, suggested replacements, and reasons for each edit.
- Corrected the industry/company confusion for Test_MissingName; its company is missing, while its name field is present.
- Restored the omitted demo-request acknowledgement for Test_SMBAverage and polished the other greetings and invitations.
- The five suggested replacements pass the existing draft validator. Original generated drafts and all qualification decisions remain available in outreach_testing.json.
- Verification clarification: after installation on October 5, all 20 offline tests passed in the project's .venv; the earlier 18-pass/2-skip result was from staging.
- Learner review is in progress. No user/sales approval has been recorded and no emails have been sent.
- Next: discuss the suggested edits, then prepare the 100-lead demonstration.

## 2026-10-06 — 100-lead demonstration verified

- Combined 29 original training and 23 original testing rows unchanged with 48 clearly labeled synthetic leads. Twelve rubric cases, repeated four times, cover size and recency boundaries and missing company size.
- Ran the existing CLI once for qualification and local Gemma drafting at the historical evaluation date `2024-01-20`.
- Result: 100 processed; 35 qualified, 36 human review, and 29 rejected. Gemma generated all 35 drafts in 21 local calls with zero failures and exit code 0.
- Measured elapsed time: 2,234.77 seconds (about 37 minutes 15 seconds) on this computer. This is a classroom scale test, not a production performance claim.
- The audit verified original input rows, all 48 added expected scores and decisions, ranking, preserved qualification results after drafting, and draft status and structural checks.
- Prepared the one-page README, complete JSON output, manifest, audit, and five source-diverse sample drafts in a submission folder. No emails were sent or approved for sending.
- Next: user/sales review of generated wording, then decide whether to extend the assignment into the portfolio roadmap. Formal FDE hurdle assessments remain separate.

## 2026-10-07 — Human review and controlled delivery test

- Reviewed five representative outreach drafts and prepared corrected versions in reviewed_sample_drafts.md.
- Corrections improved greetings, preserved source-specific wording, removed awkward company/industry phrasing, and kept one clear next step.
- One Alice Chen sample was sent as a controlled delivery test to the project owner; it reached Gmail Spam.
- The test confirms that draft quality and deliverability are separate concerns. Production readiness requires sender authentication and reputation checks in addition to content review.
- No bulk campaign was sent. The remaining reviewed examples are unsent.
- Core assignment implementation and submission evidence are complete.
- Next portfolio increment: PostgreSQL data model and SQL reporting, followed by Salesforce API integration.

## 2026-10-11 — PostgreSQL schema and Python connection checkpoint

- Created local PostgreSQL 18 database MiniProject_FDE and verified the public schema.
- Designed seven tables: processing_runs, input_files, leads, lead_occurrences,
  qualification_results, outreach_drafts, and review_events.
- Extended the original one-file design so one program run can contain multiple
  input files.
- Separated canonical lead identity from file occurrences. The project rule uses
  normalized lead name plus company name as the canonical identity. Repeated
  appearances share one lead_id; every source appearance keeps its own
  lead_occurrence_id.
- Records missing lead name or company are preserved as occurrences with a null
  lead_id and identity_status = review_required; the source CSV is not changed.
- Added generated normalized name/company columns, primary and foreign keys,
  uniqueness rules, rubric point checks, score-to-decision checks, and safe
  draft/review state constraints.
- Added five operational indexes for lead history, qualification lookup, priority
  queue, draft review backlog, and review history.
- Added two partial unique indexes preventing repeated approval and sent events
  for the same draft. Multiple edit events remain allowed.
- Chose one current draft per qualification result. Draft versioning was discussed
  and intentionally excluded; edits, reviewer name, edited content, notes, and
  timestamps are retained in review_events.
- Tested a complete seven-table Alice workflow and used it to identify duplicate
  approval behavior. Removed all committed demonstration data and confirmed all
  seven tables returned to zero rows.
- Added Psycopg 3 as the PostgreSQL driver in requirements.txt.
- Added database_check.py; verified connection to MiniProject_FDE as postgres,
  PostgreSQL 18.6, public schema, and all seven required tables.
- Added postgres_store.py. It maps the saved 100-lead JSON report into the seven
  tables using one transaction, reuses canonical leads, preserves raw records,
  stores qualification decisions and outreach drafts, and supports --dry-run.
- Verified the new Python files compile successfully. Live importer verification
  remains pending.
- Expected dry-run result: 100 total, 35 qualified, 36 review, 29 rejected,
  two identity-review occurrences, 35 drafts, and committed = false.
- Portfolio plan remains six focused increments over ten days: PostgreSQL/SQL,
  FastAPI plus Salesforce, RAG, agent workflow, multimodal intake, and deployment
  with evaluation and demonstration.
