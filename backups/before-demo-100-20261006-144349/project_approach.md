# Lead Intelligence System

> **Current direction — October 5, 2026:** By user choice, this stage uses local
> Gemma `gemma3:4b` through Ollama for outreach drafts. No API key is required;
> the local run completed with 5 drafts. Sales review is still required. Follow
> [OUTREACH_SETUP.md](OUTREACH_SETUP.md) for current commands. Earlier OpenAI setup
> steps below are historical and superseded for this stage. The broader RAG,
> agent, and cloud portfolio ideas remain a roadmap requiring separate planning.

## Project approach

**Goal:** Complete the assignment, then extend it into an FDE portfolio project.

**Core stack:** Python + Ollama/Gemma; PostgreSQL and Salesforce integration later.

**Current stage:** Validation, scoring, priority ranking, richer reports, and batched local outreach are implemented. The verified local run produced 5 drafts; sales review remains.

**Next step:** Review local drafts, then complete the 100-lead demonstration.

> Build one working increment at a time: understand → implement → test → explain.

---

## Contents

1. [Scope and technology](#1-scope-and-technology)
2. [Progress so far](#2-progress-so-far)
3. [Assignment roadmap](#3-assignment-roadmap)
4. [Portfolio roadmap](#4-portfolio-roadmap)
5. [Qualification rubric](#5-qualification-rubric)
6. [Job-description alignment](#6-job-description-alignment)
7. [Learning and delivery](#7-learning-and-delivery)
8. [References](#8-references)

---

## 1. Scope and technology

### The application

Read leads from a CSV, validate their information, apply the qualification rubric,
rank qualified leads, and generate personalized first-message drafts.

Save the decisions, reasons, priorities, and drafts in a report the sales team can use.

### Technology choices

| Purpose | Technology |
| :--- | :--- |
| Validation and scoring | Python |
| Outreach generation | Ollama local API with Gemma `gemma3:4b` |
| Document retrieval / RAG | OpenAI File Search and vector stores |
| Agent workflows | OpenAI Agents SDK |
| Image-based intake | An image-capable OpenAI model |
| Storage and analytics | PostgreSQL and SQL |
| CRM integration | Salesforce APIs |
| Cloud hosting | To be selected later |

**Product context:** Salesforce CRM. Our qualification rules are classroom campaign
assumptions, not Salesforce's official sales policy. Connecting a Salesforce test
account is a later extension.

**AI integration:** ChatGPT supports learning and prompt experiments. The Python
application calls Ollama locally using Python's standard library. Retrieval, agents,
image intake, storage, CRM integration, and cloud hosting above are later extensions.

**Implementation choices:** Current local outreach requires no API key. Confirm
account access and costs separately before any optional cloud integration.
Cloud hosting, RPA, messaging, and integration platforms are separate choices.

---

## 2. Progress so far

- [x] Load lead records from CSV.
- [x] Validate scoring fields.
- [x] Calculate rubric scores and decisions.
- [x] Save score breakdowns and reasoning.
- [x] Rank qualified leads.
- [x] Implement batched local outreach through Ollama/Gemma.
- [x] Verify a live local run: 5 drafts, 3 calls, zero failures.
- [ ] Complete user/sales review and edit drafts before use.
- [ ] Complete the 100-lead demonstration and submission.

### Verified data

| Dataset | Records |
| :--- | ---: |
| Training | 29 |
| Testing | 23 |
| **Total available** | **52** |

### Testing results

| Qualified | Human review | Rejected |
| ---: | ---: | ---: |
| 5 | 13 | 5 |

The sample evaluation date is **January 20, 2024**, configurable with `--as-of`.
The existing implementation is in `main.py`.

---

## 3. Assignment roadmap

**Finish these four steps before expanding the project.**

### Step 1 · Business rules and validation

**Status: Initial implementation complete**

Apply explicit rules to validate and score leads. Continue checking that the results
match the agreed rubric.

**Deliverable:** A decision and clear explanation for each processed lead.

### Step 2 · Priorities and reports

**Status: Implemented and checked**

Rank qualified leads using this order:

1. Higher score first.
2. More recent interaction first when scores match.
3. Original CSV order when both match.

Keep a separate human-review list. Include decisions, reasoning, priority ranks,
aggregate statistics, and common rejection reasons.

**Deliverable:** An actionable report and an ordered outreach queue.

### Step 3 · Local Gemma outreach

**Status: Implemented; live local run verified; user/sales review pending**

Use Ollama's local API with `gemma3:4b` to generate personalized first-message
drafts. Default to two qualified leads per request and a 180-second timeout.

- Process multiple leads per request.
- Match responses to leads using stable identifiers.
- Use clear prompts, examples, and structured responses.
- Validate returned content and handle failures and rate limits.
- Use known lead details and a friendly, professional tone.

**Deliverable:** Draft messages saved in the report. Automatic email sending is
outside the assignment's required scope.

### Step 4 · Evaluation and submission

**Status: Planned**

Check scoring correctness, personalization, unsupported claims, malformed responses,
missing data, and API failures. Prepare enough sample data to demonstrate at least
**100 leads processed end-to-end without manual intervention**.

**Submission checklist:**

- [ ] Source code.
- [ ] Sample leads CSV.
- [ ] JSON or CSV output report.
- [ ] Three to five sample outreach messages.
- [ ] README of at most one page.
- [ ] API keys excluded from submission.

---

## 4. Portfolio roadmap

These extensions go beyond the brief's **8–10-hour assignment scope**.
Complete them in the following order.

### Step 5 · Database and SQL

Store leads, processing runs, decisions, and review outcomes in PostgreSQL.

**Evidence:** SQL queries for qualification rates and the review backlog.

### Step 6 · API and Salesforce integration

Expose the workflow through an authenticated API. Map CSV and Salesforce records
into one consistent internal lead format: the canonical data model.

**Evidence:** Lead exchange with an available Salesforce test environment.

### Step 7 · Retrieval-augmented generation

Use OpenAI File Search and vector stores to retrieve approved product facts and
customer examples before drafting.

**Evidence:** Draft claims traceable to supporting documents.

### Step 8 · Agent workflow

Use the OpenAI Agents SDK to coordinate retrieval, drafting, checks, and escalation.
Expose existing Python functions as tools and maintain explicit workflow state.

**Evidence:** A working agent workflow with inspectable tool calls.

### Step 9 · Multimodal intake

Extract lead fields from a scanned enquiry using an image-capable OpenAI model.
Validate extracted data before it enters the normal workflow.

**Evidence:** A scanned enquiry processed into a validated lead record.

### Step 10 · Cloud deployment

Deploy an authenticated prototype with reproducible setup, secrets management,
and access control. Select the cloud platform at this stage.

**Evidence:** A deployed application and documented setup.

### Step 11 · Events and enterprise integration

Process incoming lead events with retries, duplicate prevention, and an audit trail.
Choose an integration platform as a service (iPaaS) when needed.

**Evidence:** A lead event processed reliably through the workflow.

### Step 12 · RPA and legacy ingestion

Automate one process without a usable API using a suitable RPA platform:
Power Automate, UiPath, or Automation Anywhere. Ingest a simulated legacy extract.

**Evidence:** A working automation and an explanation of why RPA fits the task.

### Step 13 · Operational data and analytics

Practise operational data store (ODS) concepts, change data capture (CDC), and
warehouse reporting with traceable updates.

**Evidence:** Source changes reflected in reporting without duplicate records.

### Step 14 · LLMOps and customer handover

Monitor quality, latency, cost, and failures. Practise user acceptance testing (UAT),
release and rollback procedures, and stakeholder demonstrations.

**Evidence:** Evaluation results, an operational runbook, and a customer demo.

> Choose one suitable tool from competing alternatives. Every addition should solve
> a clear problem or demonstrate a specific learning objective.

---

## 5. Qualification rubric

**Total score = 1 baseline point + company-size points + source points + recency points.**

### Company size

| Employees | Points |
| :--- | ---: |
| 20–500, inclusive | 4 |
| Below 20 or above 500 | 0 |

### Lead source

| Source | Points |
| :--- | ---: |
| Inbound demo request | 3 |
| Referral or sales call | 2 |
| Webinar attendee or content download | 1 |
| LinkedIn outreach | 0 |

### Interaction recency

Days are measured backwards from the evaluation date.

| Days ago | Points |
| :--- | ---: |
| 0–30 | 2 |
| 31–90 | 1 |
| More than 90 | 0 |

### Decision thresholds

| Score | Decision |
| :--- | :--- |
| 8–10 | Qualified |
| 5–7 | Human review |
| 1–4 | Rejected for this campaign |

### Exceptions and interpretation

- **Missing company size:** Add a warning and assign zero company-size points.
- **Invalid size, or missing/invalid source or date:** Human review with a `null`
  score. This includes an unmapped source.
- **Missing name, company, or industry:** Add separate warnings; never invent details.
- **Large companies with recent demo interest:** Review their requirements and our
  delivery capacity. Company size alone does not automatically reject them.
- **Scoring ownership:** Keep rubric arithmetic in Python. The LLM must not silently
  change the agreed rules.

---

## 6. Job-description alignment

### JD_1 · Enterprise FDE skills

The approach develops Python, SQL, LLMs, agent workflows, RAG, integrations,
automation, cloud, and operational practices.

**Additional domain exercise:** Adapt the workflow to insurance submission intake:
completeness checks, document extraction, and routing for underwriter review.

**Remaining gap:** Project work demonstrates learning; it does not replace the years
of insurance and client-delivery experience requested by this JD.

### JD_2 · Google-focused AI prototyping

The project develops transferable skills in prototyping, prompting, agents,
multimodal applications, integrations, and technical validation.

**Additional platform exercise:** If targeting this role, port a small workflow to
Gemini, Vertex AI, and Google ADK. Explore Gemini Enterprise separately if access
is available.

**Remaining gap:** A local Gemma implementation does not demonstrate hands-on use of
those Google products. Certifications remain separate milestones.

---

## 7. Learning and delivery

For every increment:

1. State the customer's problem and expected behavior.
2. Explain the technology choice.
3. Build a small working implementation.
4. Test concrete examples and failure cases.
5. Explain results, limitations, and next actions to a stakeholder.
6. Update `FDE_Training_Log.md` at meaningful checkpoints.

**Measure:** Processing time, review workload, and draft quality.

**Report honestly:** Do not claim conversion or revenue improvements without evidence.

---

## 8. References

- [Ollama local API](https://docs.ollama.com/api/introduction)
- [Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs)
- [OpenAI API quickstart](https://developers.openai.com/api/docs/quickstart)
- [OpenAI File Search](https://developers.openai.com/api/docs/guides/tools-file-search)
- [OpenAI Agents SDK](https://developers.openai.com/api/docs/guides/agents/sdk)


