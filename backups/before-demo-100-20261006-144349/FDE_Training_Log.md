# My FDE Training Log

> **Current direction — October 5, 2026:** The user selected local Gemma
> `gemma3:4b` through Ollama for outreach, with no API key required. Local-run
> verification completed with 5 drafts; user/sales review remains. Use
> [OUTREACH_SETUP.md](OUTREACH_SETUP.md) for current commands. Earlier OpenAI next
> steps are preserved as history and superseded for this stage. RAG, agents, and
> cloud portfolio work require separate planning. Current testing data has 23
> leads (5 qualified, 13 review, 5 rejected at `2024-01-20`); missing company size
> retains the user's warning plus zero-points behavior.

**Project started:** 2026-09-29
**Last updated:** 2026-10-06
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
- [ ] Demonstrate at least 100 leads processed without manual intervention.
- [ ] Prepare source code, sample data, output report, and a one-page README.

## Constraints and evidence

- Required interface: command-line tool.
- Required fit score: 1–10.
- Required decisions: qualified, rejected, or review.
- Generate first-message drafts; automatic sending and follow-up scheduling are not required by the building section.
- Current CSV counts: 29 training leads and 23 testing leads (52 total). At `2024-01-20`, testing decisions are 5 qualified, 13 review, and 5 rejected. DATA_README.md incorrectly describes 30 training leads.
- Missing company size produces a warning and zero size points; invalid size or missing/invalid source or date still requires review with a null score.
- Qualification criteria will be classroom assumptions, not Salesforce's official sales policy.

## Next learning step

Review the local Gemma drafts for accuracy, personalization, and tone, then prepare
the 100-lead demonstration. The live local run is complete; drafts are not yet
approved for use.

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
