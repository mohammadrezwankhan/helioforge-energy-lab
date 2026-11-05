"""Concrete catalogue and result contracts shared by the numerical study modules.

Imported input records are validated by each study's Pydantic model. The only
open values here are the heterogeneous data/default/detail/table boundaries;
metric values, chart coordinates and catalogue metadata retain explicit types.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import NotRequired, Protocol, TypeAlias, TypeVar

from pydantic import BaseModel
from typing_extensions import TypedDict

MetricValue: TypeAlias = float | int | str | None
ChartCoordinate: TypeAlias = float | int | str | None
TableRow: TypeAlias = Mapping[str, object]


class NumericField(TypedDict):
    name: str
    label: str
    default: float
    min: float
    max: float
    step: float
    unit: str


class DataField(TypedDict):
    name: str
    label: str
    default: object


class StudySource(TypedDict):
    title: str
    url: str


class StudyDefinition(TypedDict):
    id: str
    page: str
    title: str
    summary: str
    kind: str
    fields: list[NumericField]
    data_fields: list[DataField]
    equations: list[str]
    limitations: list[str]
    sources: list[StudySource]


class Metric(TypedDict):
    label: str
    value: MetricValue
    unit: str


class Series(TypedDict):
    name: str
    x_label: str
    y_unit: str
    x: Sequence[ChartCoordinate]
    y: Sequence[float | int | None]


class StudyResult(TypedDict):
    metrics: Sequence[Metric]
    series: Sequence[Series]
    table: Sequence[TableRow]
    details: NotRequired[Mapping[str, object]]
    warnings: Sequence[str]


class StudyModule(Protocol):
    """A source-backed catalogue module with one validated dispatch boundary."""

    __name__: str
    __file__: str | None
    STUDIES: list[StudyDefinition]

    def run(self, study_id: str, inputs: object) -> StudyResult: ...


_Input = TypeVar("_Input", bound=BaseModel)
StudyRunner: TypeAlias = Callable[[object], StudyResult]
StudyEntry: TypeAlias = tuple[type[BaseModel], StudyRunner]


def typed_runner(model: type[_Input], run_model: Callable[[_Input], StudyResult]) -> StudyRunner:
    """Bind the exact input model to its solver and validate exactly once."""

    def execute(inputs: object) -> StudyResult:
        return run_model(model.model_validate(inputs))

    return execute


def typed_entry(model: type[_Input], run_model: Callable[[_Input], StudyResult]) -> StudyEntry:
    """Keep the public registry's model slot while retaining a typed dispatch."""
    return model, typed_runner(model, run_model)
