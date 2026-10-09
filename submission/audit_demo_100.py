"""Audit the 100-lead classroom run against preserved inputs and known rubric cases."""

import csv
import hashlib
import json
import os
import sys
from collections import Counter
from datetime import date
from pathlib import Path


STAGE = Path(__file__).resolve().parent
PROJECT = Path(os.environ.get("LEAD_PROJECT_ROOT", STAGE))
sys.path.insert(0, str(PROJECT))
from outreach import prepare_leads, validate_drafts


def read_csv(path):
    """Read a sample CSV as text fields for direct comparison with reported leads."""
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def file_hash(path):
    """Return a SHA-256 digest that identifies the exact fixture or result audited."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit_qualification(report, manifest, input_rows):
    """Check all 100 inputs, original row preservation, ranks, totals, and twelve known cases."""
    records = report["leads"]
    assert len(records) == len(input_rows) == manifest["total_rows"] == 100
    assert report["evaluation_date"] == manifest["evaluation_date"] == "2024-01-20"
    assert [record["lead"] for record in records] == input_rows
    assert (report["summary"]["qualified"], report["summary"]["review"],
            report["summary"]["rejected"]) == (35, 36, 29)
    assert report["summary"]["validation_needs_review"] == 5
    assert report["summary"]["total"] == 100
    assert all(record["csv_row"] == position + 2 for position, record in enumerate(records))

    expected_order = sorted((item for item in records if item["decision"] == "qualified"),
                            key=lambda item: (-item["score"],
                                              -date.fromisoformat(item["lead"]["last_interaction_date"]).toordinal(),
                                              item["csv_row"]))
    assert [item["csv_row"] for item in report["priority_queue"]] == [
        item["csv_row"] for item in expected_order]
    assert [item["priority_rank"] for item in expected_order] == list(range(1, 36))
    assert all(item["priority_rank"] is None for item in records if item["decision"] != "qualified")

    for case_index, case in enumerate(manifest["synthetic_cases"]):
        for item in records[52 + case_index * 4:52 + (case_index + 1) * 4]:
            assert item["score"] == case["expected_score"], (case["name"], item["score"])
            assert item["decision"] == case["expected_decision"], (case["name"], item["decision"])
            assert item["lead"]["company_size"] == case["company_size"]
            if case["name"] == "missing_size_demo":
                assert item["warnings"] and not item["issues"]


def audit_outreach(report, qualification):
    """Check score preservation and safe draft or failure status for every qualified row."""
    for original, current in zip(qualification["leads"], report["leads"]):
        for field in ("lead", "score", "decision", "score_breakdown", "reasoning",
                      "issues", "warnings", "priority_rank"):
            assert original[field] == current[field], (current["csv_row"], field)
    stats = report["outreach_summary"]
    assert (stats["provider"], stats["model"], stats["batch_size"]) == ("ollama", "gemma3:4b", 2)
    assert stats["drafted"] + stats["failed"] == report["summary"]["qualified"] == 35
    assert all(item["outreach"]["status"] == "not_qualified"
               for item in report["leads"] if item["decision"] != "qualified")
    failures = Counter()
    for item in report["priority_queue"]:
        state = item["outreach"]
        if state["status"] == "drafted":
            assert state["sent"] is False and state["requires_sales_review"] is True
            assert state["error"] is None
            validate_drafts(json.dumps({"drafts": [{"lead_id": f"row-{item['csv_row']}",
                                                  **state["draft"]}]}), prepare_leads([item]))
        else:
            assert state["status"] == "failed" and state["draft"] is None and state["error"]
            failures[state["error"]] += 1
    assert len(report["sample_outreach_messages"]) == min(5, stats["drafted"])
    return failures


def main():
    """Write a compact audit record after checking both the qualification and full runs."""
    manifest = json.loads((STAGE / "demo_100_manifest.json").read_text(encoding="utf-8"))
    input_path = STAGE / "leads_100_demo.csv"
    assert file_hash(input_path) == manifest["combined_csv_sha256"]
    for source in manifest["source_files"]:
        assert file_hash(PROJECT / source["name"]) == source["sha256"]
    originals = read_csv(PROJECT / "leads_training.csv") + read_csv(PROJECT / "leads_testing.csv")
    inputs = read_csv(input_path)
    assert inputs[:52] == originals
    qualification = json.loads((STAGE / "qualification_100_demo.json").read_text(encoding="utf-8"))
    audit_qualification(qualification, manifest, inputs)
    result = {"qualification_verified": True, "total_leads": 100,
              "decisions": {key: qualification["summary"][key]
                            for key in ("qualified", "review", "rejected")},
              "synthetic_cases_verified": 48,
              "existing_rows_preserved": 52,
              "combined_csv_sha256": file_hash(input_path)}
    full_path = STAGE / "outreach_100_demo.json"
    if full_path.exists():
        full = json.loads(full_path.read_text(encoding="utf-8"))
        audit_qualification(full, manifest, inputs)
        failures = audit_outreach(full, qualification)
        result.update({"outreach_verified": True, "outreach": full["outreach_summary"],
                       "failure_codes": dict(failures), "outreach_report_sha256": file_hash(full_path)})
    else:
        result["outreach_verified"] = False
    output = STAGE / "demo_100_audit.json"
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
