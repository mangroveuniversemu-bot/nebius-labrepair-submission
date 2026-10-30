"""Exercise real loopback HTTP, including refusals; no provider requests."""

import http.client
import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from urllib.parse import urlencode

from labrepair.serve import make_handler


class ReviewServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler())
        cls.port = cls.server.server_port
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)

    def request(self, method, path, data=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        fields = {"Origin": f"http://127.0.0.1:{self.port}", "Content-Type": "application/json"}
        fields.update(headers or {})
        body = json.dumps(data).encode() if data is not None else None
        connection.request(method, path, body=body, headers=fields)
        response = connection.getresponse()
        content = response.read()
        status, received = response.status, dict(response.headers)
        connection.close()
        return status, received, content

    def test_working_review_and_decision_return_exact_bound_receipts(self):
        code, _, body = self.request("POST", "/api/review", {"scenario": "channel-fix"})
        self.assertEqual(code, 200)
        review = json.loads(body)
        code, _, body = self.request("POST", "/api/decision", {
            "scenario": "channel-fix", "receipt_sha256": review["receipt_sha256"], "choice": "hold-for-evidence"
        })
        self.assertEqual(code, 200)
        self.assertFalse(json.loads(body)["changes_scientific_claim"])

    def test_foreign_origin_and_host_cannot_trigger_a_review(self):
        for headers in ({"Origin": "https://example.com"}, {"Host": "example.com"}):
            self.assertEqual(self.request("POST", "/api/review", {"scenario": "channel-fix"}, headers)[0], 403)

    def test_oversized_requests_and_unsupported_media_are_refused(self):
        self.assertEqual(self.request("POST", "/api/review", {"scenario": "x" * 5000})[0], 413)
        self.assertEqual(self.request("POST", "/api/review", {}, {"Content-Type": "text/plain"})[0], 415)

    def test_unknown_scenario_and_dispatch_route_are_refused(self):
        self.assertEqual(self.request("POST", "/api/review", {"scenario": "../private"})[0], 422)
        self.assertEqual(self.request("POST", "/api/execute", {"scenario": "channel-fix"})[0], 422)

    def test_workspace_and_secret_paths_are_not_served(self):
        for path in ("/.env", "/.git/config", "/../README.md", "/evidence/environment.json", "/%2e%2e/.env"):
            self.assertEqual(self.request("GET", path)[0], 404)

    def test_static_assets_have_local_only_security_policy(self):
        for path in ("/", "/app.js", "/style.css"):
            code, headers, body = self.request("GET", path)
            self.assertEqual(code, 200)
            self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
            self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
            self.assertTrue(body)
        code, _, body = self.request("GET", "/api/status")
        self.assertEqual(code, 200)
        capabilities = json.loads(body)["capabilities"]
        self.assertEqual(capabilities["nebius_generation"], "VERIFIED_NEBIUS_HOSTED_NVIDIA")
        self.assertEqual(capabilities["nebius_sandbox_execution"], "VERIFIED_ONE_DISPOSABLE_OPERATION")
        self.assertFalse(capabilities["nvidia_developer_smoke"]["qualifies_as_nebius_inference"])

    def test_download_is_an_attachment_bound_to_a_fresh_review(self):
        _, _, body = self.request("POST", "/api/review", {"scenario": "channel-fix"})
        review = json.loads(body)
        query = urlencode({"scenario": "channel-fix", "receipt_sha256": review["receipt_sha256"], "choice": "hold-for-evidence"})
        code, headers, body = self.request("GET", "/download?" + query)
        self.assertEqual(code, 200)
        self.assertEqual(headers["Content-Disposition"], 'attachment; filename="labrepair-channel-fix.json"')
        exported = json.loads(body)
        self.assertEqual(exported["review"], review)
        self.assertFalse(exported["review_intent"]["authorizes_payment"])
        self.assertEqual(self.request("GET", "/download?" + query.replace(review["receipt_sha256"], "0" * 64))[0], 422)

    def test_recorded_run_is_read_only_pinned_and_has_a_native_download(self):
        code,_,body=self.request("GET","/api/recorded-validation")
        self.assertEqual(code,200)
        record=json.loads(body)
        self.assertEqual(record['sandbox']['status'],'SUCCESS')
        self.assertEqual([c['process_exit_code'] for c in record['cases']],[1,0,1])
        self.assertEqual(record['provider_calls_by_replay'],0)
        code,headers,body=self.request("GET","/download-recorded")
        self.assertEqual(code,200)
        self.assertEqual(headers['Content-Disposition'],'attachment; filename="labrepair-recorded-validation.json"')
        self.assertEqual(json.loads(body),record)
        self.assertEqual(self.request("GET","/api/recorded-validation",headers={'Host':'example.com'})[0],403)

    def test_health_is_independent_and_readiness_verifies_the_saved_evidence(self):
        with patch("labrepair.serve.load_recorded_validation", side_effect=AssertionError("Health must not read receipts")) as load:
            code, _, body = self.request("GET", "/healthz")
            self.assertEqual(code, 200)
            self.assertEqual(json.loads(body), {"status": "OK", "service": "LABREPAIR_LOCAL_REVIEW"})
            load.assert_not_called()
        code, _, body = self.request("GET", "/ready")
        self.assertEqual(code, 200)
        ready = json.loads(body)
        _, _, body = self.request("GET", "/api/recorded-validation")
        record = json.loads(body)
        self.assertEqual(ready["status"], "READY")
        self.assertEqual(ready["recorded_evidence"], record["status"])
        self.assertEqual(ready["receipt_sha256"], record["receipt_sha256"])
        for path in ("/healthz", "/ready"):
            self.assertEqual(self.request("GET", path, headers={"Host": "example.com"})[0], 403)

    def test_missing_recorded_evidence_does_not_disable_local_synthetic_review(self):
        # Common outbound HTTP transports must remain unused for every route.
        # The test client talks only to the real loopback HTTP server.
        with patch("labrepair.serve.load_recorded_validation", side_effect=ValueError("RECORDED_PROVIDER_EVIDENCE_CHANGED")), \
             patch("urllib.request.urlopen", side_effect=AssertionError("Provider request forbidden")) as outbound_urlopen, \
             patch("http.client.HTTPSConnection.request", side_effect=AssertionError("Provider request forbidden")) as outbound_https:
            code, _, body = self.request("GET", "/healthz")
            self.assertEqual(code, 200)
            self.assertEqual(json.loads(body)["status"], "OK")
            code, _, body = self.request("GET", "/ready")
            self.assertEqual(code, 503)
            self.assertEqual(json.loads(body), {"status": "NOT_READY", "error": "RECORDED_EVIDENCE_UNAVAILABLE"})
            code, _, body = self.request("GET", "/api/status")
            self.assertEqual(code, 200)
            status = json.loads(body)
            self.assertIn("channel-fix", status["scenarios"])
            self.assertEqual(status["recorded_evidence"], {"status": "RECORDED_EVIDENCE_UNAVAILABLE", "receipt_sha256": None})
            for capability in ("nebius_generation", "nebius_sandbox_execution", "eligible_nebius_runtime_evidence"):
                self.assertEqual(status["capabilities"][capability], "UNAVAILABLE_BY_THIS_READBACK")
            self.assertEqual(status["capabilities"]["automatic_cloud_dispatch"], "DISABLED")
            self.assertNotIn("live_record_receipt_sha256", status["capabilities"])
            for path in ("/api/recorded-validation", "/download-recorded"):
                code, headers, body = self.request("GET", path)
                self.assertEqual(code, 503)
                self.assertEqual(json.loads(body), {"error": "RECORDED_EVIDENCE_UNAVAILABLE"})
                self.assertNotIn("Content-Disposition", headers)
            code, _, body = self.request("POST", "/api/review", {"scenario": "channel-fix"})
            self.assertEqual(code, 200)
            review = json.loads(body)
            self.assertEqual(review["local_result"], "LOCAL_SEMANTIC_MATCH")
            self.assertEqual(review["candidate_execution"], "NOT_RUN")
            self.assertEqual(review["network_requests"], 0)
            code, _, body = self.request("POST", "/api/decision", {
                "scenario": "channel-fix", "receipt_sha256": review["receipt_sha256"], "choice": "hold-for-evidence",
            })
            self.assertEqual(code, 200)
            self.assertFalse(json.loads(body)["authorizes_payment"])
            outbound_urlopen.assert_not_called()
            outbound_https.assert_not_called()


if __name__ == "__main__":
    unittest.main()
