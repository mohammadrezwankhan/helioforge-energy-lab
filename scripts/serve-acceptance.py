"""Loopback-only snapshot server with exact generated CSP, gzip and no directory listing."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import os
import ssl
from collections.abc import Mapping
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import MappingProxyType
from typing import NamedTuple
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
# The reviewed export has 364 files / 42,118,307 bytes, including its offline copy.
# Reject oversized payload and entry inventories before opening the listener.
MAX_SNAPSHOT_ENTRIES = 4096
MAX_SNAPSHOT_BYTES = 128 * 1024 * 1024
CONTENT_TYPES = {
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
}


class Asset(NamedTuple):
    data: bytes
    content_type: str


class Snapshot(NamedTuple):
    routes: Mapping[str, Asset]
    policy: str


def has_control_characters(value: str) -> bool:
    return any(ord(character) < 32 or ord(character) == 127 for character in value)


def load_snapshot(site: Path) -> Snapshot:
    """Freeze a completed local export; its producer must remain stopped during loading."""
    site = site.resolve()
    if not site.is_relative_to((ROOT / ".cloudflare").resolve()):
        raise ValueError("Acceptance site must remain inside the generated .cloudflare directory")
    routes: dict[str, Asset] = {}
    policy: str | None = None
    total_bytes = 0
    entries = 0
    for directory, directories, filenames in os.walk(site, followlinks=False):
        entries += len(directories) + len(filenames)
        if entries > MAX_SNAPSHOT_ENTRIES:
            raise ValueError("Acceptance snapshot entry limit exceeded")
        directories[:] = [
            name
            for name in directories
            if not (Path(directory) / name).is_symlink() and not has_control_characters(name)
        ]
        for name in filenames:
            target = Path(directory) / name
            if target.is_symlink() or not target.is_file() or has_control_characters(name):
                continue
            relative = target.relative_to(site)
            is_policy = relative.as_posix() == "_headers"
            if name.startswith("_") and not is_policy:
                continue
            if not target.resolve().is_relative_to(site):
                raise ValueError("Acceptance snapshot contains an escaping path")
            remaining = MAX_SNAPSHOT_BYTES - total_bytes
            if target.stat().st_size > remaining:
                raise ValueError("Acceptance snapshot byte limit exceeded")
            with target.open("rb") as source:
                data = source.read(remaining + 1)
            total_bytes += len(data)
            if total_bytes > MAX_SNAPSHOT_BYTES:
                raise ValueError("Acceptance snapshot byte limit exceeded")
            if is_policy:
                policy = next(
                    line.split(": ", 1)[1]
                    for line in data.decode("utf-8").splitlines()
                    if line.startswith("  Content-Security-Policy: ")
                )
                if has_control_characters(policy):
                    raise ValueError("Acceptance CSP contains a control character")
                continue
            asset = Asset(data, CONTENT_TYPES.get(target.suffix, "application/octet-stream"))
            route = "/" + relative.as_posix()
            routes[route] = asset
            if name == "index.html":
                directory_route = route.removesuffix("index.html")
                routes[directory_route] = asset
                if directory_route != "/":
                    routes[directory_route.removesuffix("/")] = asset
    if policy is None:
        raise ValueError("Acceptance snapshot requires its generated CSP headers")
    return Snapshot(MappingProxyType(routes), policy)


def make_handler(snapshot: Snapshot) -> type[BaseHTTPRequestHandler]:
    """Select only immutable startup records; request text never reaches file I/O."""

    class Handler(BaseHTTPRequestHandler):
        def do_HEAD(self) -> None:
            self.respond(False)

        def do_GET(self) -> None:
            self.respond(True)

        def respond(self, body: bool) -> None:
            try:
                request_path = unquote(urlsplit(self.path).path)
            except ValueError:
                self.send_error(404)
                return
            asset = snapshot.routes.get(request_path)
            if asset is None:
                self.send_error(404)
                return
            data = asset.data
            compressed = "gzip" in self.headers.get("Accept-Encoding", "")
            encoded = gzip.compress(data, mtime=0) if compressed else data
            self.send_response(200)
            self.send_header("Content-Type", asset.content_type)
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Content-Security-Policy", snapshot.policy)
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Cache-Control", "public, max-age=60")
            self.send_header("ETag", '"' + hashlib.sha256(data).hexdigest() + '"')
            self.send_header("Vary", "Accept-Encoding")
            if request_path.startswith("/run"):
                self.send_header("X-Robots-Tag", "noindex, follow")
            if compressed:
                self.send_header("Content-Encoding", "gzip")
            self.end_headers()
            if body:
                self.wfile.write(encoded)

        def log_message(self, _fmt: str, *_values: object) -> None:
            pass

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=4189)
    parser.add_argument("--tls-cert", type=Path)
    parser.add_argument("--tls-key", type=Path)
    args = parser.parse_args()
    site = Path(os.environ.get("HELIOFORGE_ACCEPTANCE_SITE", ROOT / ".cloudflare/site"))
    snapshot = load_snapshot(site)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(snapshot))
    if args.tls_cert:
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.minimum_version = ssl.TLSVersion.TLSv1_2
        tls.load_cert_chain(args.tls_cert, args.tls_key)
        server.socket = tls.wrap_socket(server.socket, server_side=True)
    print(  # noqa: T201 -- CLI report output.
        (
            "Local generated-site acceptance "
            f"{('https' if args.tls_cert else 'http')}"
            "://127.0.0.1:"
            f"{args.port}"
            "/run/; cache profile is laboratory-only"
        ),
        flush=True,
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
