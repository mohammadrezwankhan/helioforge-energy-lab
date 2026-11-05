"""Real HTTP regression controls for the generated-site acceptance server."""

from __future__ import annotations

import gzip
import hashlib
import io
import os
import runpy
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from unittest.mock import patch

SCRIPT = Path(__file__).with_name("serve-acceptance.py")
ROOT = SCRIPT.parents[1]
POLICY = "default-src 'none'; script-src 'self'; style-src 'self'; base-uri 'none'"
HTML = b"<!doctype html><title>Generated snapshot</title>"


class AcceptanceServerTests(unittest.TestCase):
    def setUp(self) -> None:
        cloudflare = ROOT / ".cloudflare"
        cloudflare.mkdir(exist_ok=True)
        temporary = tempfile.TemporaryDirectory(prefix="server-test-", dir=cloudflare)
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.site = self.directory / "site"
        self.site.mkdir()
        (self.site / "_headers").write_text(f"/*\n  Content-Security-Policy: {POLICY}\n", encoding="utf-8")
        (self.site / "index.html").write_bytes(HTML)
        (self.site / "run").mkdir()
        (self.site / "run/index.html").write_bytes(HTML)
        self.secret = self.directory / "outside.txt"
        self.secret.write_bytes(b"outside the approved generated site")

    def start_server(self) -> ThreadingHTTPServer:
        captured: list[ThreadingHTTPServer] = []

        def capture_server(
            address: tuple[str, int], handler: type[BaseHTTPRequestHandler]
        ) -> ThreadingHTTPServer:
            server = ThreadingHTTPServer(address, handler)
            captured.append(server)
            self.addCleanup(server.server_close)
            return server

        # Only pause the blocking CLI loop; requests use the actual handler,
        # real filesystem snapshot and real loopback HTTP server below.
        with (
            patch("http.server.ThreadingHTTPServer", new=capture_server),
            patch.object(ThreadingHTTPServer, "serve_forever", return_value=None),
            patch.object(sys, "argv", [str(SCRIPT), "--port", "0"]),
            patch.dict(os.environ, {"HELIOFORGE_ACCEPTANCE_SITE": str(self.site)}),
            redirect_stdout(io.StringIO()),
        ):
            runpy.run_path(str(SCRIPT), run_name="__main__")
        server = captured[0]
        thread = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 5)
        self.addCleanup(server.shutdown)
        return server

    def request(
        self,
        server: ThreadingHTTPServer,
        path: str,
        *,
        method: str = "GET",
        encoding: str = "identity",
    ) -> tuple[int, dict[str, str], bytes]:
        connection = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        try:
            connection.request(method, path, headers={"Accept-Encoding": encoding})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def test_directory_index_symlink_cannot_escape_the_site(self) -> None:
        (self.site / "escape").mkdir()
        (self.site / "escape/index.html").symlink_to(self.secret)
        server = self.start_server()
        for route in ("/escape", "/escape/", "/escape/index.html"):
            with self.subTest(route=route):
                status, _, data = self.request(server, route)
                self.assertEqual(status, 404)
                self.assertNotIn(self.secret.read_bytes(), data)

    def test_requests_cannot_read_files_changed_after_startup(self) -> None:
        asset = self.site / "asset.txt"
        asset.write_bytes(b"approved immutable snapshot")
        server = self.start_server()
        asset.unlink()
        asset.symlink_to(self.secret)
        status, _, data = self.request(server, "/asset.txt")
        self.assertEqual(status, 200)
        self.assertEqual(data, b"approved immutable snapshot")

    def test_requests_use_the_snapshot_without_opening_files(self) -> None:
        server = self.start_server()
        with patch.object(Path, "open", side_effect=AssertionError("request-time file read")):
            status, _, data = self.request(server, "/run/")
            self.assertEqual(status, 200)
            self.assertEqual(data, HTML)
            missing_status, _, _ = self.request(server, "/../outside.txt")
            self.assertEqual(missing_status, 404)

    def test_control_characters_do_not_become_routes_or_headers(self) -> None:
        (self.site / "payload\r\nX-Injected: yes.txt").write_bytes(b"untrusted filename")
        server = self.start_server()
        status, headers, _ = self.request(server, "/payload%0D%0AX-Injected:%20yes.txt")
        self.assertEqual(status, 404)
        self.assertNotIn("X-Injected", headers)

    def test_traversal_symlinks_private_files_and_directory_listing_are_rejected(self) -> None:
        (self.site / "linked").symlink_to(self.directory, target_is_directory=True)
        (self.site / "empty").mkdir()
        (self.site / "_private.txt").write_bytes(b"private metadata")
        server = self.start_server()
        for route in (
            "/../outside.txt",
            "/%2e%2e/outside.txt",
            "/%2e%2e%2foutside.txt",
            "/linked/outside.txt",
            "/empty/",
            "/_headers",
            "/_private.txt",
            "/missing",
        ):
            with self.subTest(route=route):
                status, _, data = self.request(server, route)
                self.assertEqual(status, 404)
                self.assertNotIn(self.secret.read_bytes(), data)

    def test_index_aliases_preserve_body_csp_and_cache_headers(self) -> None:
        server = self.start_server()
        for route in ("/", "/index.html", "/run", "/run/", "/run/index.html?case=1"):
            with self.subTest(route=route):
                status, headers, data = self.request(server, route)
                self.assertEqual(status, 200)
                self.assertEqual(data, HTML)
                self.assertEqual(headers["Content-Type"], "text/html; charset=utf-8")
                self.assertEqual(headers["Content-Length"], str(len(HTML)))
                self.assertEqual(headers["Content-Security-Policy"], POLICY)
                self.assertEqual(headers["ETag"], '"' + hashlib.sha256(HTML).hexdigest() + '"')
                self.assertEqual(headers["Cache-Control"], "public, max-age=60")
                self.assertEqual(headers["Vary"], "Accept-Encoding")
                self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
                self.assertEqual(headers["X-Frame-Options"], "DENY")
                self.assertEqual(
                    headers.get("X-Robots-Tag"), "noindex, follow" if route.startswith("/run") else None
                )

    def test_head_and_gzip_preserve_exact_representation_metadata(self) -> None:
        server = self.start_server()
        status, headers, compressed = self.request(server, "/run/", encoding="gzip")
        self.assertEqual(status, 200)
        self.assertEqual(compressed, gzip.compress(HTML, mtime=0))
        self.assertEqual(gzip.decompress(compressed), HTML)
        self.assertEqual(headers["Content-Encoding"], "gzip")
        self.assertEqual(headers["Content-Length"], str(len(compressed)))
        head_status, head_headers, body = self.request(server, "/run/", method="HEAD", encoding="gzip")
        self.assertEqual(head_status, 200)
        self.assertEqual(body, b"")
        for name in ("Content-Type", "Content-Length", "Content-Encoding", "Content-Security-Policy", "ETag"):
            self.assertEqual(head_headers[name], headers[name])

    def test_oversized_snapshot_fails_before_listening(self) -> None:
        with (self.site / "too-large.bin").open("wb") as asset:
            asset.truncate(128 * 1024 * 1024 + 1)
        with self.assertRaisesRegex(ValueError, "snapshot.*limit"):
            self.start_server()

    def test_generated_asset_types_and_nested_index_routes_are_preserved(self) -> None:
        expected_types = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "text/javascript; charset=utf-8",
            ".json": "application/json; charset=utf-8",
            ".txt": "text/plain; charset=utf-8",
            ".svg": "image/svg+xml",
            ".xml": "application/xml",
            ".png": "image/png",
            ".mp4": "video/mp4",
            ".md": "text/markdown",
            ".unknown": "application/octet-stream",
            "": "application/octet-stream",
        }
        for extension in expected_types:
            (self.site / ("asset" + extension)).write_bytes(b"exact asset bytes")
        (self.site / "chapter/deep").mkdir(parents=True)
        (self.site / "chapter/deep/index.html").write_bytes(HTML)
        server = self.start_server()
        for extension, content_type in expected_types.items():
            with self.subTest(extension=extension):
                status, headers, data = self.request(server, "/asset" + extension)
                self.assertEqual(status, 200)
                self.assertEqual(data, b"exact asset bytes")
                self.assertEqual(headers["Content-Type"], content_type)
        for route in ("/chapter/deep", "/chapter/deep/", "/chapter/deep/index.html"):
            with self.subTest(route=route):
                status, _, data = self.request(server, route)
                self.assertEqual(status, 200)
                self.assertEqual(data, HTML)

    def test_entry_limit_fails_before_listening(self) -> None:
        for index in range(4097):
            (self.site / f"asset-{index}.txt").touch()
        with self.assertRaisesRegex(ValueError, "snapshot.*limit"):
            self.start_server()

    def test_import_does_not_parse_cli_arguments_or_open_a_listener(self) -> None:
        output = io.StringIO()
        with (
            patch.object(sys, "argv", ["unrelated-program", "--unrelated-option"]),
            patch("http.server.ThreadingHTTPServer", side_effect=AssertionError("listener opened on import")),
            redirect_stdout(output),
        ):
            runpy.run_path(str(SCRIPT), run_name="acceptance_server_import")
        self.assertEqual(output.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
