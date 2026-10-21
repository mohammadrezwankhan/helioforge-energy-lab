"""The upstream XML boundary rejects DTDs before any entity expansion."""

import pytest

from helioforge.integrations import xml_root


@pytest.mark.parametrize("encoding", ["utf-8", "utf-16", "utf-16le", "utf-16be"])
@pytest.mark.parametrize(
    "document",
    [
        "<!DOCTYPE feed><feed/>",
        '<!DOCTYPE feed [<!ENTITY audit "audit-entity-marker">]>'
        "<feed><entry><title>&audit;</title></entry></feed>",
        '<!DOCTYPE feed SYSTEM "https://example.invalid/audit.dtd"><feed/>',
    ],
    ids=["doctype", "internal-entity", "external-doctype"],
)
def test_upstream_xml_rejects_doctype_in_every_supported_encoding(encoding, document):
    # A byte-pattern check misses the NUL-interleaved declarations in UTF-16.
    # The tiny marker demonstrates expansion without a resource-exhaustion payload.
    with pytest.raises(ValueError, match="entities and document types are forbidden"):
        xml_root(document.encode(encoding))


@pytest.mark.parametrize("encoding", ["utf-8", "utf-16", "utf-16le", "utf-16be"])
def test_upstream_xml_preserves_safe_encodings_namespaces_and_character_references(encoding):
    document = (
        '<feed xmlns="http://www.w3.org/2005/Atom"><entry>'
        "<title>Research &amp; energy &#8364;</title></entry></feed>"
    )
    root = xml_root(document.encode(encoding))
    assert root.tag == "feed"
    assert root.findtext("entry/title") == "Research & energy €"


def test_upstream_xml_reports_malformed_input_without_parser_details():
    with pytest.raises(ValueError, match="^Upstream XML is invalid\\.$"):
        xml_root(b"<feed><entry></feed>")


def test_regulator_api_rejects_encoded_entities_without_saving_evidence(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from helioforge.main import app

    monkeypatch.setenv("HELIOFORGE_DB", str(tmp_path / "audit.sqlite3"))
    monkeypatch.setenv("HELIOFORGE_REGULATORY_FEEDS", '{"FR":"https://www.cre.fr/feed"}')
    document = (
        '<!DOCTYPE feed [<!ENTITY audit "audit-entity-marker">]>'
        "<feed><entry><title>&audit;</title>"
        "<link>https://www.cre.fr/publication</link></entry></feed>"
    )

    async def supplied_feed(url, params):
        # Substitute only the remote transport. The API, parser and store are real.
        return document.encode("utf-16")

    monkeypatch.setattr("helioforge.integrations.upstream", supplied_feed)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.post("/api/connectors/regulatory", json={"market": "FR", "consent": True})
        assert response.status_code == 422
        assert response.json() == {"detail": "XML entities and document types are forbidden."}
        assert client.get("/api/runs").json() == []
