"""Read a leads CSV, validate and score its records, rank qualified leads, and save decisions and summaries as JSON.
With --draft-outreach, request OpenAI email drafts for qualified leads; no messages are sent.
"""

import argparse
import csv
from collections import Counter
import json
import os
from datetime import date
from pathlib import Path


REQUIRED_COLUMNS = {
    "name", "company", "company_size", "industry", "source",
    "last_interaction_date",
}
KNOWN_SOURCES = {
    "inbound demo request", "referral", "sales call",
    "webinar attendee", "content download", "linkedin outreach",
}
MISSING_VALUES = {"", "na", "n/a", "null", "none"}


def is_missing(value):
    """Check whether a text value is blank or a missing-value marker such as NA, ignoring spaces and letter case.
    """
    return value.strip().casefold() in MISSING_VALUES


def validate_lead(lead, evaluation_date):
    """Check company size, source, and interaction date for scoring issues.
    Return scoring issues separately from missing profile-data warnings.
    """
    issues = []
    warnings = []

    size = lead["company_size"]
    if is_missing(size):
        warnings.append("Company size is missing; score this factor as 0 points.")
    else:
        try:
            if int(size) <= 0:
                raise ValueError
        except ValueError:
            issues.append("Company size must be a positive whole number.")

    source = lead["source"]
    if is_missing(source):
        issues.append("Lead source is missing.")
    elif source.casefold() not in KNOWN_SOURCES:
        issues.append(f"Lead source is not mapped in our rubric: {source}.")

    interaction = lead["last_interaction_date"]
    if is_missing(interaction):
        issues.append("Last interaction date is missing.")
    else:
        try:
            parsed_date = date.fromisoformat(interaction)
            if parsed_date.isoformat() != interaction:
                raise ValueError
            if parsed_date > evaluation_date:
                issues.append("Last interaction date is after the evaluation date.")
        except ValueError:
            issues.append("Last interaction date must be a valid YYYY-MM-DD date.")

    # These fields do not determine the score, but matter for message drafting.
    for field in ("name", "company", "industry"):
        if is_missing(lead[field]):
            warnings.append(f"Missing {field}; do not invent it in an outreach draft.")

    return issues, warnings


def load_and_validate(input_path, evaluation_date):
    """Read the CSV, check its headers, and validate each row.
    Return lead records with their CSV row numbers, validation status, issues, and warnings.
    """
    results = []
    with input_path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, strict=True)
        headers = reader.fieldnames or []
        missing_columns = REQUIRED_COLUMNS - set(headers)
        if missing_columns:
            raise ValueError("Missing CSV columns: " + ", ".join(sorted(missing_columns)))
        if len(headers) != len(set(headers)):
            raise ValueError("CSV contains duplicate column names.")

        for row_number, row in enumerate(reader, start=2):
            lead = {field: (row.get(field) or "").strip() for field in headers}
            issues, warnings = validate_lead(lead, evaluation_date)
            if None in row or any(value is None for value in row.values()):
                issues.append("CSV row has a different number of fields from the header.")
            results.append({
                "csv_row": row_number,
                "lead": lead,
                "validation_status": "review" if issues else "ready_for_scoring",
                "issues": issues,
                "warnings": warnings,
            })
    return results


def score_lead(lead, evaluation_date):
    """Calculate a lead's 1-10 rubric score from company size, source, and recency.
    Return the qualification decision, points breakdown, and explanations.
    """
    size = None if is_missing(lead["company_size"]) else int(lead["company_size"])
    days = (evaluation_date - date.fromisoformat(lead["last_interaction_date"])).days
    source_points = {
        "inbound demo request": 3, "referral": 2, "sales call": 2,
        "webinar attendee": 1, "content download": 1, "linkedin outreach": 0,
    }
    breakdown = {
        "baseline": 1,
        "company_size": 4 if size is not None and 20 <= size <= 500 else 0,
        "source": source_points[lead["source"].casefold()],
        "recency": 2 if days <= 30 else 1 if days <= 90 else 0,
    }
    score = sum(breakdown.values())
    decision = "qualified" if score >= 8 else "review" if score >= 5 else "rejected"
    return {
        "score": score,
        "decision": decision,
        "score_breakdown": breakdown,
        "reasoning": [
            (
                f"Company size {size}: {breakdown['company_size']} points (target 20–500)."
                if size is not None
                else "Company size missing: 0 points."
            ),
            f"Source {lead['source']}: {breakdown['source']} points.",
            f"Interaction {days} days ago: {breakdown['recency']} points.",
            f"Including baseline 1: {score}/10; decision {decision}.",
        ],
    }


def qualify_records(records, evaluation_date):
    """Add scoring results to valid records and mark records with validation issues for human review without a score.
    Update and return the supplied records.
    """
    for record in records:
        if record["issues"]:
            # Unknown evidence is not assigned a misleading numeric score.
            record.update(score=None, decision="review", score_breakdown=None,
                          reasoning=list(record["issues"]))
        else:
            record.update(score_lead(record["lead"], evaluation_date))
    return records


def build_report(leads, evaluation_date):
    """Rank qualified leads and add next actions and rejection factors to the records.
    Return summary statistics, separate decision lists, and all leads in their original order.
    """
    qualified = sorted(
        (item for item in leads if item["decision"] == "qualified"),
        key=lambda item: (-item["score"],
                          -date.fromisoformat(item["lead"]["last_interaction_date"]).toordinal(),
                          item["csv_row"]),
    )
    for item in leads:
        item["priority_rank"] = None
        item["rejection_reasons"] = []
        if item["decision"] == "rejected":
            # These are contributing factors, not independent rejection rules.
            points = item["score_breakdown"]
            if (points["company_size"] == 0
                    and not is_missing(item["lead"]["company_size"])):
                item["rejection_reasons"].append("Outside target company size (20-500 employees)")
            if points["source"] < 3:
                item["rejection_reasons"].append(
                    "Source earned fewer than 3 points (the maximum); the combined score was below the 5-point rejection threshold."
                )
            if points["recency"] < 2:
                item["rejection_reasons"].append("Last interaction is more than 30 days old")
        if item["decision"] == "review":
            item["next_action"] = (
                "Resolve scoring-data issues and reassess." if item["issues"]
                else "Sales to assess fit and interest; score is in the review range."
            )
        elif item["decision"] == "qualified":
            item["next_action"] = (
                "Resolve missing profile information before personalizing outreach."
                if item["warnings"] else "Prepare personalized outreach in priority order."
            )
        else:
            item["next_action"] = "Do not prioritize outreach for this campaign."
    for rank, item in enumerate(qualified, start=1):
        item["priority_rank"] = rank

    review = [item for item in leads if item["decision"] == "review"]
    rejected = [item for item in leads if item["decision"] == "rejected"]
    invalid = sum(bool(item["issues"]) for item in leads)
    reasons = Counter(reason for item in rejected for reason in item["rejection_reasons"])
    total = len(leads)
    return {
        "stage": "prioritized_qualification_without_llm",
        "evaluation_date": evaluation_date.isoformat(),
        "ranking_rule": "Score descending, interaction date descending, original CSV order",
        "summary": {
            "total": total,
            "ready_for_scoring": total - invalid,
            "validation_needs_review": invalid,
            "qualified": len(qualified),
            "qualified_percentage": round(100 * len(qualified) / total, 2) if total else 0.0,
            "review": len(review),
            "review_due_to_score": len(review) - invalid,
            "review_due_to_data": invalid,
            "rejected": len(rejected),
            "leads_with_warnings": sum(bool(item["warnings"]) for item in leads),
            "common_rejection_reasons": [
                {"reason": reason, "count": count}
                for reason, count in sorted(reasons.items(), key=lambda pair: (-pair[1], pair[0]))
            ],
            "rejection_reason_note": "Counts are contributing factors among rejected leads; one lead may have multiple factors. The combined score determines rejection.",
        },
        "priority_queue": qualified,
        "human_review": review,
        "rejected_leads": rejected,
        "leads": leads,
    }


def main():
    """Read command-line options, run validation, qualification, and reporting, then save the report as JSON.
    Optionally add OpenAI drafts; preserve reports and signal any drafting failures with exit code 2.
    """
    default_input = Path(__file__).resolve().with_name("leads_testing.csv")
    default_output = Path(__file__).resolve().with_name("qualification_report.json")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, nargs="?", default=default_input,
                        help="Input leads CSV (defaults to leads_testing.csv in this project)")
    parser.add_argument("--as-of", type=date.fromisoformat, default=date.today(),
                        help="Evaluation date (YYYY-MM-DD); defaults to today")
    parser.add_argument("--output", type=Path, default=default_output)
    parser.add_argument("--draft-outreach", action="store_true", help="Generate unsent OpenAI email drafts")
    parser.add_argument("--model", default=os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"))
    parser.add_argument("--batch-size", type=int, choices=range(2, 21), default=5)
    parser.add_argument("--max-attempts", type=int, choices=range(1, 6), default=3)
    parser.add_argument("--product-context", type=Path,
                        default=Path(__file__).resolve().with_name("product_context.md"))
    args = parser.parse_args()
    if args.input.resolve() == args.output.resolve():
        parser.error("Output must be a different file from the input CSV.")
    if args.draft_outreach and args.product_context.resolve() == args.output.resolve():
        parser.error("Output must be a different file from the product context.")

    try:
        leads = qualify_records(load_and_validate(args.input, args.as_of), args.as_of)
        report = build_report(leads, args.as_of)
        if args.draft_outreach:
            from outreach import add_outreach
            # Preserve qualification results even if the local context is unavailable.
            try:
                context = args.product_context.read_text(encoding="utf-8-sig")
            except (OSError, UnicodeError):
                context = ""
            report = add_outreach(report, context, model=args.model,
                                  batch_size=args.batch_size, max_attempts=args.max_attempts)
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    except (OSError, UnicodeError, ValueError, csv.Error) as error:
        parser.exit(1, f"Error: {error}\n")

    print(json.dumps(report["summary"], indent=2))
    print(f"Qualification report saved to {args.output}")
    if args.draft_outreach:
        print(json.dumps(report["outreach_summary"], indent=2))
        if report["outreach_summary"]["failed"]:
            parser.exit(2, "Outreach incomplete; qualification results and safe error codes are saved in the report.\n")


if __name__ == "__main__":
    main()
