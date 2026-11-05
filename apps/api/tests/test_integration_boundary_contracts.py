"""Malformed imports and controlled upstream failures never become fabricated evidence."""

import asyncio
import base64
import hashlib
import json
import shutil
import socket
import struct
import subprocess
from collections.abc import AsyncIterator, Callable
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Self

import httpx
import pytest

from helioforge import integrations


@pytest.mark.parametrize(
    "text,message",
    [
        ("value,timestamp\n1,2026-01-01T00:00Z", "CSV columns must be exactly"),
        ("timestamp,value\n", "at least one data row"),
        ("timestamp,value\n2026-01-01T00:00Z", "complete rows"),
        ("timestamp,value\n2026-01-01T00:00Z,1,extra", "complete rows"),
        ("timestamp,value\nnot-a-date,1", "ISO 8601"),
        ("timestamp,value\n2026-01-01T00:00Z,1000000000001", "finite and within"),
    ],
)
def test_series_rejects_ambiguous_columns_incomplete_rows_and_invalid_values(text: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        integrations.import_series(integrations.SeriesImport(text=text, unit="kW"))


def test_series_limit_rejects_the_20001st_complete_observation() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    text = "timestamp,value\n" + "\n".join(
        f"{(start + timedelta(seconds=index)).isoformat()},1" for index in range(20_001)
    )
    with pytest.raises(ValueError, match="at most 20000 complete rows"):
        integrations.import_series(integrations.SeriesImport(text=text, unit="kW"))


def test_irregular_series_preserves_gaps_without_imputation() -> None:
    result = integrations.import_series(
        integrations.SeriesImport(
            text="timestamp,value\n2026-01-01T01:00+01:00,3\n2026-01-01T01:00Z,4\n2026-01-01T03:00Z,5",
            unit="kWh",
        )
    )
    assert result["values"] == [3, 4, 5]
    assert result["rows"][0]["timestamp"] == "2026-01-01T00:00:00+00:00"
    assert result["regular"] is False
    assert result["gaps_or_irregular_intervals"] is True
    assert result["interval_seconds"] is None
    assert result["missing_values_imputed"] == 0


@pytest.mark.parametrize(
    "features,message",
    [
        ([], "FeatureCollection"),
        ([None], "GeoJSON Feature"),
        ([{"type": "Point"}], "GeoJSON Feature"),
        ([{"type": "Feature", "geometry": []}], "coordinates must be"),
        (
            [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [2, 48]}, "properties": [1]}],
            "primitive asset properties",
        ),
        (
            [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [2, 48]},
                    "properties": {"nested": {"name": "not primitive"}},
                }
            ],
            "primitive asset properties",
        ),
    ],
)
def test_geography_rejects_invalid_feature_and_property_shapes(features: object, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        integrations.import_geography(
            integrations.GeoImport(geojson={"type": "FeatureCollection", "features": features})
        )


@pytest.mark.parametrize(
    "name,raw,message",
    [
        ("source.txt", b"\xff", "UTF-8 encoded"),
        ("source.pdf", b"plain text", "PDF signature is missing"),
        ("source.exe", b"unsupported", "Supported documents"),
        ("source.txt", b" \n\t", "no usable text"),
        pytest.param("source.txt", b"x" * 200_001, "no usable text", id="text-size-bound"),
        pytest.param("source.txt", b"x" * 700_001, "700000 bytes", id="decoded-size-bound"),
    ],
)
def test_document_rejects_invalid_encoding_format_and_content_bounds(
    name: str, raw: bytes, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        integrations.extract_document(
            integrations.DocumentImport(filename=name, content_base64=base64.b64encode(raw).decode("ascii"))
        )


def test_unavailable_native_parser_reports_that_no_extraction_occurred(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    with pytest.raises(ValueError, match="no extraction was performed"):
        integrations.extract_document(
            integrations.DocumentImport(filename="source.png", content_base64="aW1hZ2U=")
        )


@pytest.mark.parametrize("output_size", [None, 200_001])
def test_native_parser_must_produce_bounded_text_and_cleans_temporary_input(
    monkeypatch: pytest.MonkeyPatch, output_size: int | None
) -> None:
    sources: list[Path] = []

    def run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[bytes]:
        sources.append(Path(command[7]))
        if output_size is not None:
            Path(command[8]).write_bytes(b"x" * output_size)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(shutil, "which", lambda _name: "/local-fixture/pdftotext")
    monkeypatch.setattr(subprocess, "run", run)
    with pytest.raises(ValueError, match="Extracted text is missing or exceeds"):
        integrations.extract_document(
            integrations.DocumentImport(filename="source.pdf", content_base64="JVBERi0xLjQ=")
        )
    assert len(sources) == 1
    assert not sources[0].exists()


def test_telemetry_rejects_future_and_duplicate_channels_and_retains_alarm_scope() -> None:
    reading = integrations.Reading(channel="sensor", value=85, unit="ppm")
    with pytest.raises(ValueError, match="warning threshold must be below"):
        integrations.Reading(channel="sensor", value=1, unit="ppm", warning=80, critical=80)
    now = datetime(2026, 1, 1, tzinfo=UTC)
    with pytest.raises(ValueError, match="future by more than 30 seconds"):
        integrations.inspect_telemetry(
            integrations.TelemetryImport(
                source="local fixture", timestamp="2026-01-01T00:00:31Z", readings=[reading]
            ),
            now=now,
        )
    with pytest.raises(ValueError, match="channels must be unique"):
        integrations.inspect_telemetry(
            integrations.TelemetryImport(
                source="local fixture", timestamp="2026-01-01T00:00:00Z", readings=[reading, reading]
            ),
            now=now,
        )
    result = integrations.inspect_telemetry(
        integrations.TelemetryImport(
            source="local fixture", timestamp="2026-01-01T00:00:30Z", readings=[reading]
        ),
        now=now,
    )
    assert result["age_seconds"] == -30
    assert result["stale"] is False
    assert result["readings"][0]["threshold_state"] == "critical"
    assert result["operational_alarm"] is False


class FixtureStream(httpx.AsyncByteStream):
    def __init__(self, chunks: list[bytes]) -> None:
        self.chunks = chunks

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for chunk in self.chunks:
            yield chunk


def controlled_http(
    monkeypatch: pytest.MonkeyPatch, handler: Callable[[httpx.Request], httpx.Response]
) -> None:
    real_client = httpx.AsyncClient

    def client(*, timeout: float, follow_redirects: bool, trust_env: bool) -> httpx.AsyncClient:
        assert timeout == 15
        assert follow_redirects is False
        assert trust_env is False
        return real_client(
            timeout=timeout,
            follow_redirects=follow_redirects,
            trust_env=trust_env,
            transport=httpx.MockTransport(handler),
        )

    monkeypatch.setattr(httpx, "AsyncClient", client)


@pytest.mark.parametrize("size", [2_000_000, 2_000_001])
def test_upstream_stream_is_bounded_before_evidence_is_returned(
    monkeypatch: pytest.MonkeyPatch, size: int
) -> None:
    def response(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://fixture.invalid/feed?query=local"
        return httpx.Response(200, stream=FixtureStream([b"x" * 1_000_000, b"y" * (size - 1_000_000)]))

    controlled_http(monkeypatch, response)
    operation = integrations.upstream("https://fixture.invalid/feed", {"query": "local"})
    if size == 2_000_000:
        result = asyncio.run(operation)
        assert result == b"x" * 1_000_000 + b"y" * 1_000_000
    else:
        with pytest.raises(ValueError, match="exceeded 2 MB"):
            asyncio.run(operation)


@pytest.mark.parametrize("status", [302, 503])
def test_upstream_non_success_never_redirects_or_substitutes_data(
    monkeypatch: pytest.MonkeyPatch, status: int
) -> None:
    def response(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status, headers={"location": "https://untrusted.invalid/"}, text="private detail"
        )

    controlled_http(monkeypatch, response)
    with pytest.raises(ValueError, match=f"HTTP {status}; no synthetic substitute") as caught:
        asyncio.run(integrations.upstream("https://fixture.invalid/feed", {}))
    assert "private detail" not in str(caught.value)


@pytest.mark.parametrize("error_type", [httpx.ConnectError, httpx.ReadTimeout])
def test_upstream_network_failure_does_not_expose_credentials_or_response_details(
    monkeypatch: pytest.MonkeyPatch, error_type: type[httpx.HTTPError]
) -> None:
    def response(_request: httpx.Request) -> httpx.Response:
        raise error_type("private provider detail")

    controlled_http(monkeypatch, response)
    with pytest.raises(ValueError, match="Upstream unavailable") as caught:
        asyncio.run(integrations.upstream("https://fixture.invalid/feed", {"credential": "local-only"}))
    assert "private provider detail" not in str(caught.value)
    assert "local-only" not in str(caught.value)


@pytest.mark.parametrize("values", [None, [], [1, 2]])
def test_weather_rejects_missing_or_inconsistent_arrays(
    monkeypatch: pytest.MonkeyPatch, values: object
) -> None:
    async def upstream(url: str, params: dict[str, str | float]) -> bytes:
        assert url == "https://api.open-meteo.com/v1/forecast"
        assert "apikey" not in params
        return json.dumps(
            {
                "hourly": {
                    "time": ["2026-01-01T00:00"],
                    "temperature_2m": values,
                    "wind_speed_10m": [2],
                    "shortwave_radiation": [0],
                }
            }
        ).encode()

    monkeypatch.delenv("OPEN_METEO_API_KEY", raising=False)
    monkeypatch.setattr(integrations, "upstream", upstream)
    with pytest.raises(ValueError, match="arrays are missing or inconsistent"):
        asyncio.run(integrations.weather(integrations.WeatherRequest()))


def price_xml(
    *,
    curve: str = "A01",
    resolution: str = "PT15M",
    end: str = "2026-01-01T00:30Z",
    points: tuple[tuple[int, str], ...] = ((1, "-10"), (2, "70")),
) -> bytes:
    observations = "".join(
        f"<Point><position>{position}</position><price.amount>{price}</price.amount></Point>"
        for position, price in points
    )
    return (
        "<Publication_MarketDocument><TimeSeries><currency_Unit.name>EUR</currency_Unit.name>"
        "<price_Measure_Unit.name>MWH</price_Measure_Unit.name>"
        f"<curveType>{curve}</curveType><Period><timeInterval><start>2026-01-01T00:00Z</start>"
        f"<end>{end}</end></timeInterval><resolution>{resolution}</resolution>{observations}"
        "</Period></TimeSeries></Publication_MarketDocument>"
    ).encode()


@pytest.mark.parametrize(
    "payload,message",
    [
        (b"<broken", "Upstream XML is invalid"),
        (b"<Publication_MarketDocument/>", "No unique day-ahead"),
        (price_xml(curve="A99"), "Unsupported ENTSO-E curve"),
        (price_xml(resolution="PT5M"), "Unsupported price resolution"),
        (price_xml(end="2026-01-01T00:10Z"), "Invalid price period"),
        (price_xml(points=((1, "1"), (1, "2"))), "Invalid or duplicate"),
        (price_xml(points=((0, "1"),)), "Invalid or duplicate"),
        (price_xml(points=((1, "nan"),)), "Invalid or duplicate"),
        (price_xml(points=((1, "1000001"),)), "Invalid or duplicate"),
        (price_xml(points=((1, "1"),)), "Incomplete price series"),
        (price_xml(curve="A03", points=((2, "1"),)), "must start at position 1"),
    ],
)
def test_price_documents_reject_unknown_curves_incomplete_intervals_and_invalid_points(
    payload: bytes, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        integrations.parse_entsoe(payload)


def test_variable_block_prices_expand_only_declared_intervals_and_reject_duplicates() -> None:
    raw = price_xml(curve="A03", end="2026-01-01T01:00Z", points=((1, "-10"), (3, "30")))
    rows = integrations.parse_entsoe(raw)
    assert [row["price_eur_mwh"] for row in rows] == [-10, -10, 30, 30]
    assert [row["timestamp"] for row in rows] == [
        "2026-01-01T00:00:00+00:00",
        "2026-01-01T00:15:00+00:00",
        "2026-01-01T00:30:00+00:00",
        "2026-01-01T00:45:00+00:00",
    ]
    assert all(row["interval_seconds"] == 900 for row in rows)
    with pytest.raises(ValueError, match="No unique day-ahead"):
        integrations.parse_entsoe(b"<root>" + raw + raw + b"</root>")


def test_market_requires_configured_token_and_keeps_it_out_of_the_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = integrations.MarketRequest(market="DE", date=date(2026, 12, 31), consent=True)
    monkeypatch.delenv("ENTSOE_API_TOKEN", raising=False)
    with pytest.raises(ValueError, match="server-side ENTSOE_API_TOKEN"):
        asyncio.run(integrations.market_prices(request))
    monkeypatch.setenv("ENTSOE_API_TOKEN", "local-fixture-value")

    async def upstream(url: str, params: dict[str, str | float]) -> bytes:
        assert url == "https://web-api.tp.entsoe.eu/api"
        assert params == {
            "securityToken": "local-fixture-value",
            "documentType": "A44",
            "in_Domain": "10Y1001A1001A82H",
            "out_Domain": "10Y1001A1001A82H",
            "periodStart": "202612310000",
            "periodEnd": "202701010000",
        }
        return price_xml()

    monkeypatch.setattr(integrations, "upstream", upstream)
    result = asyncio.run(integrations.market_prices(request))
    assert [row["price_eur_mwh"] for row in result["rows"]] == [-10, 70]
    assert result["data_kind"] == "external_market_data"
    assert result["authenticity"] == "unverified"
    assert "local-fixture-value" not in json.dumps(result)


@pytest.mark.parametrize(
    "stamp,expected",
    [
        ("Fri, 02 Jan 2026 01:30:00 +0100", "2026-01-02T00:30:00+00:00"),
        ("Fri, 02 Jan 2026 01:30:00", None),
        ("not-a-date", None),
        ("", None),
    ],
)
def test_regulatory_dates_remain_unknown_when_missing_invalid_or_without_zone(
    monkeypatch: pytest.MonkeyPatch, stamp: str, expected: str | None
) -> None:
    raw = (
        "<rss><channel><item><title>Consultation</title><link>https://www.cre.fr/item</link>"
        f"<pubDate>{stamp}</pubDate><description>Review 2026-03-01</description></item></channel></rss>"
    ).encode()

    async def upstream(_url: str, _params: dict[str, str | float]) -> bytes:
        return raw

    monkeypatch.setenv("HELIOFORGE_REGULATORY_FEEDS", '{"FR":"https://www.cre.fr/feed"}')
    monkeypatch.setattr(integrations, "upstream", upstream)
    result = asyncio.run(
        integrations.regulatory_feed(integrations.RegulatoryRequest(consent=True, previous_sha256="0" * 64))
    )
    assert result["rows"][0]["published_at"] == expected
    assert result["rows"][0]["effective_date_verified"] is False
    assert result["rows"][0]["date_candidates"] == ["2026-03-01"]
    assert result["changed_since_previous"] is True
    assert result["sha256"] == hashlib.sha256(raw).hexdigest()


def test_feed_with_no_official_entries_cannot_be_recorded_as_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def upstream(_url: str, _params: dict[str, str | float]) -> bytes:
        return b"<rss><item><title>Unknown destination</title><link>https://untrusted.invalid/</link></item></rss>"

    monkeypatch.setenv("HELIOFORGE_REGULATORY_FEEDS", '{"FR":"https://www.cre.fr/feed"}')
    monkeypatch.setattr(integrations, "upstream", upstream)
    with pytest.raises(ValueError, match="No supported official RSS/Atom entries"):
        asyncio.run(integrations.regulatory_feed(integrations.RegulatoryRequest(consent=True)))


class ModbusFixture:
    def __init__(self, fault: str) -> None:
        self.fault = fault
        self.response = b""

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args: object) -> None:
        pass

    def sendall(self, request: bytes) -> None:
        transaction, protocol, length, unit, function, address, count = struct.unpack(">HHHBBHH", request)
        assert (protocol, length, unit, function, address, count) == (0, 6, 1, 4, 0, 2)
        payload = struct.pack(">BBHH", function, 4, 15, 30)
        if self.fault == "function":
            payload = bytes([3]) + payload[1:]
        elif self.fault == "bytecount":
            payload = payload[:1] + bytes([2]) + payload[2:]
        elif self.fault == "payload_length":
            payload = payload[:-2]
        header = struct.pack(
            ">HHHB",
            (transaction + 1) % 65536 if self.fault == "transaction" else transaction,
            1 if self.fault == "protocol" else 0,
            2 if self.fault == "short_length" else 254 if self.fault == "long_length" else 1 + len(payload),
            2 if self.fault == "unit" else unit,
        )
        self.response = header + payload
        if self.fault == "closed":
            self.response = self.response[:-1]

    def recv(self, count: int) -> bytes:
        chunk = self.response[: min(count, 2)]
        self.response = self.response[len(chunk) :]
        return chunk


@pytest.mark.parametrize(
    "fault,message",
    [
        ("transaction", "header did not match"),
        ("protocol", "header did not match"),
        ("unit", "header did not match"),
        ("short_length", "header did not match"),
        ("long_length", "header did not match"),
        ("function", "exception or unexpected register count"),
        ("bytecount", "exception or unexpected register count"),
        ("payload_length", "exception or unexpected register count"),
        ("closed", "ended before the response completed"),
    ],
)
def test_modbus_rejects_mismatched_and_truncated_responses(
    monkeypatch: pytest.MonkeyPatch, fault: str, message: str
) -> None:
    monkeypatch.setenv("HELIOFORGE_MODBUS_DEVICES", '{"meter":{"host":"fixture.invalid","count":2}}')

    def connect(address: tuple[str, int], *, timeout: float) -> ModbusFixture:
        assert address == ("fixture.invalid", 502)
        assert timeout == 3
        return ModbusFixture(fault)

    monkeypatch.setattr(socket, "create_connection", connect)
    with pytest.raises(ValueError, match=message):
        integrations.modbus_read(integrations.ModbusRequest(device="meter"))


def test_modbus_timeout_reports_no_substitute_without_internal_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HELIOFORGE_MODBUS_DEVICES", '{"meter":{"host":"fixture.invalid"}}')

    def connect(_address: tuple[str, int], *, timeout: float) -> socket.socket:
        assert timeout == 3
        raise TimeoutError("private network detail")

    monkeypatch.setattr(socket, "create_connection", connect)
    with pytest.raises(ValueError, match="unreachable; no synthetic data was substituted") as caught:
        integrations.modbus_read(integrations.ModbusRequest(device="meter"))
    assert "private network detail" not in str(caught.value)


@pytest.mark.parametrize("field,value", [("function", 6), ("address", 65535), ("port", 0), ("host", "")])
def test_modbus_rejects_write_functions_and_out_of_range_configuration_before_io(
    monkeypatch: pytest.MonkeyPatch, field: str, value: object
) -> None:
    config = {"meter": {"host": "fixture.invalid", "count": 2, field: value}}
    monkeypatch.setenv("HELIOFORGE_MODBUS_DEVICES", json.dumps(config))
    with pytest.raises(ValueError, match="Invalid server Modbus read configuration"):
        integrations.modbus_read(integrations.ModbusRequest(device="meter"))
