"""Loopback-only snapshot server with generated CSP, gzip and no directory listing.

Load at most 128 MiB from a trusted, stable generated tree; restart after a rebuild.
Symlinks are excluded. HTTP requests only select immutable in-memory assets.
"""

import argparse
import gzip
import hashlib
import mimetypes
import os
import ssl
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import MappingProxyType
from typing import NamedTuple
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
# Keep the local acceptance snapshot bounded; restart after rebuilding its files.
MAX_SNAPSHOT_BYTES = 128 * 1024 * 1024


class SnapshotAsset(NamedTuple):
    data: bytes
    content_type: str
    etag: str


def header_value(value: str) -> str:
    if not value or any(not 32 <= ord(character) <= 126 for character in value):
        raise ValueError("Snapshot headers must contain printable ASCII only")
    return value


def load_snapshot(directory: Path) -> MappingProxyType[str, SnapshotAsset]:
    """Read a trusted generated tree once, before accepting any HTTP requests."""
    routes: dict[str, SnapshotAsset] = {}
    total = 0
    for target in sorted(directory.rglob("*")):
        # rglob does not descend into directory symlinks; never serve file links.
        if target.is_symlink() or not target.is_file() or target.name.startswith("_"):
            continue
        if not target.resolve().is_relative_to(directory):
            raise ValueError("Snapshot entry escaped the generated site")
        with target.open("rb") as source:
            data = source.read(MAX_SNAPSHOT_BYTES - total + 1)
        total += len(data)
        if total > MAX_SNAPSHOT_BYTES:
            raise ValueError("Acceptance snapshot exceeds the 128 MiB limit")
        content_type = header_value(
            (mimetypes.guess_type(target.name)[0] or "application/octet-stream")
            + ("; charset=utf-8" if target.suffix in {".html", ".css", ".js", ".json", ".txt"} else "")
        )
        asset = SnapshotAsset(data, content_type, '"' + hashlib.sha256(data).hexdigest() + '"')
        route = "/" + target.relative_to(directory).as_posix()
        routes[route] = asset
        if target.name == "index.html":
            alias = route.removesuffix("index.html")
            routes[alias] = asset
            if alias != "/":
                routes[alias.rstrip("/")] = asset
    return MappingProxyType(routes)


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--port", type=int, default=4189)
parser.add_argument("--tls-cert", type=Path)
parser.add_argument("--tls-key", type=Path)
args = parser.parse_args()
site = Path(os.environ.get("HELIOFORGE_ACCEPTANCE_SITE", ROOT / ".cloudflare/site")).resolve()
if not site.is_relative_to((ROOT / ".cloudflare").resolve()):
    raise ValueError("Acceptance site must remain inside the generated .cloudflare directory")
headers_file = site / "_headers"
if headers_file.is_symlink() or not headers_file.is_file():
    raise ValueError("Acceptance headers must be a regular generated file")
policy = header_value(
    next(
        line.split(": ", 1)[1]
        for line in headers_file.read_text().splitlines()
        if line.startswith("  Content-Security-Policy: ")
    )
)
snapshot = load_snapshot(site)


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
        asset = snapshot.get(request_path)
        if asset is None:
            self.send_error(404)
            return
        compressed = "gzip" in self.headers.get("Accept-Encoding", "")
        encoded = gzip.compress(asset.data, mtime=0) if compressed else asset.data
        self.send_response(200)
        self.send_header("Content-Type", asset.content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Content-Security-Policy", policy)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Cache-Control", "public, max-age=60")
        self.send_header("ETag", asset.etag)
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


server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
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
