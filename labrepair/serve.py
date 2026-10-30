"""Loopback-only scientific review UI. No shell, provider, upload or file browser."""

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from labrepair.paths import ROOT
from labrepair.candidate_review import unique_object
from labrepair.recorded_validation import load_recorded_validation
from labrepair.scientific_workflow import (
    SCENARIOS, ScienceReviewError, decision_record, run_scenario,
)

STATIC = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
}
MAX_BODY = 4096


def make_handler():
    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(5)

        def log_message(self, _format, *_args):
            pass  # No account information, candidate text or request bodies logged.

        def _send(self, status, data, content_type="application/json; charset=utf-8", filename=None):
            raw = data if isinstance(data, bytes) else json.dumps(data).encode()
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            if filename:
                self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
            self.end_headers()
            self.wfile.write(raw)

        def _local_host(self):
            return self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"

        def _discard_small_body(self):
            # Drain a bounded rejected request before closing the connection.
            # Otherwise Windows may reset the socket before delivering the 403.
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if 0 < length <= 65536 and not self.headers.get("Transfer-Encoding"):
                    self.rfile.read(length)
            except (ValueError, OSError):
                pass

        def do_GET(self):
            if not self._local_host():
                return self._send(403, {"error": "LOOPBACK_HOST_REQUIRED"})
            path = urlsplit(self.path).path
            if path in STATIC:
                name, kind = STATIC[path]
                return self._send(200, (ROOT / "review-app" / name).read_bytes(), kind)
            if path == "/healthz":
                # Service liveness does not inspect archived receipts or providers.
                return self._send(200, {"status": "OK", "service": "LABREPAIR_LOCAL_REVIEW"})
            if path == "/ready":
                try:
                    recorded = load_recorded_validation()
                except (OSError, ValueError, KeyError, TypeError):
                    return self._send(503, {"status": "NOT_READY", "error": "RECORDED_EVIDENCE_UNAVAILABLE"})
                return self._send(200, {
                    "status": "READY", "recorded_evidence": recorded["status"],
                    "receipt_sha256": recorded["receipt_sha256"],
                })
            if path == "/api/status":
                capabilities = json.loads((ROOT / "evidence/capability_status_20261026.json").read_text())
                try:
                    recorded = load_recorded_validation()
                except (OSError, ValueError, KeyError, TypeError):
                    # A historical capability snapshot cannot vouch for a failed
                    # readback. Keep local synthetic review available separately.
                    capabilities.update(
                        nebius_generation="UNAVAILABLE_BY_THIS_READBACK",
                        nebius_sandbox_execution="UNAVAILABLE_BY_THIS_READBACK",
                        eligible_nebius_runtime_evidence="UNAVAILABLE_BY_THIS_READBACK",
                        automatic_cloud_dispatch="DISABLED",
                    )
                    capabilities.pop("live_record_receipt_sha256", None)
                    recorded_evidence = {"status": "RECORDED_EVIDENCE_UNAVAILABLE", "receipt_sha256": None}
                else:
                    capabilities.update(nebius_generation="VERIFIED_NEBIUS_HOSTED_NVIDIA",nebius_sandbox_execution="VERIFIED_ONE_DISPOSABLE_OPERATION",eligible_nebius_runtime_evidence="OBSERVED_MODEL_INFERENCE_AND_ISOLATED_TESTS",automatic_cloud_dispatch="DISABLED",live_record_receipt_sha256=recorded["receipt_sha256"])
                    recorded_evidence = {"status": recorded["status"], "receipt_sha256": recorded["receipt_sha256"]}
                return self._send(200, {"scenarios": SCENARIOS, "capabilities": capabilities, "recorded_evidence": recorded_evidence})
            if path in ("/api/recorded-validation", "/download-recorded"):
                try:
                    recorded=load_recorded_validation()
                    return self._send(200,recorded,filename="labrepair-recorded-validation.json" if path=="/download-recorded" else None)
                except (OSError, ValueError, KeyError, TypeError):
                    return self._send(503,{"error":"RECORDED_EVIDENCE_UNAVAILABLE"})
            if path == "/download":
                try:
                    fields = parse_qs(urlsplit(self.path).query, strict_parsing=True)
                    if set(fields) != {"scenario", "receipt_sha256", "choice"} or any(len(v) != 1 for v in fields.values()):
                        raise ValueError
                    fields = {key: value[0] for key, value in fields.items()}
                    review = run_scenario(fields["scenario"])
                    if fields["receipt_sha256"] != review["receipt_sha256"]:
                        raise ValueError
                    intent = None if fields["choice"] == "none" else decision_record(review, fields["choice"])
                    return self._send(200, {"review": review, "review_intent": intent}, filename=f'labrepair-{review["scenario"]}.json')
                except (ValueError, TypeError, KeyError, OSError, ScienceReviewError):
                    return self._send(422, {"error": "EXPORT_BINDING_INVALID"})
            return self._send(404, {"error": "NOT_FOUND"})

        def do_POST(self):
            expected_origin = f"http://127.0.0.1:{self.server.server_port}"
            if not self._local_host() or self.headers.get("Origin") != expected_origin:
                self._discard_small_body()
                return self._send(403, {"error": "LOCAL_ORIGIN_REQUIRED"})
            if self.headers.get("Transfer-Encoding") or self.headers.get("Content-Type") != "application/json":
                self._discard_small_body()
                return self._send(415, {"error": "BOUNDED_JSON_REQUIRED"})
            try:
                length = int(self.headers.get("Content-Length", "-1"))
            except ValueError:
                length = -1
            if not 0 < length <= MAX_BODY:
                self._discard_small_body()
                return self._send(413, {"error": "BODY_LIMIT"})
            try:
                data = json.loads(self.rfile.read(length), object_pairs_hook=unique_object)
                path = urlsplit(self.path).path
                if path == "/api/review" and isinstance(data, dict) and set(data) == {"scenario"}:
                    return self._send(200, run_scenario(data["scenario"]))
                if path == "/api/decision" and isinstance(data, dict) and set(data) == {"scenario", "receipt_sha256", "choice"}:
                    return self._send(200, decision_record(data, data["choice"]))
                return self._send(422, {"error": "INVALID_ACTION"})
            except (ValueError, TypeError, KeyError, OSError, ScienceReviewError):
                return self._send(422, {"error": "REVIEW_UNAVAILABLE_OR_INVALID"})

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8770)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("port must be between 1024 and 65535")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler())
    print(f"LabRepair synthetic review: http://127.0.0.1:{args.port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
