"""Read exact publication endpoints and retain their HTTP evidence."""

import urllib.error
import urllib.request
from dataclasses import dataclass
from http.client import HTTPMessage
from typing import IO

PUBLICATION_ROUTES = ("app.json", "run/", "robots.txt", "sitemap.xml", "about/", "methodology/", "")


@dataclass(frozen=True)
class PublicationResponse:
    """The original status, headers and bytes of a publication observation."""

    status: int
    headers: dict[str, str]
    body: bytes


class PublicationRequest(urllib.request.Request):
    """Construct requests only for the seven reviewed HTTPS routes."""

    def __init__(self, route: str) -> None:
        if route not in PUBLICATION_ROUTES:
            raise ValueError("Publication route is not one of the reviewed endpoints")
        super().__init__("https://mkgrid.co.technology/" + route)


class NoPublicationRedirect(urllib.request.HTTPRedirectHandler):
    """Keep redirect responses as evidence without issuing another request."""

    def redirect_request(
        self,
        _request: urllib.request.Request,
        _response: IO[bytes],
        _code: int,
        _message: str,
        _headers: HTTPMessage,
        _new_url: str,
    ) -> None:
        return None


def fetch_publication_route(route: str) -> PublicationResponse:
    """Return HTTP errors as observations while propagating transport failures."""
    request = PublicationRequest(route)
    try:
        response = urllib.request.build_opener(NoPublicationRedirect()).open(request, timeout=30)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        return PublicationResponse(int(response.status), dict(response.headers), response.read())
