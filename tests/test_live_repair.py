"""Mocked transport tests only: never call an inference API or read a real key."""
import io
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from http.client import IncompleteRead

from labrepair.live_repair import ENDPOINT, MODEL, LiveRepairError, NoRedirect, fixed_request, preview, run_live
from labrepair.daily_budget import DailyLimitExceeded, status


def fabricated_response(content=None, **changes):
    value = {"model": MODEL, "choices": [{"finish_reason": "stop", "message": {
        "role": "assistant", "content": content or '{"channel_signs":[1,1,-1,-1],"offsets":[0,0,0,0]}'}}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 30, "total_tokens": 130}}
    value.update(changes)
    return json.dumps(value).encode()


class Response(io.BytesIO):
    status = 200


class LiveRepairTests(unittest.TestCase):
    def test_preview_and_missing_billing_consent_never_read_key_or_open_transport(self):
        with patch("labrepair.live_repair.os.environ.get", side_effect=AssertionError("No key access")), \
                patch("labrepair.live_repair.request.build_opener", side_effect=AssertionError("No transport")):
            self.assertEqual(preview()["network_requests"], 0)
            with self.assertRaises(LiveRepairError):
                run_live(confirm_provider_billing=False, run_id="sample")

    def test_exact_request_once_then_existing_reviewer_and_no_key_in_receipts(self):
        with tempfile.TemporaryDirectory() as folder, \
                patch.dict("os.environ", {"NEBIUS_API_KEY": "fabricated-test-secret"}), \
                patch("labrepair.live_repair.request.build_opener") as factory:
            factory.return_value.open.return_value = Response(fabricated_response())
            result = run_live(confirm_provider_billing=True, run_id="test", output_root=Path(folder))
            self.assertEqual(result["status"], "MODEL_REPAIR_VERIFIED")
            self.assertEqual(result["usage"]["total_tokens"], 130)
            self.assertEqual(result["actual_billed_currency"], "unknown")
            outgoing = factory.return_value.open.call_args.args[0]
            self.assertEqual(outgoing.full_url, ENDPOINT)
            self.assertEqual(outgoing.data, fixed_request())
            self.assertEqual(outgoing.get_method(), "POST")
            self.assertEqual(factory.return_value.open.call_count, 1)
            for path in (Path(folder) / "test").iterdir():
                self.assertNotIn(b"fabricated-test-secret", path.read_bytes())
            with self.assertRaises(FileExistsError):
                run_live(confirm_provider_billing=True, run_id="test", output_root=Path(folder))
            self.assertEqual(factory.return_value.open.call_count, 1)

    def test_http_failure_is_not_retried_and_does_not_persist_error_body(self):
        with tempfile.TemporaryDirectory() as folder, \
                patch.dict("os.environ", {"NEBIUS_API_KEY": "fabricated-test-secret"}), \
                patch("labrepair.live_repair.request.build_opener") as factory:
            factory.return_value.open.side_effect = HTTPError(ENDPOINT, 429, "fabricated-test-secret", {}, io.BytesIO(b"private error"))
            result = run_live(confirm_provider_billing=True, run_id="test", output_root=Path(folder))
            self.assertEqual(result["status"], "FAILED")
            self.assertEqual(result["http_status"], 429)
            self.assertEqual(factory.return_value.open.call_count, 1)
            self.assertFalse((Path(folder) / "test/response.json").exists())
            self.assertNotIn("fabricated-test-secret", json.dumps(result))

    def test_oversized_or_secret_echo_response_is_not_saved(self):
        for raw in (b"x" * 65537, fabricated_response("fabricated-test-secret")):
            with self.subTest(size=len(raw)), tempfile.TemporaryDirectory() as folder, \
                    patch.dict("os.environ", {"NEBIUS_API_KEY": "fabricated-test-secret"}), \
                    patch("labrepair.live_repair.request.build_opener") as factory:
                factory.return_value.open.return_value = Response(raw)
                result = run_live(confirm_provider_billing=True, run_id="test", output_root=Path(folder))
                self.assertEqual(result["status"], "FAILED")
                self.assertFalse((Path(folder) / "test/response.json").exists())
                self.assertNotIn("fabricated-test-secret", json.dumps(result))

    def test_wrong_model_truncation_and_tool_calls_cannot_become_verified(self):
        truncated = json.loads(fabricated_response())
        truncated["choices"][0]["finish_reason"] = "length"
        tool = json.loads(fabricated_response())
        tool["choices"][0]["message"]["tool_calls"] = [{"name": "execute"}]
        for raw in (fabricated_response(model="another/model"), json.dumps(truncated).encode(), json.dumps(tool).encode()):
            with self.subTest(raw=raw), tempfile.TemporaryDirectory() as folder, \
                    patch.dict("os.environ", {"NEBIUS_API_KEY": "fabricated-test-secret"}), \
                    patch("labrepair.live_repair.request.build_opener") as factory:
                factory.return_value.open.return_value = Response(raw)
                result = run_live(confirm_provider_billing=True, run_id="test", output_root=Path(folder))
                self.assertEqual(result["status"], "FAILED")
                self.assertEqual(factory.return_value.open.call_count, 1)

    def test_redirects_and_changed_request_do_not_forward_credentials(self):
        self.assertIsNone(NoRedirect().redirect_request(None, None, 307, "redirect", {}, "https://elsewhere.invalid"))
        with patch("labrepair.live_repair.REQUEST_FILE") as source, \
                patch("labrepair.live_repair.os.environ.get", side_effect=AssertionError("No key access")):
            source.read_bytes.return_value = b'{"model":"changed"}'
            with self.assertRaises(LiveRepairError):
                run_live(confirm_provider_billing=True, run_id="test")

    def test_sixth_live_request_is_blocked_before_transport_even_after_errors(self):
        with tempfile.TemporaryDirectory() as folder, \
                patch.dict("os.environ", {"NEBIUS_API_KEY": "fabricated-test-secret"}), \
                patch("labrepair.live_repair.request.build_opener") as factory:
            factory.return_value.open.side_effect = HTTPError(ENDPOINT, 500, "error", {}, None)
            for n in range(5):
                run_live(confirm_provider_billing=True, run_id="run" + str(n), output_root=Path(folder))
            with self.assertRaises(DailyLimitExceeded):
                run_live(confirm_provider_billing=True, run_id="run6", output_root=Path(folder))
            self.assertEqual(factory.return_value.open.call_count, 5)
            snapshot = status(Path(folder) / "budget.sqlite")
            self.assertEqual(snapshot["daily_reserved_usd"], "0.050000")
            self.assertEqual(snapshot["warning"], "DAILY_LIMIT_REACHED")

    def test_incomplete_body_keeps_its_reservation_without_retry(self):
        with tempfile.TemporaryDirectory() as folder, \
                patch.dict("os.environ", {"NEBIUS_API_KEY": "fabricated-test-secret"}), \
                patch("labrepair.live_repair.request.build_opener") as factory:
            factory.return_value.open.return_value.__enter__.side_effect = IncompleteRead(b"prefix", 10)
            result = run_live(confirm_provider_billing=True, run_id="test", output_root=Path(folder))
            self.assertEqual(result["reason"], "TRANSPORT_ERROR_NO_RETRY")
            self.assertEqual(result["daily_budget_reservation"]["daily_reserved_calls"], 1)
            self.assertEqual(factory.return_value.open.call_count, 1)

    def test_receipt_write_failure_never_reports_zero_requests(self):
        script = Path(__file__).resolve().parents[1] / "scripts/run_live_repair.py"
        spec = importlib.util.spec_from_file_location("live_cli_test", script)
        cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cli)
        capture = io.StringIO()
        with patch.object(cli, "run_live", side_effect=OSError("post-dispatch write failed")), \
                patch("sys.argv", [str(script), "--live", "--confirm-provider-billing"]), \
                patch("sys.stdout", capture):
            self.assertEqual(cli.main(), 2)
        result = json.loads(capture.getvalue())
        self.assertEqual(result["network_requests"], "unknown")
        self.assertTrue(result["request_may_have_been_sent"])


if __name__ == "__main__":
    unittest.main()
