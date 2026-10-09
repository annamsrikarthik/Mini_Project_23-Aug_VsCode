# Generate your first email drafts

The qualification rules still run in Python. Add `--draft-outreach` to generate
unsent drafts for qualified leads with the OpenAI Responses API.

## 1. Setup

In VS Code's terminal, from this project folder:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

If `.venv` does not exist, create it first with `python -m venv .venv`.
Use an OpenAI API key with model access and available API quota. Do not paste the
key into this chat, Python source, or the report. API billing/access is separate
from this code's setup; no API credit availability is assumed.

## 2. Generate drafts

```powershell
.\run_outreach.ps1
```

This helper privately prompts for the key if needed. It runs the testing CSV with
the sample evaluation date `2024-01-20` and saves `outreach_testing.json` in the
project folder. It does not persist the key. A run uses the OpenAI API and may
incur usage charges. If your terminal policy blocks scripts, use the Python command
below after configuring `OPENAI_API_KEY` in your terminal environment.

With the key already configured:

```powershell
.\.venv\Scripts\python.exe main.py leads_testing.csv --as-of 2024-01-20 --draft-outreach --output outreach_testing.json
```

Default model: `gpt-4.1-mini`. Override with `--model` (or the helper's `-Model`).
Default batch size: 5 qualified leads per request; `--batch-size` accepts 2–20.
A final remainder may contain one lead. This is not the asynchronous Batch API.

## 3. Inspect the report

- `priority_queue[].outreach`: subject, body, status, and safe error code.
- `sample_outreach_messages`: up to five successful examples.
- `outreach_summary`: model, prompt version, API attempts, drafted and failed counts.
- `run_status`: completed or completed with outreach errors.

Each generated draft has `requires_sales_review: true` and `sent: false`.
Qualification scores and decisions are retained when drafting fails. Non-qualified
leads receive no draft. Missing profile fields are omitted from the prompt.

Exit codes: 0 = completed, 1 = file/input processing failure, 2 = outreach failure
with qualification results saved, or invalid command-line arguments.
For `missing_api_key`, configure the key and rerun. For `api_http_401`, check the key;
for `api_http_403`/`api_http_404`, check model/project access. For quota/rate-limit
errors, check API quota and retry later. No raw provider errors or keys are saved.

## 4. Test without an API call

```powershell
.\.venv\Scripts\python.exe -B -m unittest -v test_outreach
```

Tests simulate responses and failures. Passing them does not verify live API access
or real draft quality. No simulated messages are used as live output samples.

## Files and limitations

- `main.py`: entry point; keeps qualification-only mode working without the SDK/key.
- `outreach.py`: batching, prompts, API requests, response validation, retries.
- `product_context.md`: discovery-only campaign guidance; no edition feature claims.
- `test_outreach.py`: offline behavior checks.

We validate IDs, structure, length, personalization, and some obvious unsupported
claims. These checks do not prove every sentence accurate; sales must review drafts.
No emails are sent. No Salesforce account connection is required at this stage.

Current user edits are preserved: missing company size receives a warning and zero
size points. This differs from the earlier rubric document's null-score policy.
The testing CSV now contains 23 records; at the sample evaluation date the current
code finds 5 qualified, 13 review, and 5 rejected.

Implementation references: [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs),
[rate limits](https://developers.openai.com/api/docs/guides/rate-limits),
[default model](https://developers.openai.com/api/docs/models/gpt-4.1-mini).

## Confirmed live-run blocker — October 5, 2026

A live diagnostic returned `credit_balance_exhausted` (HTTP 429). The organization
associated with the key has no prepaid API credits remaining. Check OpenAI API
billing and add credits if you choose to proceed. No live drafts were generated.
The code now stops retries for this and other explicit billing/usage-limit errors.
