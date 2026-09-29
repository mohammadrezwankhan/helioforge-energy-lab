"""Small local SQLite audit store. Do not expose as a multi-tenant service."""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from contextlib import contextmanager
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from helioforge.catalog import PILOTS


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, path: str | None = None):
        self.path = path or os.getenv("HELIOFORGE_DB", "data/helioforge.sqlite3")
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, kind TEXT, created_at TEXT, input_hash TEXT, input_json TEXT, result_json TEXT)")
            db.execute("CREATE TABLE IF NOT EXISTS pilots (id TEXT PRIMARY KEY, data_json TEXT)")
            db.execute("CREATE TABLE IF NOT EXISTS pilot_events (id TEXT PRIMARY KEY, pilot_id TEXT, created_at TEXT, old_json TEXT, new_json TEXT)")
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

    def save(self, kind: str, inputs: dict, result: dict) -> dict:
        run_id, created = str(uuid4()), utc_now()
        raw = json.dumps(inputs, sort_keys=True, separators=(",", ":"), allow_nan=False)
        digest = hashlib.sha256(raw.encode()).hexdigest()
        # Never persist provider credentials or the caller's API key.
        with self.connect() as db:
            db.execute("INSERT INTO runs VALUES (?,?,?,?,?,?)", (run_id, kind, created, digest, raw,
                                                                   json.dumps(result, allow_nan=False)))
        return {**result, "run_id": run_id, "created_at": created, "input_sha256": digest}

    def list_runs(self) -> list[dict]:
        with self.connect() as db:
            return [dict(row) for row in db.execute("SELECT id,kind,created_at,input_hash FROM runs ORDER BY created_at DESC LIMIT 100")]

    def get_run(self, run_id: str) -> dict | None:
        with self.connect() as db:
            row = db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        if row is None:
            return None
        return {"run_id": row["id"], "kind": row["kind"], "created_at": row["created_at"],
                "input_sha256": row["input_hash"], "inputs": json.loads(row["input_json"]),
                "result": json.loads(row["result_json"])}

    def pilots(self) -> list[dict]:
        with self.connect() as db:
            return [json.loads(row[0]) for row in db.execute("SELECT data_json FROM pilots ORDER BY id")]

    def update_pilot(self, pilot_id: str, patch: dict) -> dict | None:
        with self.connect() as db:
            row = db.execute("SELECT data_json FROM pilots WHERE id=?", (pilot_id,)).fetchone()
            if row is None:
                return None
            old = json.loads(row[0])
            new = {**old, **patch, "updated_at": utc_now()}
            db.execute("UPDATE pilots SET data_json=? WHERE id=?", (json.dumps(new), pilot_id))
            db.execute("INSERT INTO pilot_events VALUES (?,?,?,?,?)", (str(uuid4()), pilot_id, utc_now(),
                                                                        json.dumps(old), json.dumps(new)))
        return new

    def pilot_events(self) -> list[dict]:
        with self.connect() as db:
            return [dict(row) for row in db.execute("SELECT * FROM pilot_events ORDER BY created_at DESC LIMIT 100")]
