"""Corrupt persisted evidence is rejected before it is returned as an object."""

from pathlib import Path

import pytest

from helioforge.store import Store


@pytest.mark.parametrize("encoded", ["null", "[]", '"text"', "12", "false"])
@pytest.mark.parametrize("result_column", [False, True])
def test_nonobject_saved_json_is_rejected(tmp_path: Path, encoded: str, result_column: bool) -> None:
    store = Store(str(tmp_path / "malformed.sqlite3"))
    inputs, result = ("{}", encoded) if result_column else (encoded, "{}")
    with store.connect() as db:
        db.execute(
            "INSERT INTO runs VALUES (?,?,?,?,?,?)",
            ("malformed", "test", "now", "hash", inputs, result),
        )
    with pytest.raises(ValueError, match="must be JSON objects"):
        store.get_run("malformed")


@pytest.mark.parametrize("column", [1, 2, 3, 4, 5])
def test_null_saved_text_is_rejected(tmp_path: Path, column: int) -> None:
    store = Store(str(tmp_path / "null.sqlite3"))
    values: list[str | None] = ["malformed", "test", "now", "hash", "{}", "{}"]
    values[column] = None
    with store.connect() as db:
        db.execute("INSERT INTO runs VALUES (?,?,?,?,?,?)", values)
    with pytest.raises(ValueError, match="must contain text"):
        store.get_run("malformed")


def test_valid_nested_saved_objects_keep_original_types(tmp_path: Path) -> None:
    store = Store(str(tmp_path / "valid.sqlite3"))
    inputs = {"array": [0, 1.5, None, True, "text"], "object": {"units": "kWh"}}
    result = {"valid": True, "finite": 0.0, "unavailable": None}
    saved = store.save("test", inputs, result)
    run_id = saved["run_id"]
    assert isinstance(run_id, str)
    retrieved = store.get_run(run_id)
    assert retrieved is not None
    assert retrieved["inputs"] == inputs
    assert retrieved["result"] == result
