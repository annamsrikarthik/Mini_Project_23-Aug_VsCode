# 100-lead demonstration results

**Run date:** October 6, 2026  
**Evaluation date for the historical sample:** January 20, 2024  
**Provider and model:** local Ollama, `gemma3:4b`  
**Command:** `main.py leads_100_demo.csv --as-of 2024-01-20 --draft-outreach --provider ollama --model gemma3:4b --batch-size 2 --max-attempts 3 --request-timeout 300 --output outreach_100_demo.json`

## Input and qualification

The input contains 29 existing training records, 23 existing testing records,
and 48 clearly labeled synthetic leads. The synthetic rows cover twelve
company-size, source, recency, and missing-size cases, repeated four times with
unique sample identities. The original 52 rows were copied without changing
their fields. Their source hashes and the combined-input hash are in
`demo_100_manifest.json`.

| Decision | Leads |
| --- | ---: |
| Qualified | 35 |
| Human review | 36 |
| Rejected | 29 |
| Total | 100 |

Five records need human review because their scoring data has validation issues.
The other review decisions come from scores in the review band. Missing company
size is a warning and zero size points under the current agreed rubric.

## Measured end-to-end run

The program processed all 100 rows in one CLI invocation. It made **21** local
model requests and saved **35** unsent email drafts for the 35 qualified leads.
**0** drafts failed. The measured
runtime was **2234.77 seconds** (wall clock); the CLI exit code was **0**.

The `demo_100_audit.json` check verifies that all 100 input rows match the
report, original rows are preserved, all 48 added rows have their expected
scores and decisions, qualified ranks are ordered, and qualification results
remain unchanged after drafting. It also checks each successful draft's
identifier, structure, personalization anchor, length, and selected unsupported
claims. Successful drafts are marked `sent: false` and
`requires_sales_review: true`; the full report keeps any failures beside the
affected leads. The `sample_outreach_messages` field contains up to five
examples.

## Scope and interpretation

This is a classroom scale demonstration, not a conversion experiment or a
production load test. The 48 added leads are synthetic, and the sample date is
historical. Automated text checks do not prove the messages are accurate or
ready to send. Sales must review the wording and missing details. No emails
were sent, and no paid API was called.
