"""Build a reproducible 100-lead classroom dataset from the existing two CSVs.
The first 52 records are copied unchanged; 48 clearly synthetic rows cover rubric edges.
"""

import csv
import hashlib
import json
import os
from datetime import date, timedelta
from pathlib import Path


STAGE = Path(__file__).resolve().parent
PROJECT = Path(os.environ.get("LEAD_PROJECT_ROOT", STAGE))
EVALUATION_DATE = date(2024, 1, 20)
COLUMNS = ["name", "company", "company_size", "industry", "source", "last_interaction_date"]
CASES = [
    ("minimum_target_demo_today", "20", "Inbound demo request", 0, 10, "qualified"),
    ("maximum_target_referral_day30", "500", "Referral", 30, 9, "qualified"),
    ("target_webinar_day30", "120", "Webinar attendee", 30, 8, "qualified"),
    ("target_demo_day90", "75", "Inbound demo request", 90, 9, "qualified"),
    ("just_over_target_demo", "501", "Inbound demo request", 0, 6, "review"),
    ("just_below_target_referral", "19", "Referral", 0, 5, "review"),
    ("target_content_day91", "150", "Content download", 91, 6, "review"),
    ("missing_size_demo", "NA", "Inbound demo request", 0, 6, "review"),
    ("small_linkedin_day91", "10", "LinkedIn outreach", 91, 1, "rejected"),
    ("large_content_day90", "1000", "Content download", 90, 3, "rejected"),
    ("small_salescall_day91", "15", "Sales call", 91, 3, "rejected"),
    ("small_webinar_today", "12", "Webinar attendee", 0, 4, "rejected"),
]


def source_hash(path):
    """Record a source file's hash so the combined fixture can be traced back to it."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_rows(path):
    """Read one original CSV without changing any of its lead values or column order."""
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != COLUMNS:
            raise ValueError(f"Unexpected columns in {path.name}: {reader.fieldnames}")
        rows = list(reader)
    if any(set(row) != set(COLUMNS) or any(value is None for value in row.values()) for row in rows):
        raise ValueError(f"Malformed row in {path.name}")
    return rows


def make_synthetic_rows():
    """Create four unique sample leads for each of twelve explicit rubric cases."""
    rows = []
    for case_index, (label, size, source, age, score, decision) in enumerate(CASES, start=1):
        for variant in range(1, 5):
            number = (case_index - 1) * 4 + variant
            rows.append({
                "name": f"ScaleDemo_{number:03d}",
                "company": f"Sample Company {number:03d}",
                "company_size": size,
                "industry": ("SaaS", "Finance", "Retail", "Logistics")[variant - 1],
                "source": source,
                "last_interaction_date": (EVALUATION_DATE - timedelta(days=age)).isoformat(),
            })
    return rows


def main():
    """Combine 52 original rows with 48 synthetic rows and save a traceable manifest."""
    training_path = PROJECT / "leads_training.csv"
    testing_path = PROJECT / "leads_testing.csv"
    training = read_rows(training_path)
    testing = read_rows(testing_path)
    if (len(training), len(testing)) != (29, 23):
        raise ValueError("Expected 29 training and 23 testing rows; inspect source changes first.")
    generated = make_synthetic_rows()
    rows = training + testing + generated
    if len(rows) != 100 or len(generated) != 48:
        raise ValueError("Demo must contain exactly 100 rows, including 48 synthetic rows.")
    output = STAGE / "leads_100_demo.csv"
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    manifest = {
        "purpose": "Reproducible classroom scale demonstration; synthetic rows are not customers.",
        "evaluation_date": EVALUATION_DATE.isoformat(),
        "source_files": [
            {"name": training_path.name, "rows": len(training), "sha256": source_hash(training_path)},
            {"name": testing_path.name, "rows": len(testing), "sha256": source_hash(testing_path)},
        ],
        "source_rows_copied": len(training) + len(testing),
        "synthetic_rows_added": len(generated),
        "total_rows": len(rows),
        "synthetic_cases": [
            {"name": label, "rows": 4, "company_size": size, "source": source,
             "days_since_interaction": age, "expected_score": score, "expected_decision": decision}
            for label, size, source, age, score, decision in CASES
        ],
        "combined_csv_sha256": source_hash(output),
    }
    (STAGE / "demo_100_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Prepared {len(rows)} leads: {len(training)} training + {len(testing)} testing + {len(generated)} synthetic.")


if __name__ == "__main__":
    main()
