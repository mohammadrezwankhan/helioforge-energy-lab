"""Exercise fixed publication routes and real urllib redirect processing offline."""

import importlib
import io
import unittest
import urllib.request
import urllib.response
from email.message import Message
from unittest.mock import patch


class FixtureResponse(urllib.response.addinfourl):
    """Provide the status message consumed by urllib response processing."""

    msg = "Fixture"


class FixtureTransportHandler(urllib.request.BaseHandler):
    """Replace only the external transport, retaining urllib's response handlers."""

    handler_order = 100

    def __init__(self, status: int, location: str | None = None) -> None:
        super().__init__()
        self.status = status
        self.location = location
        self.requests: list[str] = []
        self.bodies: list[io.BytesIO] = []

    def https_open(self, request: urllib.request.Request) -> urllib.response.addinfourl:
        self.requests.append(request.full_url)
        if request.full_url != "https://mkgrid.co.technology/app.json":
            raise AssertionError("Publication transport followed an unexpected endpoint")
        headers = Message()
        headers["Content-Type"] = "application/json"
        if self.location is not None:
            headers["Location"] = self.location
        body = io.BytesIO(b'{"fixture": true}')
        self.bodies.append(body)
        return FixtureResponse(body, headers, request.full_url, self.status)

    def http_open(self, request: urllib.request.Request) -> urllib.response.addinfourl:
        return self.https_open(request)


class PublicationHttpTests(unittest.TestCase):
    def test_redirects_are_recorded_without_following_them(self) -> None:
        module = importlib.import_module("scripts.publication_http")
        original_build_opener = urllib.request.build_opener
        for location in [
            "https://untrusted.example/private",
            "http://127.0.0.1/private",
            "file:///private-placeholder",
            "https://mkgrid.co.technology/run/",
        ]:
            with self.subTest(location=location):
                handler = FixtureTransportHandler(302, location)
                with patch.object(
                    module.urllib.request,
                    "build_opener",
                    side_effect=lambda *handlers, fixture=handler: original_build_opener(*handlers, fixture),
                ):
                    response = module.fetch_publication_route("app.json")
                self.assertEqual(response.status, 302)
                self.assertEqual(response.headers["Location"], location)
                self.assertEqual(response.body, b'{"fixture": true}')
                self.assertEqual(handler.requests, ["https://mkgrid.co.technology/app.json"])
                self.assertTrue(all(body.closed for body in handler.bodies))

    def test_success_and_denial_preserve_exact_response_bytes(self) -> None:
        module = importlib.import_module("scripts.publication_http")
        original_build_opener = urllib.request.build_opener
        for status in [200, 403, 404]:
            with self.subTest(status=status):
                handler = FixtureTransportHandler(status)
                with patch.object(
                    module.urllib.request,
                    "build_opener",
                    side_effect=lambda *handlers, fixture=handler: original_build_opener(*handlers, fixture),
                ):
                    response = module.fetch_publication_route("app.json")
                self.assertEqual(response.status, status)
                self.assertEqual(response.body, b'{"fixture": true}')
                self.assertEqual(response.headers["Content-Type"], "application/json")
                self.assertTrue(all(body.closed for body in handler.bodies))

    def test_unreviewed_routes_are_rejected_before_transport(self) -> None:
        module = importlib.import_module("scripts.publication_http")
        for route in [
            "https://untrusted.example/",
            "//untrusted.example/",
            "file:///private-placeholder",
            "../private",
            "app.json?redirect=1",
            "app.json#fragment",
            "app.json\r\nInjected: value",
        ]:
            with self.subTest(route=route), self.assertRaises(ValueError):
                module.fetch_publication_route(route)


if __name__ == "__main__":
    unittest.main()
