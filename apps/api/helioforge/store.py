"""Small local SQLite audit store. Do not expose as a multi-tenant service."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict
from uuid import uuid4

from helioforge.catalog import PILOTS


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class SavedRun(TypedDict):
    run_id: str
    kind: str
    created_at: str
    input_sha256: str
    inputs: dict[str, object]
    result: dict[str, object]


class RunSummary(TypedDict):
    id: str
    kind: str
    created_at: str
    input_hash: str


class PilotEvent(TypedDict):
    id: str
    pilot_id: str
    created_at: str
    old_json: str
    new_json: str


def _text(row: sqlite3.Row, column: str | int) -> str:
    value: object = row[column]
    if not isinstance(value, str):
        raise ValueError(f"Stored column {column!r} must contain text.")
    return value


def _object(encoded: str) -> dict[str, object]:
    value: object = json.loads(encoded)
    if not isinstance(value, dict):
        raise ValueError("Stored inputs and results must be JSON objects.")
    # The JSON decoder guarantees string keys; nested values remain opaque here.
    return value


class Store:
    def __init__(self, path: str | None = None) -> None:
        if path:
            self.path = path
        else:
            self.path = os.getenv("HELIOFORGE_DB", "data/helioforge.sqlite3")
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute(
                "CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, kind"
                " TEXT, created_at TEXT, input_hash TEXT, input_json TEXT,"
                " result_json TEXT)"
            )
            db.execute("CREATE TABLE IF NOT EXISTS pilots (id TEXT PRIMARY KEY, data_json TEXT)")
            db.execute(
                "CREATE TABLE IF NOT EXISTS pilot_events (id TEXT PRIMARY"
                " KEY, pilot_id TEXT, created_at TEXT, old_json TEXT,"
                " new_json TEXT)"
            )
            for pilot in PILOTS:
                db.execute("INSERT OR IGNORE INTO pilots VALUES (?,?)", (pilot["id"], json.dumps(pilot)))

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:  # Commit successful work; roll back an exceptional exit.
                yield db
        finally:
            db.close()  # sqlite3's transaction context alone does not close a connection.

    def save(
        self, kind: str, inputs: Mapping[str, object], result: Mapping[str, object]
    ) -> dict[str, object]:
        run_id, created = str(uuid4()), utc_now()
        raw = json.dumps(inputs, sort_keys=True, separators=(",", ":"), allow_nan=False)
        digest = hashlib.sha256(raw.encode()).hexdigest()
        # Never persist provider credentials or the caller's API key.
        with self.connect() as db:
            db.execute(
                "INSERT INTO runs VALUES (?,?,?,?,?,?)",
                (run_id, kind, created, digest, raw, json.dumps(result, allow_nan=False)),
            )
        return {**result, "run_id": run_id, "created_at": created, "input_sha256": digest}

    def list_runs(self) -> list[RunSummary]:
        with self.connect() as db:
            return [
                {
                    "id": _text(row, "id"),
                    "kind": _text(row, "kind"),
                    "created_at": _text(row, "created_at"),
                    "input_hash": _text(row, "input_hash"),
                }
                for row in db.execute(
                    "SELECT id,kind,created_at,input_hash FROM runs ORDER BY created_at DESC LIMIT 100"
                )
            ]

    def get_run(self, run_id: str) -> SavedRun | None:
        with self.connect() as db:
            row = db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        if row is None:
            return None
        return {
            "run_id": _text(row, "id"),
            "kind": _text(row, "kind"),
            "created_at": _text(row, "created_at"),
            "input_sha256": _text(row, "input_hash"),
            "inputs": _object(_text(row, "input_json")),
            "result": _object(_text(row, "result_json")),
        }

    def pilots(self) -> list[dict[str, object]]:
        with self.connect() as db:
            return [_object(_text(row, 0)) for row in db.execute("SELECT data_json FROM pilots ORDER BY id")]

    def update_pilot(self, pilot_id: str, patch: Mapping[str, object]) -> dict[str, object] | None:
        with self.connect() as db:
            row = db.execute("SELECT data_json FROM pilots WHERE id=?", (pilot_id,)).fetchone()
            if row is None:
                return None
            old = _object(_text(row, 0))
            new = {**old, **patch, "updated_at": utc_now()}
            db.execute("UPDATE pilots SET data_json=? WHERE id=?", (json.dumps(new), pilot_id))
            db.execute(
                "INSERT INTO pilot_events VALUES (?,?,?,?,?)",
                (str(uuid4()), pilot_id, utc_now(), json.dumps(old), json.dumps(new)),
            )
        return new

    def pilot_events(self) -> list[PilotEvent]:
        with self.connect() as db:
            return [
                {
                    "id": _text(row, "id"),
                    "pilot_id": _text(row, "pilot_id"),
                    "created_at": _text(row, "created_at"),
                    "old_json": _text(row, "old_json"),
                    "new_json": _text(row, "new_json"),
                }
                for row in db.execute("SELECT * FROM pilot_events ORDER BY created_at DESC LIMIT 100")
            ]
