"""Load a saved lead-intelligence JSON report into PostgreSQL.

The loader uses PostgreSQL's PGHOST, PGPORT, PGDATABASE, PGUSER, and
PGPASSWORD environment variables. All rows for one report are written in a
single transaction: either the entire run succeeds, or no partial run remains.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

import psycopg
from psycopg import Connection
from psycopg.types.json import Jsonb


def parse_positive_integer(value: Any) -> int | None:
    """Return a positive integer, or None for missing and invalid values."""

    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def parse_iso_date(value: Any) -> date | None:
    """Return a strict ISO date, or None when the source value is invalid."""

    try:
        text = str(value).strip()
        parsed = date.fromisoformat(text)
    except (TypeError, ValueError):
        return None
    return parsed if parsed.isoformat() == text else None


def insert_processing_run(
    connection: Connection,
    report: dict[str, Any],
) -> int:
    """Create one running execution record and return its generated ID."""

    outreach = report.get("outreach_summary") or {}
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO processing_runs (
                evaluation_date,
                run_status,
                model_provider,
                model_name
            )
            VALUES (%s, 'running', %s, %s)
            RETURNING run_id
            """,
            (
                date.fromisoformat(report["evaluation_date"]),
                outreach.get("provider"),
                outreach.get("model"),
            ),
        )
        return cursor.fetchone()[0]


def insert_input_file(
    connection: Connection,
    run_id: int,
    source_file: str,
    record_count: int,
) -> int:
    """Create the input-file record and return its generated ID."""

    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO input_files (
                run_id,
                file_name,
                file_order,
                file_status,
                records_found
            )
            VALUES (%s, %s, 1, 'processing', %s)
            RETURNING input_file_id
            """,
            (run_id, Path(source_file).name, record_count),
        )
        return cursor.fetchone()[0]


def find_or_create_lead(
    connection: Connection,
    lead: dict[str, Any],
) -> int | None:
    """Return the canonical lead ID, or None when name/company is missing."""

    name = str(lead.get("name") or "").strip()
    company = str(lead.get("company") or "").strip()
    if not name or not company:
        return None

    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO leads (lead_name, company_name)
            VALUES (%s, %s)
            ON CONFLICT (normalized_name, normalized_company)
            DO UPDATE SET
                lead_name = EXCLUDED.lead_name,
                company_name = EXCLUDED.company_name
            RETURNING lead_id
            """,
            (name, company),
        )
        return cursor.fetchone()[0]


def insert_occurrence(
    connection: Connection,
    input_file_id: int,
    item: dict[str, Any],
    lead_id: int | None,
) -> int:
    """Preserve one source row and return its occurrence ID."""

    lead = item["lead"]
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO lead_occurrences (
                input_file_id,
                lead_id,
                csv_row,
                lead_name,
                company_name,
                company_size,
                industry,
                source,
                last_interaction_date,
                identity_status,
                raw_record
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            RETURNING lead_occurrence_id
            """,
            (
                input_file_id,
                lead_id,
                item["csv_row"],
                str(lead.get("name") or "").strip() or None,
                str(lead.get("company") or "").strip() or None,
                parse_positive_integer(lead.get("company_size")),
                str(lead.get("industry") or "").strip() or None,
                str(lead.get("source") or "").strip() or None,
                parse_iso_date(lead.get("last_interaction_date")),
                "matched" if lead_id is not None else "review_required",
                Jsonb(lead),
            ),
        )
        return cursor.fetchone()[0]


def insert_qualification(
    connection: Connection,
    occurrence_id: int,
    item: dict[str, Any],
) -> int:
    """Store the deterministic score, decision, explanations, and priority."""

    score = item.get("score")
    breakdown = item.get("score_breakdown") or {}
    if score is None:
        baseline = company_size = source = recency = None
    else:
        baseline = breakdown.get("baseline")
        company_size = breakdown.get("company_size")
        source = breakdown.get("source")
        recency = breakdown.get("recency")

    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO qualification_results (
                lead_occurrence_id,
                validation_status,
                score,
                decision,
                baseline_points,
                company_size_points,
                source_points,
                recency_points,
                priority_rank,
                issues,
                warnings,
                reasoning,
                rejection_reasons,
                next_action
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s
            )
            RETURNING qualification_id
            """,
            (
                occurrence_id,
                item["validation_status"],
                score,
                item["decision"],
                baseline,
                company_size,
                source,
                recency,
                item.get("priority_rank"),
                Jsonb(item.get("issues") or []),
                Jsonb(item.get("warnings") or []),
                Jsonb(item.get("reasoning") or []),
                Jsonb(item.get("rejection_reasons") or []),
                item.get("next_action"),
            ),
        )
        return cursor.fetchone()[0]


def insert_outreach_draft(
    connection: Connection,
    qualification_id: int,
    item: dict[str, Any],
    outreach_summary: dict[str, Any],
) -> bool:
    """Store a drafted or failed outreach result; return whether one was stored."""

    outreach = item.get("outreach") or {}
    status = outreach.get("status")
    if status not in {"drafted", "failed"}:
        return False

    draft = outreach.get("draft") or {}
    error = outreach.get("error")
    if isinstance(error, dict):
        error = json.dumps(error, ensure_ascii=False)

    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO outreach_drafts (
                qualification_id,
                provider,
                model_name,
                prompt_version,
                draft_status,
                subject,
                body,
                error_message,
                requires_sales_review,
                sent
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                qualification_id,
                outreach_summary.get("provider") or "unknown",
                outreach_summary.get("model") or "unknown",
                outreach_summary.get("prompt_version") or "unknown",
                status,
                draft.get("subject"),
                draft.get("body"),
                error,
                bool(outreach.get("requires_sales_review", True)),
                bool(outreach.get("sent", False)),
            ),
        )
    return True


def summarize_loaded_run(connection: Connection, run_id: int) -> dict[str, int]:
    """Return row and decision counts for the newly loaded run."""

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE q.decision = 'qualified') AS qualified,
                COUNT(*) FILTER (WHERE q.decision = 'review') AS review,
                COUNT(*) FILTER (WHERE q.decision = 'rejected') AS rejected,
                COUNT(*) FILTER (WHERE o.lead_id IS NULL) AS identity_review,
                COUNT(d.draft_id) AS drafts
            FROM input_files f
            JOIN lead_occurrences o
                ON o.input_file_id = f.input_file_id
            JOIN qualification_results q
                ON q.lead_occurrence_id = o.lead_occurrence_id
            LEFT JOIN outreach_drafts d
                ON d.qualification_id = q.qualification_id
            WHERE f.run_id = %s
            """,
            (run_id,),
        )
        row = cursor.fetchone()

    return dict(
        zip(
            ("total", "qualified", "review", "rejected", "identity_review", "drafts"),
            row,
            strict=True,
        )
    )


def load_report(
    report_path: Path,
    source_file: str,
    dry_run: bool = False,
) -> dict[str, int]:
    """Load one report atomically and return its database summary."""

    report = json.loads(report_path.read_text(encoding="utf-8"))
    records = report.get("leads")
    if not isinstance(records, list) or not records:
        raise ValueError("The report must contain a non-empty 'leads' list.")

    expected_total = report.get("summary", {}).get("total")
    if expected_total != len(records):
        raise ValueError(
            f"Report summary total {expected_total!r} does not match "
            f"{len(records)} lead records."
        )

    with psycopg.connect() as connection:
        run_id = insert_processing_run(connection, report)
        input_file_id = insert_input_file(
            connection,
            run_id,
            source_file,
            len(records),
        )
        outreach_summary = report.get("outreach_summary") or {}

        for item in records:
            lead_id = find_or_create_lead(connection, item["lead"])
            occurrence_id = insert_occurrence(
                connection,
                input_file_id,
                item,
                lead_id,
            )
            qualification_id = insert_qualification(
                connection,
                occurrence_id,
                item,
            )
            insert_outreach_draft(
                connection,
                qualification_id,
                item,
                outreach_summary,
            )

        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE input_files
                SET file_status = 'completed',
                    processed_at = CURRENT_TIMESTAMP
                WHERE input_file_id = %s
                """,
                (input_file_id,),
            )
            cursor.execute(
                """
                UPDATE processing_runs
                SET run_status = 'completed',
                    completed_at = CURRENT_TIMESTAMP
                WHERE run_id = %s
                """,
                (run_id,),
            )

        summary = summarize_loaded_run(connection, run_id)
        summary["run_id"] = run_id

        if dry_run:
            connection.rollback()
            summary["committed"] = False
        else:
            connection.commit()
            summary["committed"] = True

    return summary


def main() -> int:
    """Parse CLI arguments, load the report, and print a safe summary."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="Saved outreach JSON report")
    parser.add_argument(
        "--source-file",
        default="leads_100_demo.csv",
        help="Original CSV filename recorded in PostgreSQL",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and load inside a transaction, then roll everything back",
    )
    args = parser.parse_args()

    try:
        summary = load_report(
            args.report,
            source_file=args.source_file,
            dry_run=args.dry_run,
        )
    except (OSError, ValueError, json.JSONDecodeError, psycopg.Error) as error:
        print(f"PostgreSQL load failed: {error}", file=sys.stderr)
        return 1

    print(json.dumps(summary, indent=2))
    if args.dry_run:
        print("Dry run passed; database changes were rolled back.")
    else:
        print("PostgreSQL import committed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
