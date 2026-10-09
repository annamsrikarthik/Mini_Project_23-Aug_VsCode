# Generate local email drafts

Python keeps the qualification rules. Outreach now defaults to the locally installed
`gemma3:4b` model through Ollama, as requested. No API key or paid API calls are
needed for this path. The verified local run produced 5 drafts in 3 calls with
zero failures using prompt `discovery-v4`. Drafts still require sales review and
editing before use; one missing-company greeting needs attention.

## 1. Start Ollama

Ollama and `gemma3:4b` are already installed on this computer. Open the Ollama app
and leave it running. From the project folder in PowerShell, confirm the model:

```powershell
ollama list
```

The local Python integration uses only the standard library; no `pip` packages
are required. If the project environment is missing, create it with
`python -m venv .venv`.

## 2. Generate drafts

```powershell
.\run_outreach.ps1
```

The helper reads `leads_testing.csv`, uses the sample evaluation date `2024-01-20`,
and saves `outreach_testing.json`. If PowerShell blocks scripts, run Python directly:

```powershell
.\.venv\Scripts\python.exe main.py leads_testing.csv --as-of 2024-01-20 --draft-outreach --output outreach_testing.json
```

Defaults: provider `ollama`, model `gemma3:4b`, batch size 2 qualified leads, and
request timeout 180 seconds. Override with `--model`, `--batch-size` (2–20), and
`--request-timeout` (seconds); helper equivalents are `-Model`, `-BatchSize`, and
`-RequestTimeout`. A final batch may contain one lead. Local generation can take
time, especially while the model first loads.

There is no automatic switch to a cloud provider when local generation fails.
The previous OpenAI route is optional and requires explicit `--provider openai`
(or `-Provider openai`), the optional `openai` package, an API key, and available
paid API quota. See `requirements.txt` for the optional installation command.

## 3. Review the report

- `priority_queue[].outreach`: subject, body, status, and safe error code.
- `sample_outreach_messages`: up to five successful examples.
- `outreach_summary`: provider/model, prompt version, attempts, and draft/failure counts.
- `run_status`: completed or completed with outreach errors.

Drafts remain unsent (`sent: false`) and require sales review
(`requires_sales_review: true`). Review factual claims, personalization, and tone
before using them. Automatic checks do not prove every sentence accurate.
Non-qualified leads receive no draft. Qualification scores and decisions remain
in the report even when drafting fails.

The current testing CSV contains 23 leads: 5 qualified, 13 review, and 5 rejected
at `2024-01-20`. The user's missing-company-size rule remains a warning plus zero
size points; older rubric notes describing a null score are historical.

## 4. Resolve a local failure

| Error | Action |
| --- | --- |
| `ollama_unavailable` | Start the Ollama app, then rerun. |
| `ollama_model_not_found` | Check `ollama list`; use an installed model via `--model`. |
| `ollama_timeout` | Increase `--request-timeout`, then rerun. |
| Draft validation failure | Review the failure code and supplied context, then rerun; do not use a rejected draft. |

Exit codes: 0 = completed; 1 = file/input processing failure; 2 = outreach failure
with qualification results saved, or invalid command-line arguments. Raw provider
errors and API keys are not saved in the report.

Offline checks simulate provider responses and do not verify live draft quality:

```powershell
.\.venv\Scripts\python.exe -B -m unittest -v test_outreach
```

Implementation references: [Ollama local API](https://docs.ollama.com/api/introduction)
and [structured outputs](https://docs.ollama.com/capabilities/structured-outputs).

## Historical OpenAI blocker — October 5, 2026

The earlier live OpenAI diagnostic returned `credit_balance_exhausted` (HTTP 429),
and no live OpenAI drafts were generated. The current local Gemma workflow does
not require resolving that billing issue.
