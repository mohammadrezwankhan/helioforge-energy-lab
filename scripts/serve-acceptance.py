"""Loopback-only snapshot server with exact generated CSP, gzip and no directory listing."""
import argparse
import gzip
import hashlib
import mimetypes
import os
import ssl
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--port", type=int, default=4189)
parser.add_argument("--tls-cert", type=Path)
parser.add_argument("--tls-key", type=Path)
args = parser.parse_args()
site = Path(os.environ.get("HELIOFORGE_ACCEPTANCE_SITE", ROOT / ".cloudflare/site"))
if not site.resolve().is_relative_to((ROOT / ".cloudflare").resolve()):
    raise ValueError("Acceptance site must remain inside the generated .cloudflare directory")
policy = next(line.split(": ", 1)[1] for line in (site / "_headers").read_text().splitlines()
              if line.startswith("  Content-Security-Policy: "))


class Handler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.respond(False)

    def do_GET(self):
        self.respond(True)

    def respond(self, body):
        request_path = unquote(urlsplit(self.path).path)
        target = (site / request_path.lstrip("/")).resolve()
        if not target.is_relative_to(site.resolve()):
            self.send_error(404)
            return
        if target.is_dir():
            target /= "index.html"
        if not target.is_file() or target.name.startswith("_"):
            self.send_error(404)
            return
        data = target.read_bytes()
        compressed = "gzip" in self.headers.get("Accept-Encoding", "")
        encoded = gzip.compress(data, mtime=0) if compressed else data
        self.send_response(200)
        self.send_header("Content-Type", (mimetypes.guess_type(target.name)[0] or "application/octet-stream") +
                         ("; charset=utf-8" if target.suffix in {".html", ".css", ".js", ".json", ".txt"} else ""))
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Content-Security-Policy", policy)
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

    def log_message(self, fmt, *values):
        pass


server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
if args.tls_cert:
    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls.load_cert_chain(args.tls_cert, args.tls_key)
    server.socket = tls.wrap_socket(server.socket, server_side=True)
print(f"Local generated-site acceptance {'https' if args.tls_cert else 'http'}://127.0.0.1:{args.port}/run/; cache profile is laboratory-only", flush=True)
server.serve_forever()
