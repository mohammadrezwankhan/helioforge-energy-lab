"""Assert concrete result shapes before independent numerical test arithmetic.

These helpers preserve the original values. They do not coerce strings, fill
missing data, replace nulls, round numbers, or alter numerical tolerances.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence


def number(value: object) -> float:
    """Require a real JSON number without changing its value."""
    assert isinstance(value, (int, float)) and not isinstance(value, bool)
    return value


def integer(value: object) -> int:
    """Require an integer index/count before using it for discrete indexing."""
    assert isinstance(value, int) and not isinstance(value, bool)
    return value


def text(value: object) -> str:
    """Require text before applying textual or timestamp operations."""
    assert isinstance(value, str)
    return value


def sequence(value: object) -> Sequence[object]:
    """Require a list/tuple rather than treating text or mappings as records."""
    assert isinstance(value, (list, tuple))
    return value


def record(value: object) -> Mapping[str, object]:
    """Require a string-keyed result record, retaining every original value."""
    assert isinstance(value, Mapping)
    checked: dict[str, object] = {}
    for key, item in value.items():
        assert isinstance(key, str)
        checked[key] = item
    return checked


def numbers(value: object) -> list[float]:
    """Require a complete numeric vector with no missing or coerced entries."""
    return [number(item) for item in sequence(value)]


def records(value: object) -> list[Mapping[str, object]]:
    """Require an ordered collection of complete string-keyed records."""
    return [record(item) for item in sequence(value)]
