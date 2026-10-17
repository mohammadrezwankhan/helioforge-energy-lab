import base64
import json
from datetime import datetime, timezone

import pytest

from helioforge.integrations import (
    DocumentImport,
    SeriesImport,
    TelemetryImport,
    extract_document,
    import_series,
    inspect_telemetry,
    parse_entsoe,
)


def test_series_requires_utc_order_finite_values_and_units():
    p = SeriesImport(text="timestamp,value\n2026-01-01T00:00:00Z,12\n2026-01-01T01:00:00Z,15", unit="EUR/MWh")
    r = import_series(p)
    assert r["values"] == [12, 15]
    assert r["interval_seconds"] == 3600
    assert r["data_kind"] == "user_supplied_unverified"
    for text in [
        "timestamp,value\n2026-01-01T00:00:00,12",
        "timestamp,value\n2026-01-01T00:00:00Z,nan",
        "timestamp,value\n2026-01-01T00:00:00Z,1\n2026-01-01T00:00:00Z,2",
    ]:
        with pytest.raises(ValueError):
            import_series(SeriesImport(text=text, unit="kW"))


def test_document_hash_and_extraction_never_proves_authenticity():
    text = "Manufacturer warranty: 6000 cycles; 80% retained capacity. Tariff EUR 0.15/kWh."
    r = extract_document(
        DocumentImport(filename="warranty.txt", content_base64=base64.b64encode(text.encode()).decode())
    )
    assert r["text"] == text
    assert r["authenticity"] == "unverified"
    assert any(x["category"] == "warranty" for x in r["extracted_candidates"])
    assert len(r["sha256"]) == 64
    with pytest.raises(ValueError):
        extract_document(DocumentImport(filename="../evil.exe", content_base64="!!!"))


def test_telemetry_stale_and_threshold_are_distinct():
    p = TelemetryImport(
        source="Test instrument",
        timestamp="2026-01-01T00:00:00Z",
        readings=[{"channel": "gas1", "value": 15, "unit": "ppm", "warning": 10, "critical": 20}],
    )
    r = inspect_telemetry(p, now=datetime(2026, 1, 1, 1, tzinfo=timezone.utc))
    assert r["stale"] is True
    assert r["readings"][0]["threshold_state"] == "warning"
    assert r["operational_alarm"] is False


def test_entsoe_preserves_quarter_hours_negative_prices_and_currency():
    raw = b"<Publication_MarketDocument><TimeSeries><currency_Unit.name>EUR</currency_Unit.name><price_Measure_Unit.name>MWH</price_Measure_Unit.name><Period><timeInterval><start>2026-01-01T00:00Z</start><end>2026-01-01T00:30Z</end></timeInterval><resolution>PT15M</resolution><Point><position>1</position><price.amount>-10</price.amount></Point><Point><position>2</position><price.amount>70</price.amount></Point></Period></TimeSeries></Publication_MarketDocument>"
    r = parse_entsoe(raw)
    assert [x["price_eur_mwh"] for x in r] == [-10, 70]
    assert r[1]["timestamp"] == "2026-01-01T00:15:00+00:00"
    with pytest.raises(ValueError):
        parse_entsoe(raw.replace(b"EUR", b"GBP"))
    with pytest.raises(ValueError):
        parse_entsoe(b'<!DOCTYPE x [<!ENTITY secret SYSTEM "file:///x">]><x/>')


def test_geographic_points_reject_unknown_and_nonfinite_coordinates():
    from helioforge.integrations import GeoImport, import_geography

    feature = {
        "type": "Feature",
        "properties": {"name": "Surveyed site"},
        "geometry": {"type": "Point", "coordinates": [2.3, 48.8]},
    }
    doc = {"type": "FeatureCollection", "features": [feature]}
    assert import_geography(GeoImport(geojson=doc))["rows"][0]["longitude"] == 2.3
    for coordinates in ([181, 48], [True, 48], [float("nan"), 48], [2, 95], [2, 48, 12]):
        feature["geometry"]["coordinates"] = coordinates
        with pytest.raises(ValueError):
            import_geography(GeoImport(geojson=doc))


def test_readonly_modbus_packet_and_response(monkeypatch):
    import struct

    from helioforge.integrations import ModbusRequest, modbus_read

    monkeypatch.setenv(
        "HELIOFORGE_MODBUS_DEVICES",
        json.dumps({"test": {"host": "configured.example", "count": 2, "address": 4, "function": 4}}),
    )

    class FakeSocket:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def sendall(self, raw):
            tx, proto, length, unit, fn, address, count = struct.unpack(">HHHBBHH", raw)
            assert (proto, length, unit, fn, address, count) == (0, 6, 1, 4, 4, 2)
            self.response = struct.pack(">HHHBBBHH", tx, 0, 7, unit, fn, 4, 15, 30)

        def recv(self, n):
            chunk = self.response[: min(n, 2)]
            self.response = self.response[len(chunk) :]
            return chunk

    monkeypatch.setattr(
        "helioforge.integrations.socket.create_connection", lambda *args, **kwargs: FakeSocket()
    )
    r = modbus_read(ModbusRequest(device="test"))
    assert [x["value"] for x in r["rows"]] == [15, 30]
    assert r["function"] == 4
    with pytest.raises(ValueError, match="allow-list"):
        modbus_read(ModbusRequest(device="other"))


def test_weather_request_hides_credential_and_preserves_missing_values(monkeypatch):
    import asyncio

    from helioforge.integrations import WeatherRequest, weather

    monkeypatch.setenv("OPEN_METEO_API_KEY", "do-not-expose")

    async def mock(url, params):
        assert url == "https://customer-api.open-meteo.com/v1/forecast"
        assert params["apikey"] == "do-not-expose"
        return json.dumps(
            {
                "hourly": {
                    "time": ["2026-01-01T00:00"],
                    "temperature_2m": [None],
                    "wind_speed_10m": [2.5],
                    "shortwave_radiation": [0],
                },
                "hourly_units": {},
            }
        ).encode()

    monkeypatch.setattr("helioforge.integrations.upstream", mock)
    r = asyncio.run(weather(WeatherRequest(consent=True)))
    assert r["rows"][0]["temperature_2m"] is None
    assert "do-not-expose" not in json.dumps(r)


def test_integrations_api_local_import_is_audited(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from helioforge.main import app

    monkeypatch.setenv("HELIOFORGE_DB", str(tmp_path / "db.sqlite3"))
    with TestClient(app, base_url="http://127.0.0.1") as c:
        r = c.post(
            "/api/evidence/series", json={"text": "timestamp,value\n2026-01-01T00:00:00Z,3", "unit": "kW"}
        )
        assert r.status_code == 200, r.text
        assert c.get("/api/runs/" + r.json()["run_id"]).json()["kind"] == "series_import"
        assert (
            c.post("/api/connectors/market", json={"market": "DE", "date": "2026-01-01"}).status_code == 403
        )
        status = c.get("/api/connectors/status").json()
        assert "key" not in json.dumps(status).lower().replace("api_key_configured", "")


def test_regulatory_atom_keeps_publication_separate_from_effective_date(monkeypatch):
    import asyncio

    from helioforge.integrations import RegulatoryRequest, regulatory_feed

    monkeypatch.setenv("HELIOFORGE_REGULATORY_FEEDS", '{"FR":"https://www.cre.fr/feed"}')
    raw = b"""<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Draft network consultation</title><link href="https://www.cre.fr/publication"/><updated>2026-10-01T08:00:00Z</updated><summary>Proposed consultation closes 2026-12-01</summary></entry><entry><title>Untrusted destination</title><link href="https://cre.fr.evil.example/page"/></entry></feed>"""

    async def mock(url, params):
        assert url == "https://www.cre.fr/feed"
        return raw

    monkeypatch.setattr("helioforge.integrations.upstream", mock)
    result = asyncio.run(regulatory_feed(RegulatoryRequest(consent=True)))
    assert len(result["rows"]) == 1
    row = result["rows"][0]
    assert row["published_at"] == "2026-10-01T08:00:00+00:00"
    assert row["effective_date_verified"] is False
    assert "2026-12-01" in row["date_candidates"]
    assert result["changed_since_previous"] is None
    repeated = asyncio.run(regulatory_feed(RegulatoryRequest(consent=True, previous_sha256=result["sha256"])))
    assert repeated["changed_since_previous"] is False


def test_regulatory_allowlist_and_missing_configuration_fail_closed(monkeypatch):
    import asyncio

    from helioforge.integrations import RegulatoryRequest, regulator_url, regulatory_feed

    for url in (
        "https://cre.fr.evil.example/feed",
        "http://cre.fr/feed",
        "https://user:pass@cre.fr/feed",
        "https://cre.fr:444/feed",
    ):
        assert regulator_url(url, "FR") is False
    monkeypatch.delenv("HELIOFORGE_REGULATORY_FEEDS", raising=False)
    with pytest.raises(ValueError, match="Configure an official regulator"):
        asyncio.run(regulatory_feed(RegulatoryRequest(consent=True)))
