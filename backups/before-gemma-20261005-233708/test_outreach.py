"""Offline checks: fake API responses only; no credentials or network are used."""

import json
import os
import unittest
from copy import deepcopy
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from main import build_report, load_and_validate, qualify_records
from outreach import DraftError, OpenAIDrafter, add_outreach, prepare_leads, validate_drafts


def sample_report():
    """Load the actual testing data and apply the current local qualification rules."""
    day = date(2024, 1, 20)
    return build_report(qualify_records(load_and_validate(
        Path(__file__).with_name("leads_testing.csv"), day), day), day)


def fake_response(leads, context):
    """Return clearly simulated drafts in reverse order to test ID-based mapping."""
    return json.dumps({"drafts": [
        {"lead_id": lead["lead_id"], "subject": "CRM discovery conversation",
         "body": f"Hello {lead['company'] or lead['name'] or 'there'}, what would your team like to improve?"}
        for lead in reversed(leads)]})


class OutreachTests(unittest.TestCase):
    """Exercise batching, mapping, retries, setup failures, and unchanged scoring."""

    def test_batching_and_preserved_qualification(self):
        """Draft in groups while retaining each lead's score, order, and decision."""
        report = sample_report()
        before = deepcopy(report)
        calls = []
        def request(leads, context):
            calls.append(leads)
            return fake_response(leads, context)
        add_outreach(report, "Discovery only", batch_size=2, request_batch=request)
        expected = len(before["priority_queue"])
        self.assertEqual(len(calls), (expected + 1) // 2)
        self.assertEqual(sum(len(batch) for batch in calls), expected)
        self.assertEqual(report["summary"], before["summary"])
        for original, current in zip(before["leads"], report["leads"]):
            for key in ("lead", "score", "decision", "reasoning", "priority_rank"):
                self.assertEqual(current[key], original[key])
            if current["decision"] == "qualified":
                self.assertEqual(current["outreach"]["status"], "drafted")
                self.assertFalse(current["outreach"]["sent"])
            else:
                self.assertEqual(current["outreach"]["status"], "not_qualified")

    def test_retry_then_success(self):
        """Retry a transient error once, then accept the valid batch."""
        count = []
        waits = []
        def request(leads, context):
            count.append(1)
            if len(count) == 1:
                raise DraftError("api_http_429", retryable=True)
            return fake_response(leads, context)
        report = add_outreach(sample_report(), "context", request_batch=request, sleep=waits.append)
        self.assertEqual(report["outreach_summary"]["failed"], 0)
        self.assertEqual(len(waits), 1)

    def test_bad_output_bounded_retries(self):
        """Reject malformed output after bounded attempts without removing any lead."""
        report = sample_report()
        add_outreach(report, "context", request_batch=lambda *_: "not json", sleep=lambda _: None)
        self.assertEqual(report["outreach_summary"]["api_calls"], 3)
        self.assertEqual(report["outreach_summary"]["failed"], len(report["priority_queue"]))
        self.assertEqual(report["run_status"], "completed_with_outreach_errors")

    def test_permanent_error_stops_calls(self):
        """Do not repeat authentication failures across subsequent batches."""
        def request(*_):
            raise DraftError("api_http_401", stop_run=True)
        report = add_outreach(sample_report(), "context", batch_size=2, request_batch=request)
        self.assertEqual(report["outreach_summary"]["api_calls"], 1)
        self.assertTrue(all(item["outreach"]["error"] == "api_http_401" for item in report["priority_queue"]))

    def test_missing_key(self):
        """Save explicit failures with no API request when no key is configured."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
            report = add_outreach(sample_report(), "context")
        self.assertEqual(report["outreach_summary"]["setup_error"], "missing_api_key")
        self.assertEqual(report["outreach_summary"]["api_calls"], 0)

    def test_no_qualified_leads(self):
        """Empty reports do not require a key, context, or client."""
        report = build_report([], date(2024, 1, 20))
        with patch("outreach.OpenAIDrafter", side_effect=AssertionError("must not create client")):
            add_outreach(report, "")
        self.assertEqual(report["run_status"], "completed")

    def test_response_validation(self):
        """Reject duplicate, missing and foreign IDs, blank fields, and obvious promises."""
        payload = prepare_leads(sample_report()["priority_queue"][:2])
        good = json.loads(fake_response(payload, ""))
        cases = [
            {"drafts": good["drafts"][:1]},
            {"drafts": [good["drafts"][0]] * 2},
            {"drafts": [{**item, "lead_id": "unknown"} for item in good["drafts"]]},
            {"drafts": [{**item, "subject": ""} for item in good["drafts"]]},
            {"drafts": [{**item, "body": item["body"] + " Guaranteed 50% increase."} for item in good["drafts"]]},
        ]
        for data in cases:
            with self.subTest(data=data), self.assertRaises(DraftError):
                validate_drafts(json.dumps(data), payload)

    def test_missing_profile_normalized(self):
        """Map NA and blanks to null; IDs remain unique even when names repeat."""
        records = deepcopy(sample_report()["priority_queue"][:2])
        for item in records:
            item["lead"].update(company="NA", name="", industry="N/A")
        payload = prepare_leads(records)
        self.assertIsNone(payload[0]["company"])
        self.assertIsNone(payload[0]["name"])
        self.assertNotEqual(payload[0]["lead_id"], payload[1]["lead_id"])

    def test_refusal_and_incomplete(self):
        """Inspect response status/refusals before attempting to parse output text."""
        adapter = object.__new__(OpenAIDrafter)
        adapter.model = "test"
        adapter.sdk = SimpleNamespace(APIConnectionError=ConnectionError, APIStatusError=RuntimeError)
        for response, code in [
            (SimpleNamespace(output=[], status="incomplete"), "incomplete_response"),
            (SimpleNamespace(output=[SimpleNamespace(content=[SimpleNamespace(type="refusal")])], status="completed"), "model_refusal"),
        ]:
            adapter.client = SimpleNamespace(responses=SimpleNamespace(create=lambda **_: response))
            with self.assertRaises(DraftError) as caught:
                adapter([], "context")
            self.assertEqual(caught.exception.code, code)

    def test_other_sdk_error_is_sanitized(self):
        """Convert unexpected SDK API errors into safe failures without leaking response text."""
        class FakeAPIError(Exception):
            pass
        def fail(**kwargs):
            raise FakeAPIError("private provider response")
        adapter = object.__new__(OpenAIDrafter)
        adapter.model = "test"
        adapter.sdk = SimpleNamespace(APIConnectionError=ConnectionError,
                                      APIStatusError=RuntimeError, APIError=FakeAPIError)
        adapter.client = SimpleNamespace(responses=SimpleNamespace(create=fail))
        with self.assertRaises(DraftError) as caught:
            adapter([], "context")
        self.assertEqual(str(caught.exception), "api_response_error")

    def test_failed_batch_does_not_block_later_batch(self):
        """Retain successful later batches when one batch repeatedly fails validation."""
        calls = []
        def request(leads, context):
            calls.append(1)
            if len(calls) <= 3:
                return "invalid json"
            return fake_response(leads, context)
        report = add_outreach(sample_report(), "context", batch_size=2,
                              request_batch=request, sleep=lambda _: None)
        self.assertEqual(report["outreach_summary"]["failed"], 2)
        self.assertEqual(report["outreach_summary"]["drafted"], len(report["priority_queue"]) - 2)

    def test_real_sdk_with_fake_http_transport(self):
        """Check real SDK request serialization and error handling without a network request."""
        try:
            import httpx
            import openai
        except ImportError:
            self.skipTest("Install requirements.txt for the SDK transport check")
        seen = []
        payload = prepare_leads(sample_report()["priority_queue"][:2])
        def handler(request):
            body = json.loads(request.content)
            seen.append(body)
            self.assertTrue(body["text"]["format"]["strict"])
            self.assertFalse(body["store"])
            self.assertEqual(json.loads(body["input"])["leads"], payload)
            return httpx.Response(200, json={
                "id": "resp_fake", "object": "response", "created_at": 0,
                "status": "completed", "model": "gpt-4.1-mini", "output": [{
                    "type": "message", "id": "msg_fake", "role": "assistant", "status": "completed",
                    "content": [{"type": "output_text", "text": fake_response(payload, ""), "annotations": []}],
                }],
            })
        adapter = object.__new__(OpenAIDrafter)
        adapter.sdk, adapter.model = openai, "gpt-4.1-mini"
        adapter.client = openai.OpenAI(api_key="test-only-not-a-real-key", max_retries=0,
            http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        try:
            self.assertEqual(len(validate_drafts(adapter(payload, "context"), payload)), 2)
            self.assertEqual(len(seen), 1)
        finally:
            adapter.close()
        def error_handler(request):
            return httpx.Response(429, json={"error": {"message": "test quota", "type": "insufficient_quota", "code": "insufficient_quota"}})
        adapter.client = openai.OpenAI(api_key="test-only-not-a-real-key", max_retries=0,
            http_client=httpx.Client(transport=httpx.MockTransport(error_handler)))
        try:
            with self.assertRaises(DraftError) as caught:
                adapter(payload, "context")
            self.assertTrue(caught.exception.stop_run)
            self.assertEqual(caught.exception.code, "insufficient_api_quota")
        finally:
            adapter.close()


    def test_credit_exhaustion_stops_retries(self):
        """Report depleted credits clearly without retrying a billing failure."""
        import httpx
        import openai
        adapter = object.__new__(OpenAIDrafter)
        adapter.sdk, adapter.model = openai, "gpt-4.1-mini"
        calls = []
        def handler(request):
            calls.append(1)
            return httpx.Response(429, json={"error": {
                "message": "test billing error", "type": "insufficient_quota",
                "code": "credit_balance_exhausted"}})
        adapter.client = openai.OpenAI(api_key="test-only-not-a-real-key", max_retries=0,
            http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        try:
            report = add_outreach(sample_report(), "context", batch_size=2,
                                  request_batch=adapter)
            self.assertEqual(len(calls), 1)
            self.assertTrue(all(item["outreach"]["error"] == "credit_balance_exhausted"
                                for item in report["priority_queue"]))
        finally:
            adapter.close()


if __name__ == "__main__":
    unittest.main()
