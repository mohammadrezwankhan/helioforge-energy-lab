"""Focused offline tests for the published-release verifier's pure helpers."""
from __future__ import annotations

import gzip
import hashlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
import zlib
from contextlib import redirect_stdout
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread
from unittest import mock

SCRIPT = Path(__file__).with_name("verify-published-release.py")
SPEC = importlib.util.spec_from_file_location("verify_published_release", SCRIPT)
assert SPEC and SPEC.loader
VERIFY = importlib.util.module_from_spec(SPEC)
sys.dont_write_bytecode = True
SPEC.loader.exec_module(VERIFY)


class DecodeBodyTests(unittest.TestCase):
    def test_identity_and_gzip_content_encoding(self) -> None:
        body = b"release bytes\x00with exact content"
        self.assertEqual(VERIFY.decode_http_body(body, "identity"), body)
        self.assertEqual(VERIFY.decode_http_body(gzip.compress(body), "gzip"), body)

    def test_zlib_and_raw_deflate_content_encoding(self) -> None:
        body = b"deflate body payload" * 8
        self.assertEqual(VERIFY.decode_http_body(zlib.compress(body), "deflate"), body)
        raw = zlib.compressobj(wbits=-zlib.MAX_WBITS)
        self.assertEqual(VERIFY.decode_http_body(raw.compress(body) + raw.flush(), "deflate"), body)

    def test_unknown_content_encoding_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported HTTP content encoding"):
            VERIFY.decode_http_body(b"payload", "br")


class RouteAndCspTests(unittest.TestCase):
    def test_site_file_route_mapping(self) -> None:
        self.assertEqual(VERIFY.route_for_site_file("index.html"), "/")
        self.assertEqual(VERIFY.route_for_site_file("about/index.html"), "/about/")
        self.assertEqual(VERIFY.route_for_site_file("learning/model-glossary/index.html"),
                         "/learning/model-glossary/")
        self.assertEqual(VERIFY.route_for_site_file("run/data/file name.json"), "/run/data/file%20name.json")
        self.assertIsNone(VERIFY.route_for_site_file("_headers"))
        self.assertIsNone(VERIFY.route_for_site_file("_redirects"))
        self.assertIsNone(VERIFY.route_for_site_file("404.html"))

    def test_inline_script_hash_uses_exact_script_text(self) -> None:
        html = '<link rel="canonical" href="https://example.test/"><script>window.x = 1;</script>'
        page = VERIFY.PageFactsParser()
        page.feed(html)
        self.assertEqual(page.canonicals, ["https://example.test/"])
        digest = __import__("base64").b64encode(hashlib.sha256(b"window.x = 1;").digest()).decode("ascii")
        self.assertEqual(VERIFY.inline_csp_tokens(page), ["'sha256-" + digest + "'"])


class SourceIdentityTests(unittest.TestCase):
    def test_source_identity_requires_clean_exact_sha1_binding(self) -> None:
        commit = "a" * 40
        receipt = {"source_base_commit": commit, "working_tree_dirty": False}
        facts = {"sourceRevision": commit, "sourceTreeDirty": False}
        self.assertEqual(VERIFY.source_identity_check(facts, receipt)["status"], "PASS")
        self.assertEqual(VERIFY.source_identity_check({**facts, "sourceTreeDirty": True}, receipt)["status"], "FAIL")
        self.assertEqual(VERIFY.source_identity_check(facts, {**receipt, "source_base_commit": None})["status"], "FAIL")


class MainStatusTests(unittest.TestCase):
    def test_execution_error_after_valid_preflight_cannot_report_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            site = root / "site"
            site.mkdir()
            receipt_path = root / "receipt.json"
            receipt_path.write_text("{}", encoding="utf-8")
            out = root / "evidence"
            app_facts = {"runtimeSha256": hashlib.sha256(b"runtime").hexdigest()}
            files = {"app.json": json.dumps(app_facts).encode("utf-8"), "run/index.html": b"runtime"}
            receipt = {"source_base_commit": "a" * 40, "working_tree_dirty": False,
                       "ci_run_id": "123", "ci_attempt": "1"}
            preflight = [VERIFY.check("fixture_preflight", True, True, True)]
            stdout = io.StringIO()
            with mock.patch.object(VERIFY, "check_receipt", return_value=(preflight, receipt, files)), \
                    mock.patch.object(VERIFY, "verify_release", side_effect=RuntimeError("fixture HTTP failure")), \
                    redirect_stdout(stdout):
                result = VERIFY.main(["--base-url", "https://example.test", "--site", str(site),
                                      "--receipt", str(receipt_path), "--out", str(out)])
            report = json.loads((out / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(result, 1)
            self.assertEqual(report["status"], "FAIL")
            self.assertIn("fixture HTTP failure", report["execution_error"])


class HttpBoundaryTests(unittest.TestCase):
    def test_public_403_is_saved_and_raises_blocked(self) -> None:
        class DenyHandler(BaseHTTPRequestHandler):
            requests = 0
            user_agent = ""

            def do_GET(self) -> None:
                type(self).requests += 1
                type(self).user_agent = self.headers.get("User-Agent", "")
                self.send_response(403)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(b"ordinary access denied")

            def log_message(self, format: str, *args: object) -> None:
                return

        server = HTTPServer(("127.0.0.1", 0), DenyHandler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as temp:
                client = VERIFY.HttpClient(f"http://127.0.0.1:{server.server_port}", Path(temp), 2)
                with self.assertRaises(VERIFY.Blocked) as caught:
                    client.get(client.origin + "/", "403-fixture")
                self.assertEqual(DenyHandler.requests, 1)
                self.assertEqual(DenyHandler.user_agent,
                                 "HelioForge-Release-Verification/1.0 (+https://github.com/mohammadrezwankhan/helioforge-energy-lab)")
                self.assertEqual(caught.exception.records[0]["status"], 403)
                self.assertEqual((Path(temp) / caught.exception.records[0]["body_file"]).read_bytes(), b"ordinary access denied")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
