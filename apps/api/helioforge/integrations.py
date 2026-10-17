"""Explicit, bounded imports and read-only connectors. Never silently replace supplied evidence."""

from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import math
import os
import re
import shutil
import socket
import struct
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

import httpx
from pydantic import Field, model_validator

from helioforge.schemas import Market, StrictModel

AREAS = {
    "FR": "10YFR-RTE------C",
    "DE": "10Y1001A1001A82H",
    "ES": "10YES-REE------0",
    "IT": "10Y1001A1001A73I",
    "NL": "10YNL----------L",
    "GB": "10YGB----------A",
}
REGULATORS = {
    "FR": "cre.fr",
    "DE": "bundesnetzagentur.de",
    "ES": "cnmc.es",
    "IT": "arera.it",
    "NL": "acm.nl",
    "GB": "ofgem.gov.uk",
}


def utc(value: str) -> datetime:
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("Use an ISO 8601 timestamp with an explicit UTC offset.") from None
    if result.tzinfo is None:
        raise ValueError("Timestamp must include Z or an explicit UTC offset.")
    return result.astimezone(timezone.utc)


def provenance(raw: bytes, kind: str) -> dict:
    return {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "data_kind": kind,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "authenticity": "unverified",
        "warnings": ["A file digest detects changes; it does not verify factual truth, origin or approval."],
    }


class SeriesImport(StrictModel):
    text: str = Field(min_length=1, max_length=700000)
    unit: Literal["kW", "kWh", "EUR/MWh", "EUR/kWh", "gCO2e/kWh", "degC", "ppm", "m/s", "W/m2"]
    source: str = Field(default="User supplied CSV", min_length=1, max_length=200)


def import_series(p: SeriesImport) -> dict:
    reader = csv.DictReader(io.StringIO(p.text.lstrip("\ufeff")))
    if reader.fieldnames != ["timestamp", "value"]:
        raise ValueError("CSV columns must be exactly timestamp,value. Declare the unit separately.")
    rows, times = [], []
    for row in reader:
        if len(rows) >= 20000 or None in row or None in row.values():
            raise ValueError("CSV must contain at most 20000 complete rows.")
        stamp = utc(row["timestamp"])
        value = float(row["value"])
        if not math.isfinite(value) or abs(value) > 1e12:
            raise ValueError("Series values must be finite and within ±1e12.")
        if times and stamp <= times[-1]:
            raise ValueError("Timestamps must be unique and increasing; no silent sorting or filling.")
        times.append(stamp)
        rows.append({"timestamp": stamp.isoformat(), "value": value, "unit": p.unit})
    if not rows:
        raise ValueError("Supply at least one data row.")
    gaps = [(b - a).total_seconds() for a, b in zip(times, times[1:])]
    regular = not gaps or min(gaps) == max(gaps)
    return {
        **provenance(p.text.encode(), "user_supplied_unverified"),
        "source": p.source,
        "unit": p.unit,
        "rows": rows,
        "values": [row["value"] for row in rows],
        "count": len(rows),
        "regular": regular,
        "interval_seconds": gaps[0] if gaps and regular else None,
        "gaps_or_irregular_intervals": not regular,
        "missing_values_imputed": 0,
    }


class DocumentImport(StrictModel):
    filename: str = Field(min_length=1, max_length=180)
    content_base64: str = Field(min_length=1, max_length=940000)
    source_url: str = Field(default="", max_length=2000)
    purpose: Literal["diagram", "tariff", "warranty", "epd", "regulation", "other"] = "other"


class GeoImport(StrictModel):
    geojson: dict = Field(max_length=3)


def import_geography(p: GeoImport) -> dict:
    document = p.geojson
    features = document.get("features")
    if (
        document.get("type") != "FeatureCollection"
        or not isinstance(features, list)
        or not 1 <= len(features) <= 200
    ):
        raise ValueError("Supply a GeoJSON FeatureCollection with 1–200 Point assets.")
    rows = []
    for index, feature in enumerate(features):
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            raise ValueError("Each asset must be a GeoJSON Feature.")
        geometry = feature.get("geometry", {})
        coordinates = geometry.get("coordinates") if isinstance(geometry, dict) else None
        if (
            not isinstance(geometry, dict)
            or geometry.get("type") != "Point"
            or not isinstance(coordinates, list)
            or len(coordinates) != 2
        ):
            raise ValueError("Asset coordinates must be [longitude,latitude] Points in WGS84.")
        if any(
            isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v)
            for v in coordinates
        ):
            raise ValueError("Coordinates must be finite numeric values.")
        lon, lat = coordinates
        if not -180 <= lon <= 180 or not -90 <= lat <= 90:
            raise ValueError("Coordinate is outside WGS84 bounds.")
        props = feature.get("properties") or {}
        if (
            not isinstance(props, dict)
            or len(props) > 20
            or any(not isinstance(v, (str, float, int, bool, type(None))) for v in props.values())
        ):
            raise ValueError("At most 20 primitive asset properties are accepted.")
        rows.append(
            {"asset": str(props.get("name", f"Asset {index + 1}"))[:200], "longitude": lon, "latitude": lat}
        )
    raw = json.dumps(document, allow_nan=False, sort_keys=True).encode()
    return {
        **provenance(raw, "user_supplied_unverified"),
        "geojson": document,
        "rows": rows,
        "notice": "Coordinates are supplied by the user. No parcel ownership, survey precision or geographic validity is certified.",
    }


def extract_document(p: DocumentImport) -> dict:
    try:
        raw = base64.b64decode(p.content_base64, validate=True)
    except ValueError:
        raise ValueError("Document is not valid base64.") from None
    if not raw or len(raw) > 700000:
        raise ValueError("Document must be 1–700000 bytes.")
    ext = Path(p.filename).suffix.lower()
    method = "utf8_text"
    if ext in {".txt", ".csv", ".json", ".md", ".xml"}:
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise ValueError("Text documents must be UTF-8 encoded.") from None
    elif ext in {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}:
        pdf = ext == ".pdf"
        if pdf and not raw.startswith(b"%PDF-"):
            raise ValueError("PDF signature is missing.")
        program = shutil.which("pdftotext" if pdf else "tesseract")
        if not program:
            raise ValueError(
                "Install pdftotext (Poppler) for PDF text or Tesseract for local image OCR; no extraction was performed."
            )
        with tempfile.TemporaryDirectory(prefix="helioforge-document-") as folder:
            source, output = Path(folder) / ("input" + ext), Path(folder) / "extracted.txt"
            source.write_bytes(raw)
            command = (
                [program, "-f", "1", "-l", "20", "-enc", "UTF-8", str(source), str(output)]
                if pdf
                else [program, str(source), str(output.with_suffix("")), "--psm", "3"]
            )
            try:
                subprocess.run(
                    command,
                    check=True,
                    timeout=20,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            except (subprocess.SubprocessError, OSError):
                raise ValueError(
                    "Local document extraction failed or exceeded 20 seconds. No result was saved."
                ) from None
            if not output.exists() or output.stat().st_size > 200000:
                raise ValueError("Extracted text is missing or exceeds 200 KB. Split the document.")
            text = output.read_text(encoding="utf-8")
        method = "poppler_first_20_pages" if pdf else "tesseract_local_ocr"
    else:
        raise ValueError("Supported documents: UTF-8 TXT/CSV/JSON/MD/XML, PDF, PNG/JPEG/TIFF.")
    if not text.strip() or len(text) > 200000:
        raise ValueError(
            "Document has no usable text or exceeds 200000 characters. Scanned PDFs need image OCR."
        )
    candidates = []
    patterns = {
        "tariff": r"\b(?:EUR|€|GBP|kWh|MWh|tariff|price)\b",
        "warranty": r"\b(?:warranty|cycles?|retained|throughput|capacity)\b",
        "diagram": r"\b(?:bus|breaker|transformer|inverter|kV|kVA)\b",
        "epd": r"\b(?:EPD|CO2|GWP|cradle|PCR|verified)\b",
        "regulation": r"\b(?:effective|entry into force|valid until|article|regulation)\b",
    }
    for line in text.splitlines():
        for category, pattern in patterns.items():
            if re.search(pattern, line, re.I) and len(candidates) < 80:
                candidates.append({"category": category, "text": line[:1000], "review_required": True})
    dates = sorted(set(re.findall(r"\b20\d{2}-\d{2}-\d{2}\b", text)))[:100]
    return {
        **provenance(raw, "user_supplied_unverified"),
        "filename": Path(p.filename).name,
        "source_url": p.source_url,
        "purpose": p.purpose,
        "extraction_method": method,
        "text": text,
        "extracted_candidates": candidates,
        "date_candidates": dates,
        "identity_verified": False,
        "notice": "Candidates are text matches, not verified contract terms or electrical topology. Review against the original.",
    }


class Reading(StrictModel):
    channel: str = Field(min_length=1, max_length=80)
    value: float = Field(ge=-1e9, le=1e9)
    unit: Literal["degC", "ppm", "kW", "V", "A", "m", "raw"]
    warning: float = Field(default=50, ge=-1e9, le=1e9)
    critical: float = Field(default=80, ge=-1e9, le=1e9)

    @model_validator(mode="after")
    def order(self):
        if self.warning >= self.critical:
            raise ValueError("High warning threshold must be below the critical threshold.")
        return self


class TelemetryImport(StrictModel):
    source: str = Field(min_length=1, max_length=200)
    timestamp: str = Field(max_length=50)
    readings: list[Reading] = Field(min_length=1, max_length=500)
    stale_after_seconds: float = Field(default=60, ge=1, le=86400)


def inspect_telemetry(p: TelemetryImport, now: datetime | None = None) -> dict:
    age = ((now or datetime.now(timezone.utc)) - utc(p.timestamp)).total_seconds()
    if age < -30:
        raise ValueError("Telemetry timestamp is in the future by more than 30 seconds.")
    if len({r.channel for r in p.readings}) != len(p.readings):
        raise ValueError("Telemetry channels must be unique.")
    rows = [
        {
            **r.model_dump(),
            "threshold_state": "critical"
            if r.value >= r.critical
            else "warning"
            if r.value >= r.warning
            else "normal",
        }
        for r in p.readings
    ]
    return {
        **provenance(p.model_dump_json().encode(), "user_supplied_unverified"),
        "source": p.source,
        "timestamp": p.timestamp,
        "age_seconds": age,
        "stale": age > p.stale_after_seconds,
        "readings": rows,
        "operational_alarm": False,
        "notice": "Read-only diagnostic thresholds. Sensor calibration, units, timing and safety alarm validation remain external.",
    }


class WeatherRequest(StrictModel):
    latitude: float = Field(default=48.8566, ge=-90, le=90)
    longitude: float = Field(default=2.3522, ge=-180, le=180)
    days: int = Field(default=2, ge=1, le=7)
    consent: bool = False


class MarketRequest(StrictModel):
    market: Market = "FR"
    date: date
    consent: bool = False


class RegulatoryRequest(StrictModel):
    market: Market = "FR"
    consent: bool = False
    previous_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")


def regulator_url(url: str, market: str) -> bool:
    parsed = urlparse(url)
    host = parsed.hostname or ""
    return (
        parsed.scheme == "https"
        and not parsed.username
        and not parsed.password
        and parsed.port in {None, 443}
        and (host == REGULATORS[market] or host.endswith("." + REGULATORS[market]))
    )


async def regulatory_feed(p: RegulatoryRequest) -> dict:
    mapping = json.loads(os.getenv("HELIOFORGE_REGULATORY_FEEDS", "{}"))
    url = mapping.get(p.market) if isinstance(mapping, dict) else None
    if not isinstance(url, str) or not regulator_url(url, p.market):
        raise ValueError(
            "Configure an official regulator HTTPS RSS/Atom URL in HELIOFORGE_REGULATORY_FEEDS for this market."
        )
    raw = await upstream(url, {})
    root = xml_root(raw)
    entries = root.findall(".//item") or root.findall(".//entry")
    rows = []
    for entry in entries[:100]:
        title = entry.findtext("title") or ""
        link_node = entry.find("link")
        link = (link_node.text or link_node.get("href") or "").strip() if link_node is not None else ""
        if not title.strip() or not regulator_url(link, p.market):
            continue
        stamp = entry.findtext("pubDate") or entry.findtext("published") or entry.findtext("updated")
        published = None
        if stamp:
            try:
                published = utc(stamp).isoformat()
            except ValueError:
                try:
                    dt = parsedate_to_datetime(stamp)
                    if dt.tzinfo:
                        published = dt.astimezone(timezone.utc).isoformat()
                except (TypeError, ValueError):
                    pass
        description = " ".join(entry.itertext())
        rows.append(
            {
                "title": title[:500],
                "source_url": link,
                "published_at": published,
                "date_candidates": sorted(set(re.findall(r"\b20\d{2}-\d{2}-\d{2}\b", description)))[:10],
                "effective_date_verified": False,
            }
        )
    if not rows:
        raise ValueError(
            "No supported official RSS/Atom entries were returned. Review the feed configuration."
        )
    evidence = provenance(raw, "external_regulatory_publications")
    return {
        **evidence,
        "source": REGULATORS[p.market],
        "source_url": url,
        "rows": rows,
        "changed_since_previous": None
        if p.previous_sha256 is None
        else evidence["sha256"] != p.previous_sha256,
        "notice": "Publication timestamps and text date candidates are not legal effective dates. Exact instruments, amendments and applicability require local legal review.",
    }


async def upstream(url: str, params: dict) -> bytes:
    # URLs are constants chosen by code, never provided in a browser request. No redirects.
    async with httpx.AsyncClient(timeout=15, follow_redirects=False, trust_env=False) as client:
        try:
            async with client.stream("GET", url, params=params) as response:
                if response.status_code != 200:
                    raise ValueError(
                        f"Upstream returned HTTP {response.status_code}; no synthetic substitute was used."
                    )
                result = bytearray()
                async for chunk in response.aiter_bytes():
                    result.extend(chunk)
                    if len(result) > 2_000_000:
                        raise ValueError("Upstream response exceeded 2 MB.")
                return bytes(result)
        except httpx.HTTPError:
            raise ValueError(
                "Upstream unavailable; credentials and response details are not exposed."
            ) from None


async def weather(p: WeatherRequest) -> dict:
    params = {
        "latitude": p.latitude,
        "longitude": p.longitude,
        "forecast_days": p.days,
        "timezone": "UTC",
        "wind_speed_unit": "ms",
        "hourly": "temperature_2m,wind_speed_10m,shortwave_radiation",
    }
    api_key = os.getenv("OPEN_METEO_API_KEY")
    if api_key:
        params["apikey"] = api_key
    raw = await upstream(
        "https://customer-api.open-meteo.com/v1/forecast"
        if api_key
        else "https://api.open-meteo.com/v1/forecast",
        params,
    )
    body = json.loads(raw)
    h = body.get("hourly", {})
    names = ("time", "temperature_2m", "wind_speed_10m", "shortwave_radiation")
    if not all(isinstance(h.get(k), list) for k in names) or len({len(h[k]) for k in names}) != 1:
        raise ValueError("Weather response arrays are missing or inconsistent.")
    rows = []
    for i, t in enumerate(h["time"]):
        row = {"timestamp": utc(str(t) + "Z").isoformat()}
        for key in names[1:]:
            v = h[key][i]
            if v is not None and (not isinstance(v, (int, float)) or not math.isfinite(v)):
                raise ValueError("Weather response contains invalid values.")
            row[key] = v
        rows.append(row)
    return {
        **provenance(raw, "external_weather_forecast"),
        "source": "Open-Meteo",
        "source_url": "https://open-meteo.com/",
        "attribution": "Weather data by Open-Meteo.com; check provider licence and commercial access terms.",
        "coordinates": {"latitude": p.latitude, "longitude": p.longitude},
        "rows": rows,
        "units": body.get("hourly_units", {}),
        "notice": "Numerical weather prediction, not field measurements or energy yield.",
    }


def xml_root(raw: bytes):
    if re.search(rb"<!\s*(?:DOCTYPE|ENTITY)", raw, re.I):
        raise ValueError("XML entities and document types are forbidden.")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        raise ValueError("Upstream XML is invalid.") from None
    for element in root.iter():
        element.tag = element.tag.split("}")[-1]
    return root


def parse_entsoe(raw: bytes) -> list[dict]:
    root = xml_root(raw)
    rows = []
    for series in root.findall(".//TimeSeries"):
        if (
            series.findtext("currency_Unit.name") != "EUR"
            or series.findtext("price_Measure_Unit.name") != "MWH"
        ):
            raise ValueError(
                "Only EUR/MWh price series are accepted; convert FX explicitly outside this connector."
            )
        curve = series.findtext("curveType") or "A01"
        if curve not in {"A01", "A03"}:
            raise ValueError("Unsupported ENTSO-E curve type.")
        for period in series.findall("Period"):
            start, end = (
                utc(period.findtext("timeInterval/start") or ""),
                utc(period.findtext("timeInterval/end") or ""),
            )
            resolution = {"PT15M": 900, "PT30M": 1800, "PT60M": 3600}.get(period.findtext("resolution"))
            if not resolution:
                raise ValueError("Unsupported price resolution.")
            count = (end - start).total_seconds() / resolution
            if count != int(count) or not 1 <= count <= 744 * 4:
                raise ValueError("Invalid price period.")
            points = {}
            for point in period.findall("Point"):
                pos, price = (
                    int(point.findtext("position") or 0),
                    float(point.findtext("price.amount") or "nan"),
                )
                if pos in points or not 1 <= pos <= count or not math.isfinite(price) or abs(price) > 1e6:
                    raise ValueError("Invalid or duplicate price observation.")
                points[pos] = price
            if curve == "A03":
                current = None
                for pos in range(1, int(count) + 1):
                    if pos in points:
                        current = points[pos]
                    if current is None:
                        raise ValueError("Variable-block prices must start at position 1.")
                    points[pos] = current
            if len(points) != count:
                raise ValueError("Incomplete price series; missing intervals are not silently filled.")
            for pos, price in sorted(points.items()):
                rows.append(
                    {
                        "timestamp": (start + timedelta(seconds=(pos - 1) * resolution)).isoformat(),
                        "interval_seconds": resolution,
                        "price_eur_mwh": price,
                    }
                )
    rows.sort(key=lambda row: row["timestamp"])
    if not rows or len({r["timestamp"] for r in rows}) != len(rows):
        raise ValueError("No unique day-ahead price series returned.")
    return rows


async def market_prices(p: MarketRequest) -> dict:
    token = os.getenv("ENTSOE_API_TOKEN")
    if not token:
        raise ValueError("Set server-side ENTSOE_API_TOKEN for live day-ahead prices.")
    raw = await upstream(
        "https://web-api.tp.entsoe.eu/api",
        {
            "securityToken": token,
            "documentType": "A44",
            "in_Domain": AREAS[p.market],
            "out_Domain": AREAS[p.market],
            "periodStart": p.date.strftime("%Y%m%d0000"),
            "periodEnd": (p.date + timedelta(days=1)).strftime("%Y%m%d0000"),
        },
    )
    return {
        **provenance(raw, "external_market_data"),
        "market": p.market,
        "bidding_zone": AREAS[p.market],
        "source": "ENTSO-E Transparency Platform",
        "source_url": "https://transparency.entsoe.eu/",
        "rows": parse_entsoe(raw),
        "notice": "UTC request day. Italy uses North bidding zone; GB availability varies. No customer tariff or legal eligibility is inferred.",
    }


class ModbusRequest(StrictModel):
    device: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")


def receive_exact(connection, n: int) -> bytes:
    data = b""
    while len(data) < n:
        chunk = connection.recv(n - len(data))
        if not chunk:
            raise ValueError("Modbus connection ended before the response completed.")
        data += chunk
    return data


def modbus_read(p: ModbusRequest) -> dict:
    """Only preconfigured read-only register ranges; no UI-provided host/address/write function."""
    devices = json.loads(os.getenv("HELIOFORGE_MODBUS_DEVICES", "{}"))
    cfg = devices.get(p.device)
    if not isinstance(cfg, dict):
        raise ValueError("Device is not in the server-side HELIOFORGE_MODBUS_DEVICES allow-list.")
    host = str(cfg.get("host", ""))
    port, unit, address, count, function = (
        int(cfg.get(k, d))
        for k, d in [("port", 502), ("unit", 1), ("address", 0), ("count", 4), ("function", 4)]
    )
    if (
        not host
        or not 1 <= port <= 65535
        or not 0 <= unit <= 247
        or not 0 <= address <= 65535
        or not 1 <= count <= 125
        or address + count > 65536
        or function not in {3, 4}
    ):
        raise ValueError("Invalid server Modbus read configuration.")
    transaction = int.from_bytes(os.urandom(2), "big")
    packet = struct.pack(">HHHBBHH", transaction, 0, 6, unit, function, address, count)
    try:
        with socket.create_connection((host, port), timeout=3) as connection:
            connection.sendall(packet)
            header = receive_exact(connection, 7)
            tx, proto, length, remote_unit = struct.unpack(">HHHB", header)
            if tx != transaction or proto != 0 or remote_unit != unit or not 3 <= length <= 253:
                raise ValueError("Modbus response header did not match the request.")
            payload = receive_exact(connection, length - 1)
    except OSError:
        raise ValueError(
            "Configured Modbus device is unreachable; no synthetic data was substituted."
        ) from None
    if len(payload) != 2 + 2 * count or payload[0] != function or payload[1] != 2 * count:
        raise ValueError("Modbus returned an exception or unexpected register count.")
    values = list(struct.unpack(">" + "H" * count, payload[2:]))
    return {
        **provenance(header + payload, "external_device_unverified"),
        "device": p.device,
        "function": function,
        "rows": [{"register": address + i, "value": v, "unit": "raw"} for i, v in enumerate(values)],
        "notice": "Unsigned 16-bit raw registers. Manufacturer scale, byte order and sensor calibration must be verified. Read-only; no plant control.",
    }


def connector_status() -> dict:
    return {
        "weather": {
            "configured": True,
            "commercial_access_configured": bool(os.getenv("OPEN_METEO_API_KEY")),
        },
        "market": {"configured": bool(os.getenv("ENTSOE_API_TOKEN"))},
        "council": {
            "enabled": os.getenv("ENABLE_OPENAI", "false").lower() == "true",
            "configured": all(os.getenv(k) for k in ("OPENAI_API_KEY", "OPENAI_MODEL", "ADMIN_API_KEY")),
            "model": os.getenv("OPENAI_MODEL") or None,
        },
        "modbus": {"configured": bool(os.getenv("HELIOFORGE_MODBUS_DEVICES"))},
        "regulatory": {"configured": bool(os.getenv("HELIOFORGE_REGULATORY_FEEDS"))},
        "document_extraction": {
            "pdf": bool(shutil.which("pdftotext")),
            "image_ocr": bool(shutil.which("tesseract")),
        },
        "notice": "Configuration does not establish successful access, validation, identity or operational approval.",
    }
