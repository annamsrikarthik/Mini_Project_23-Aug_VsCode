"""Offline checks: fake API responses only; no credentials or network are used."""

import json
import os
import unittest
from copy import deepcopy
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from main import build_report, load_and_validate, qualify_records
from outreach import DraftError, OllamaDrafter, OpenAIDrafter, add_outreach, prepare_leads, validate_drafts


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
        """Save explicit OpenAI failures without an API request when its key is missing."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
            report = add_outreach(sample_report(), "context", provider="openai")
        self.assertEqual(report["outreach_summary"]["setup_error"], "missing_api_key")
        self.assertEqual(report["outreach_summary"]["api_calls"], 0)

    def test_no_qualified_leads(self):
        """Empty reports do not require a key, context, or client."""
        report = build_report([], date(2024, 1, 20))
        with patch("outreach.OpenAIDrafter", side_effect=AssertionError("must not create client")), \
                patch("outreach.OllamaDrafter", side_effect=AssertionError("must not create client")):
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
        records[0]["lead"]["source"] = "inbound demo request"
        records[1]["lead"]["source"] = "sales call"
        payload = prepare_leads(records)
        self.assertIsNone(payload[0]["company"])
        self.assertIsNone(payload[0]["name"])
        self.assertNotEqual(payload[0]["lead_id"], payload[1]["lead_id"])
        self.assertTrue(all("source" not in lead for lead in payload))
        self.assertEqual(payload[0]["outreach_intent"], "acknowledge_demo_request")
        self.assertEqual(payload[1]["outreach_intent"], "neutral_discovery")

    def test_sender_and_prior_contact_claims_are_rejected(self):
        """Reject the invented affiliation and prior conversation found in live drafts."""
        payload = prepare_leads(sample_report()["priority_queue"][:1])
        good = json.loads(fake_response(payload, ""))
        for phrase in ("I'm reaching out from Salesforce.", "It was great speaking with you earlier.",
                       "Test_MissingName, we appreciate you taking the time to speak with us."):
            data = deepcopy(good)
            data["drafts"][0]["body"] += " " + phrase
            with self.subTest(phrase=phrase), self.assertRaises(DraftError) as caught:
                validate_drafts(json.dumps(data), payload)
            self.assertEqual(caught.exception.code, "unsupported_sender_or_prior_contact")
        neutral = deepcopy(good)
        neutral["drafts"][0]["body"] += (
            " Would you like to discuss your Salesforce needs? Could we schedule a brief conversation?")
        accepted = validate_drafts(json.dumps(neutral), payload)
        self.assertEqual(accepted[payload[0]["lead_id"]]["body"], neutral["drafts"][0]["body"])

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
            self.skipTest("Optional OpenAI SDK is not installed")
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
        try:
            import httpx
            import openai
        except ImportError:
            self.skipTest("Optional OpenAI SDK is not installed")
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


def local_http_response(payload, status=200):
    """Build a simulated HTTP response so Ollama tests never contact a server."""
    response = Mock(status=status)
    response.read.return_value = json.dumps(payload).encode("utf-8")
    return response


class OllamaTests(unittest.TestCase):
    """Check local requests, safe failures, bounded retries, and no paid fallback."""

    def test_local_default_works_without_openai_key(self):
        """Use Gemma locally even when no OpenAI key exists or its model variable is set."""
        report = sample_report()
        leads = prepare_leads(report["priority_queue"])
        with patch.dict(os.environ, {"OPENAI_API_KEY": "", "OPENAI_MODEL": "paid-model"}, clear=True), \
                patch("outreach.HTTPConnection") as factory, \
                patch("outreach.OpenAIDrafter", side_effect=AssertionError("paid client forbidden")):
            connection = factory.return_value
            connection.getresponse.return_value = local_http_response({
                "done": True, "done_reason": "stop",
                "message": {"role": "assistant", "content": fake_response(leads, "")}})
            add_outreach(report, "Discovery only", request_timeout=75)
            factory.assert_called_once_with("127.0.0.1", 11434, timeout=75)
            request = connection.request.call_args
            self.assertEqual(request.args[:2], ("POST", "/api/chat"))
            raw_body = request.kwargs.get("body", request.args[2] if len(request.args) > 2 else None)
            headers = request.kwargs.get("headers", request.args[3] if len(request.args) > 3 else {})
            body = json.loads(raw_body)
            self.assertEqual(body["model"], "gemma3:4b")
            self.assertFalse(body["stream"])
            self.assertEqual(body["options"]["temperature"], 0)
            self.assertEqual(body["format"]["type"], "object")
            self.assertEqual(body["format"]["required"], ["drafts"])
            self.assertFalse(any(key.lower() == "authorization" for key in headers))
            self.assertEqual(json.loads(body["messages"][-1]["content"])["leads"], leads)
            self.assertGreaterEqual(connection.close.call_count, 1)
        self.assertEqual(report["outreach_summary"]["provider"], "ollama")
        self.assertEqual(report["outreach_summary"]["model"], "gemma3:4b")
        self.assertEqual(report["outreach_summary"]["drafted"], len(leads))
        for record in report["priority_queue"]:
            lead = prepare_leads([record])[0]
            expected = validate_drafts(fake_response([lead], ""), [lead])[lead["lead_id"]]
            self.assertEqual(record["outreach"]["draft"], expected)
            self.assertFalse(record["outreach"]["sent"])
            self.assertTrue(record["outreach"]["requires_sales_review"])

    def test_unavailable_local_server_never_falls_back(self):
        """Stop all remaining batches on a missing local server without a paid request."""
        with patch("outreach.HTTPConnection") as factory, \
                patch("outreach.OpenAIDrafter", side_effect=AssertionError("paid fallback forbidden")):
            factory.return_value.request.side_effect = ConnectionRefusedError("private socket detail")
            report = add_outreach(sample_report(), "context", batch_size=2, sleep=lambda _: None)
        self.assertEqual(report["outreach_summary"]["api_calls"], 1)
        self.assertEqual(report["outreach_summary"]["failed"], len(report["priority_queue"]))
        self.assertTrue(all(item["outreach"]["error"] == "ollama_unavailable"
                            for item in report["priority_queue"]))

    def test_local_retry_corrects_personalization_without_stale_feedback(self):
        """Retry a missing-company draft with correction guidance, then clear it for later batches."""
        report = sample_report()
        leads = prepare_leads(report["priority_queue"])
        batches = [leads[start:start + 2] for start in range(0, len(leads), 2)]
        missing_company = json.loads(fake_response(batches[0], ""))
        missing_company["drafts"][0]["body"] = "Hello, how does your team manage customer relationships?"
        responses = [json.dumps(missing_company)] + [fake_response(batch, "") for batch in batches]
        waits = []
        with patch("outreach.HTTPConnection") as factory:
            connection = factory.return_value
            connection.getresponse.side_effect = [local_http_response({
                "done": True, "message": {"content": response}}) for response in responses]
            add_outreach(report, "Discovery only", batch_size=2, max_attempts=2, sleep=waits.append)
            requests = [json.loads(call.kwargs["body"]) for call in connection.request.call_args_list]
        self.assertEqual(report["outreach_summary"]["drafted"], len(leads))
        self.assertEqual(report["outreach_summary"]["failed"], 0)
        self.assertEqual(report["outreach_summary"]["api_calls"], len(batches) + 1)
        self.assertEqual(len(waits), 1)
        self.assertNotIn("Correction for this retry:", requests[0]["messages"][0]["content"])
        self.assertIn("The last draft omitted a company/contact.", requests[1]["messages"][0]["content"])
        for request in requests[2:]:
            self.assertNotIn("Correction for this retry:", request["messages"][0]["content"])
        correction_input = json.loads(requests[1]["messages"][1]["content"])
        self.assertEqual(correction_input["required_text_by_lead"], {
            lead["lead_id"]: lead["company"] or lead["name"] for lead in batches[0]})

    def test_timeout_retries_are_bounded(self):
        """Limit local timeouts to the configured attempts and retain qualification results."""
        report = sample_report()
        original_summary = deepcopy(report["summary"])
        waits = []
        with patch("outreach.HTTPConnection") as factory:
            factory.return_value.request.side_effect = TimeoutError("private timeout detail")
            add_outreach(report, "context", max_attempts=2, request_timeout=15, sleep=waits.append)
            factory.assert_called_once_with("127.0.0.1", 11434, timeout=15)
        self.assertEqual(report["outreach_summary"]["api_calls"], 2)
        self.assertEqual(len(waits), 1)
        self.assertEqual(report["summary"], original_summary)
        self.assertTrue(all(item["outreach"]["error"] == "ollama_timeout"
                            for item in report["priority_queue"]))

    def test_http_failures_are_sanitized(self):
        """Classify local HTTP failures without including server response text in errors."""
        for status, code, retryable, stop_run in [
            (404, "ollama_model_not_found", False, True),
            (400, "ollama_http_400", False, True),
            (429, "ollama_http_429", True, False),
            (503, "ollama_http_503", True, False),
        ]:
            with self.subTest(status=status), patch("outreach.HTTPConnection") as factory:
                factory.return_value.getresponse.return_value = local_http_response(
                    {"error": "private provider text"}, status=status)
                adapter = OllamaDrafter()
                with self.assertRaises(DraftError) as caught:
                    adapter([], "context")
                self.assertEqual(str(caught.exception), code)
                self.assertEqual(caught.exception.retryable, retryable)
                self.assertEqual(caught.exception.stop_run, stop_run)
                self.assertGreaterEqual(factory.return_value.close.call_count, 1)

    def test_invalid_or_incomplete_envelope(self):
        """Reject malformed or truncated local responses before validating any draft."""
        cases = [
            ({"done": True}, "ollama_invalid_response"),
            ({"done": True, "message": {"content": None}}, "ollama_invalid_response"),
            ({"done": False, "message": {"content": "{}"}}, "ollama_incomplete_response"),
            ({"done": True, "done_reason": "length", "message": {"content": "{}"}},
             "ollama_incomplete_response"),
        ]
        for payload, code in cases:
            with self.subTest(payload=payload), patch("outreach.HTTPConnection") as factory:
                factory.return_value.getresponse.return_value = local_http_response(payload)
                with self.assertRaises(DraftError) as caught:
                    OllamaDrafter()([], "context")
                self.assertEqual(caught.exception.code, code)
                self.assertTrue(caught.exception.retryable)
        with patch("outreach.HTTPConnection") as factory:
            response = Mock(status=200)
            response.read.return_value = b"not json"
            factory.return_value.getresponse.return_value = response
            with self.assertRaises(DraftError) as caught:
                OllamaDrafter()([], "context")
            self.assertEqual(caught.exception.code, "ollama_invalid_response")


if __name__ == "__main__":
    unittest.main()
