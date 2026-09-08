from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any, Optional


SCHEMA = """
CREATE TABLE IF NOT EXISTS packets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    received_at REAL NOT NULL,
    mode TEXT NOT NULL,
    node_id INTEGER NOT NULL,
    seq INTEGER NOT NULL,
    raw TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    mode TEXT NOT NULL,
    node_id INTEGER,
    kind TEXT NOT NULL,
    detail TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


class Database:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def log_packet(self, received_at: float, mode: str, node_id: int, seq: int, obj: dict[str, Any]) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO packets(received_at, mode, node_id, seq, raw) VALUES (?,?,?,?,?)",
                (received_at, mode, node_id, seq, json.dumps(obj, separators=(",", ":"))),
            )
            self._conn.commit()

    def log_event(self, ts: float, mode: str, node_id: Optional[int], kind: str, detail: str) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO events(ts, mode, node_id, kind, detail) VALUES (?,?,?,?,?)",
                (ts, mode, node_id, kind, detail),
            )
            self._conn.commit()

    def recent_events(self, limit: int = 40) -> list[dict[str, Any]]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT ts, mode, node_id, kind, detail FROM events ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            return [
                {"ts": ts, "mode": mode, "node_id": node_id, "kind": kind, "detail": detail}
                for ts, mode, node_id, kind, detail in cur.fetchall()
            ]

    def set_setting(self, key: str, value: Any) -> None:
        encoded = json.dumps(value, separators=(",", ":"))
        with self._lock:
            self._conn.execute(
                "INSERT INTO settings(key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, encoded),
            )
            self._conn.commit()

    def get_setting(self, key: str, default: Any = None) -> Any:
        with self._lock:
            row = self._conn.execute(
                "SELECT value FROM settings WHERE key=?", (key,)
            ).fetchone()
        if row is None:
            return default
        try:
            return json.loads(row[0])
        except (TypeError, json.JSONDecodeError):
            return default

    def counts(self) -> dict[str, int]:
        with self._lock:
            packets = self._conn.execute("SELECT COUNT(*) FROM packets").fetchone()[0]
            events = self._conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        return {"packets": int(packets), "events": int(events)}

    def export_csv(self) -> str:
        with self._lock:
            rows = self._conn.execute(
                "SELECT received_at, mode, node_id, seq, raw FROM packets ORDER BY id"
            ).fetchall()
        lines = ["received_at,mode,node_id,seq,raw"]
        for received_at, mode, node_id, seq, raw in rows:
            safe = raw.replace('"', '""')
            lines.append(f'{received_at},{mode},{node_id},{seq},"{safe}"')
        return "\n".join(lines) + "\n"

    def close(self) -> None:
        with self._lock:
            self._conn.close()
