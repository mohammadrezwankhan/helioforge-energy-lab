"""Typed contracts for the versioned, packaged hybrid teaching catalogue."""

from __future__ import annotations

from typing import Literal

from typing_extensions import TypedDict

Control = Literal["GFL", "GFM", "Dual", "Synchronous"]


class HybridPreset(TypedDict):
    system_id: str
    scenario_id: str
    hours: int
    control: Control
    critical_fraction: float
    initial_soc: float
    min_soc: float
    max_soc: float
    round_trip_efficiency: float
    import_eur_kwh: float
    export_eur_kwh: float
    generator_eur_kwh: float
    solar_kw: float
    wind_kw: float
    hydro_kw: float
    generator_kw: float
    battery_kwh: float
    battery_kw: float
    load_kw: float
    grid_import_kw: float
    grid_export_kw: float


class HybridSystem(TypedDict):
    id: str
    name: str
    family: str
    topology: str
    coupling: str
    control: str
    technologies: list[str]
    description: str
    learning_focus: str
    evidence: str
    mode: str
    level: str
    preset: HybridPreset
    source_ids: list[str]


class ScenarioModifiers(TypedDict, total=False):
    solar_factor: float
    wind_factor: float
    load_factor: float
    step_factor: float
    outage_start: int
    outage_hours: int
    hours: int
    export_factor: float
    import_factor: float
    negative_prices: bool
    price_factor: float
    capacity_factor: float
    battery_factor: float
    generator_factor: float
    hydro_factor: float
    reserve_floor: float


class HybridScenario(TypedDict):
    id: str
    name: str
    category: str
    modifiers: ScenarioModifiers
    description: str
    mode: str


class CatalogueSource(TypedDict):
    id: str
    name: str
    url: str
    reviewed_on: str
    scope: str


class Technology(TypedDict):
    id: str
    name: str
    icon: str
    color: str
    boundary: str


class LessonStep(TypedDict):
    title: str
    body: str


class LessonQuestion(TypedDict):
    question: str
    options: list[str]
    answer: int
    explanation: str


class HybridLesson(TypedDict):
    id: str
    system_id: str
    title: str
    level: str
    minutes: int
    objectives: list[str]
    steps: list[LessonStep]
    scenario_id: str
    quiz: list[LessonQuestion]
    source_ids: list[str]


class HybridCatalog(TypedDict):
    version: str
    data_kind: str
    coverage_statement: str
    sources: list[CatalogueSource]
    technologies: list[Technology]
    systems: list[HybridSystem]
    scenarios: list[HybridScenario]
    lessons: list[HybridLesson]


class ConfigurationResult(TypedDict):
    valid: bool
    issues: list[str]
    tags: list[dict[str, str]]
    system_id: str
    scenario_id: str
    data_kind: str
