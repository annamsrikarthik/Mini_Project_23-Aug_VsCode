# Lead Intelligence System — mini project

This command-line tool reads inbound leads from CSV, scores them with a documented
1–10 rubric, and routes each lead to **qualified**, **human review**, or
**rejected**. Qualified leads are ranked and receive an unsent first-email draft
from the locally installed `gemma3:4b` model through Ollama. Python owns the
qualification decisions; sales reviews the drafts before any message is sent.

## Run the 100-lead demonstration

Prerequisites: Python 3.14 or compatible, Ollama running locally, and the
`gemma3:4b` model installed. The local path uses Python's standard library and
does not require an API key or paid API calls.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe build_demo_100.py
.\.venv\Scripts\python.exe main.py leads_100_demo.csv --as-of 2024-01-20 --output qualification_100_demo.json
.\.venv\Scripts\python.exe main.py leads_100_demo.csv --as-of 2024-01-20 --draft-outreach --provider ollama --model gemma3:4b --batch-size 2 --request-timeout 300 --output outreach_100_demo.json
.\.venv\Scripts\python.exe audit_demo_100.py
```

The demonstration CSV has **100 rows**: 29 original training rows, 23 original
testing rows, and 48 labeled synthetic rows covering twelve boundary cases.
The `--as-of` date makes the historical sample reproducible. The audit checks
source-row preservation, known case decisions, priority order, and draft status.

## Measured result

At the sample date, the run classified **35 qualified, 36 review, and 29
rejected** leads. Gemma drafted **35** of 35 qualified leads in **21** local
requests; **0** failed. Total measured runtime was
**2234.77 seconds**. See [demo_100_results.md](demo_100_results.md) for the audit
and limits, [outreach_100_demo.json](outreach_100_demo.json) for every decision,
and its `sample_outreach_messages` for up to five example drafts.

The score uses company size, lead source, and interaction recency, plus one
baseline point. Missing or invalid scoring data is handled explicitly; a
missing company size receives zero size points and a warning. Draft checks
catch structural errors and selected unsupported claims, but a person must
review wording and facts. No emails are sent.

## Human-reviewed samples

Five edited outreach examples are available in reviewed_sample_drafts.md. One controlled delivery test reached Gmail Spam; no bulk campaign was sent. Production delivery requires separate sender-authentication and reputation checks.

## Save a run to PostgreSQL

The optional PostgreSQL path uses the standard `PGHOST`, `PGPORT`,
`PGDATABASE`, `PGUSER`, and `PGPASSWORD` environment variables. Verify the
connection and seven-table schema first:

```powershell
.\.venv\Scripts\python.exe database_check.py
```

Test the complete Python-to-PostgreSQL flow without retaining any rows:

```powershell
.\.venv\Scripts\python.exe main.py leads_testing.csv `
    --as-of 2024-01-20 `
    --output qualification_testing.json `
    --save-postgres `
    --postgres-dry-run
```

After verifying the dry-run summary, omit `--postgres-dry-run` to commit one
new processing run:

```powershell
.\.venv\Scripts\python.exe main.py leads_testing.csv `
    --as-of 2024-01-20 `
    --output qualification_testing.json `
    --save-postgres
```

Each committed command execution intentionally creates a new row in
`processing_runs` and preserves every input occurrence. A failed database save
does not remove the JSON report. PostgreSQL failures return exit code 3;
incomplete outreach drafting returns exit code 2. The reviewed read-only SQL
reports are in [analytics_queries.sql](analytics_queries.sql).
