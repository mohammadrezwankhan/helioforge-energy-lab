"""A local readiness response cannot redirect the launcher to another service."""

import importlib.util
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import build_opener

import pytest


def test_health_opener_does_not_follow_a_local_redirect() -> None:
    path = Path(__file__).resolve().parents[3] / "launch.py"
    spec = importlib.util.spec_from_file_location("launcher_redirect_contract", path)
    assert spec is not None and spec.loader is not None
    launcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(launcher)
    contacted: list[str] = []

    class Destination(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            contacted.append(self.path)
            self.send_response(200)
            self.end_headers()

        def log_message(self, _format: str, *_args: object) -> None:
            pass

    destination = ThreadingHTTPServer(("127.0.0.1", 0), Destination)

    class Redirect(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(302)
            self.send_header("Location", f"http://127.0.0.1:{destination.server_port}/unexpected")
            self.end_headers()

        def log_message(self, _format: str, *_args: object) -> None:
            pass

    redirect = ThreadingHTTPServer(("127.0.0.1", 0), Redirect)
    threads = [
        threading.Thread(target=server.serve_forever, daemon=True) for server in (destination, redirect)
    ]
    for thread in threads:
        thread.start()
    try:
        opener = build_opener(launcher._NoHealthRedirect())
        with pytest.raises(HTTPError) as caught:
            opener.open(f"http://127.0.0.1:{redirect.server_port}/api/health", timeout=2)
        assert caught.value.code == 302
        assert contacted == []
    finally:
        for server in (redirect, destination):
            server.shutdown()
            server.server_close()
        for thread in threads:
            thread.join(timeout=2)
            assert not thread.is_alive()
