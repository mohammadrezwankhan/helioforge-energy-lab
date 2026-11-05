"""Exercise the acceptance snapshot boundary through real loopback HTTP requests."""

from __future__ import annotations

import gzip
import hashlib
import http.client
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

SERVER_SOURCE = Path(__file__).with_name("serve-acceptance.py")
POLICY = "default-src 'none'; script-src 'self'; style-src 'self'"
DOCUMENT = b"<!doctype html><title>Snapshot fixture</title>"


class AcceptanceServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.site = self.root / ".cloudflare/site"
        self.site.mkdir(parents=True)
        self.script = self.root / "scripts/serve-acceptance.py"
        self.script.parent.mkdir()
        shutil.copyfile(SERVER_SOURCE, self.script)
        (self.site / "_headers").write_text(f"/*\n  Content-Security-Policy: {POLICY}\n")
        (self.site / "index.html").write_bytes(DOCUMENT)
        (self.site / "run").mkdir()
        (self.site / "run/index.html").write_bytes(DOCUMENT)
        (self.site / "empty").mkdir()
        self.process: subprocess.Popen[bytes] | None = None
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            self.port = listener.getsockname()[1]
        self.log = self.root / "server.log"

    def stop_server(self) -> None:
        if self.process is not None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)

    def launch_server(self) -> subprocess.Popen[bytes]:
        with self.log.open("wb") as output:
            self.process = subprocess.Popen(  # noqa: S603 -- fixed Python and copied repository script, no shell.
                [sys.executable, str(self.script), "--port", str(self.port)],
                cwd=self.root,
                env={**os.environ, "HELIOFORGE_ACCEPTANCE_SITE": str(self.site)},
                stdout=output,
                stderr=subprocess.STDOUT,
            )
        self.addCleanup(self.stop_server)
        return self.process

    def start_server(self) -> None:
        process = self.launch_server()
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if process.poll() is not None:
                self.fail(f"Acceptance server exited during startup: {self.log.read_text()}")
            try:
                status, _, _ = self.request("/")
                if status == 200:
                    return
            except OSError:
                pass
            time.sleep(0.02)
        self.fail(f"Acceptance server did not become ready: {self.log.read_text()}")

    def assert_startup_rejected(self, reason: str) -> None:
        process = self.launch_server()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.fail("Acceptance server accepted an invalid snapshot")
        self.assertNotEqual(process.returncode, 0)
        self.assertIn(reason, self.log.read_text())

    def request(
        self, path: str, *, method: str = "GET", accept_encoding: str = "identity"
    ) -> tuple[int, dict[str, str], bytes]:
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            connection.request(method, path, headers={"Accept-Encoding": accept_encoding})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def test_directory_index_symlink_cannot_escape_the_site(self) -> None:
        outside = self.root / "private.html"
        outside.write_bytes(b"PRIVATE OUTSIDE THE SNAPSHOT")
        (self.site / "escape").mkdir()
        (self.site / "escape/index.html").symlink_to(outside)
        self.start_server()
        for path in ("/escape", "/escape/", "/escape/index.html"):
            with self.subTest(path=path):
                status, _, body = self.request(path)
                self.assertEqual(status, 404)
                self.assertNotIn(b"PRIVATE OUTSIDE THE SNAPSHOT", body)

    def test_file_and_directory_symlinks_are_not_routes(self) -> None:
        (self.site / "linked.html").symlink_to(self.site / "index.html")
        (self.site / "linked-directory").symlink_to(self.site / "run", target_is_directory=True)
        self.start_server()
        for path in ("/linked.html", "/linked-directory/", "/linked-directory/index.html"):
            with self.subTest(path=path):
                self.assertEqual(self.request(path)[0], 404)

    def test_snapshot_does_not_read_files_changed_after_startup(self) -> None:
        self.start_server()
        (self.site / "run/index.html").unlink()
        outside = self.root / "replacement.html"
        outside.write_bytes(b"PRIVATE POST-STARTUP REPLACEMENT")
        (self.site / "run/index.html").symlink_to(outside)
        (self.site / "new.txt").write_bytes(b"NOT PART OF THE SNAPSHOT")
        self.assertEqual(self.request("/run/")[2], DOCUMENT)
        self.assertEqual(self.request("/new.txt")[0], 404)

    def test_get_head_gzip_headers_and_directory_aliases(self) -> None:
        self.start_server()
        for path in ("/", "/index.html", "/run", "/run/", "/run/index.html", "/run/?case=1"):
            with self.subTest(path=path):
                status, headers, body = self.request(path)
                self.assertEqual((status, body), (200, DOCUMENT))
                self.assertEqual(headers["Content-Type"], "text/html; charset=utf-8")
                self.assertEqual(headers["Content-Length"], str(len(DOCUMENT)))
                self.assertEqual(headers["Content-Security-Policy"], POLICY)
                self.assertEqual(headers["ETag"], '"' + hashlib.sha256(DOCUMENT).hexdigest() + '"')
                self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
                self.assertEqual(headers["X-Frame-Options"], "DENY")
                self.assertEqual(headers["Cache-Control"], "public, max-age=60")
                self.assertEqual(headers["Vary"], "Accept-Encoding")
                self.assertEqual(headers.get("X-Robots-Tag"), "noindex, follow" if "/run" in path else None)
                head_status, head_headers, head_body = self.request(path, method="HEAD")
                self.assertEqual((head_status, head_body), (200, b""))
                for header in ("Content-Length", "Content-Type", "ETag", "Content-Security-Policy"):
                    self.assertEqual(head_headers[header], headers[header])
        status, headers, body = self.request("/run/", accept_encoding="gzip")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Encoding"], "gzip")
        self.assertEqual(headers["Content-Length"], str(len(body)))
        self.assertEqual(gzip.decompress(body), DOCUMENT)
        _, head_headers, head_body = self.request("/run/", method="HEAD", accept_encoding="gzip")
        self.assertEqual(head_body, b"")
        self.assertEqual(head_headers["Content-Length"], headers["Content-Length"])
        self.assertEqual(head_headers["ETag"], headers["ETag"])

    def test_private_missing_and_malformed_routes_are_denied(self) -> None:
        (self.root / "private.txt").write_bytes(b"PRIVATE OUTSIDE THE SNAPSHOT")
        self.start_server()
        for path in (
            "/_headers",
            "/missing",
            "/empty/",
            "/../../private.txt",
            "/%2e%2e/%2e%2e/private.txt",
            "/run/%00index.html",
            "/%0d%0aX-Injected%3A%20true",
        ):
            with self.subTest(path=path):
                status, headers, body = self.request(path)
                self.assertEqual(status, 404)
                self.assertNotIn("X-Injected", headers)
                self.assertNotIn(b"PRIVATE OUTSIDE THE SNAPSHOT", body)

    def test_generated_policy_with_control_characters_is_rejected(self) -> None:
        (self.site / "_headers").write_text("/*\n  Content-Security-Policy: default-src 'none'\x00\n")
        self.assert_startup_rejected("Snapshot headers must contain printable ASCII only")

    def test_symlinked_policy_is_rejected(self) -> None:
        outside = self.root / "external-headers"
        outside.write_text(f"/*\n  Content-Security-Policy: {POLICY}\n")
        (self.site / "_headers").unlink()
        (self.site / "_headers").symlink_to(outside)
        self.assert_startup_rejected("Acceptance headers must be a regular generated file")

    def test_oversize_snapshot_is_rejected_before_listening(self) -> None:
        with (self.site / "oversize.bin").open("wb") as oversized:
            oversized.truncate(129 * 1024 * 1024)
        self.assert_startup_rejected("Acceptance snapshot exceeds the 128 MiB limit")

    def test_site_outside_the_generated_directory_is_rejected(self) -> None:
        self.site = self.root
        self.assert_startup_rejected("Acceptance site must remain inside the generated .cloudflare directory")

    def test_data_and_unknown_extensions_retain_safe_metadata(self) -> None:
        (self.site / "data.json").write_bytes(b'{"fixture": true}')
        (self.site / "asset.fixtureunknown").write_bytes(b"\x00\xff\x01")
        self.start_server()
        _, headers, body = self.request("/data.json")
        self.assertEqual(body, b'{"fixture": true}')
        self.assertEqual(headers["Content-Type"], "application/json; charset=utf-8")
        _, headers, body = self.request("/asset.fixtureunknown")
        self.assertEqual(body, b"\x00\xff\x01")
        self.assertEqual(headers["Content-Type"], "application/octet-stream")


if __name__ == "__main__":
    unittest.main()
