"""JSON contracts for bounded local imports and explicitly enabled connectors."""

from __future__ import annotations

from typing import Protocol, TypedDict


class ImportProvenance(TypedDict):
    sha256: str
    data_kind: str
    retrieved_at: str
    authenticity: str
    warnings: list[str]


class SeriesRow(TypedDict):
    timestamp: str
    value: float
    unit: str


class SeriesResult(ImportProvenance):
    source: str
    unit: str
    rows: list[SeriesRow]
    values: list[float]
    count: int
    regular: bool
    interval_seconds: float | None
    gaps_or_irregular_intervals: bool
    missing_values_imputed: int


class GeographyRow(TypedDict):
    asset: str
    longitude: float
    latitude: float


class GeographyResult(ImportProvenance):
    geojson: dict[str, object]
    rows: list[GeographyRow]
    notice: str


class DocumentCandidate(TypedDict):
    category: str
    text: str
    review_required: bool


class DocumentResult(ImportProvenance):
    filename: str
    source_url: str
    purpose: str
    extraction_method: str
    text: str
    extracted_candidates: list[DocumentCandidate]
    date_candidates: list[str]
    identity_verified: bool
    notice: str


class TelemetryRow(TypedDict):
    channel: str
    value: float
    unit: str
    warning: float
    critical: float
    threshold_state: str


class TelemetryResult(ImportProvenance):
    source: str
    timestamp: str
    age_seconds: float
    stale: bool
    readings: list[TelemetryRow]
    operational_alarm: bool
    notice: str


class PublicationRow(TypedDict):
    title: str
    source_url: str
    published_at: str | None
    date_candidates: list[str]
    effective_date_verified: bool


class PublicationResult(ImportProvenance):
    source: str
    source_url: str
    rows: list[PublicationRow]
    changed_since_previous: bool | None
    notice: str


class WeatherRow(TypedDict):
    timestamp: str
    temperature_2m: float | None
    wind_speed_10m: float | None
    shortwave_radiation: float | None


class WeatherResult(ImportProvenance):
    source: str
    source_url: str
    attribution: str
    coordinates: dict[str, float]
    rows: list[WeatherRow]
    units: dict[str, str]
    notice: str


class PriceRow(TypedDict):
    timestamp: str
    interval_seconds: int
    price_eur_mwh: float


class MarketResult(ImportProvenance):
    market: str
    bidding_zone: str
    source: str
    source_url: str
    rows: list[PriceRow]
    notice: str


class RegisterRow(TypedDict):
    register: int
    value: int
    unit: str


class ModbusResult(ImportProvenance):
    device: str
    function: int
    rows: list[RegisterRow]
    notice: str


class ReadConnection(Protocol):
    def recv(self, size: int) -> bytes: ...


class CouncilStatus(TypedDict):
    enabled: bool
    configured: bool
    model: str | None


class ConnectorStatus(TypedDict):
    weather: dict[str, bool]
    market: dict[str, bool]
    council: CouncilStatus
    modbus: dict[str, bool]
    regulatory: dict[str, bool]
    document_extraction: dict[str, bool]
    notice: str
