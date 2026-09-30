"""Durable store-and-forward queue for receiver JSON packets."""
from __future__ import annotations
import json
import os
import sqlite3
from datetime import datetime, timezone
import urllib.error
import urllib.request
from pathlib import Path

QUEUE = Path(os.environ.get("MOLE_QUEUE", Path(__file__).with_name("queue.db")))
API = os.environ.get("MOLE_INGEST_URL", "http://127.0.0.1:8000/api/telemetry")
MAX_PENDING = 5000

def connect():
    QUEUE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(QUEUE)
    conn.execute("CREATE TABLE IF NOT EXISTS outbound (id INTEGER PRIMARY KEY, body TEXT, sent INTEGER DEFAULT 0)")
    conn.execute("CREATE TABLE IF NOT EXISTS rejected (outbound_id INTEGER PRIMARY KEY, reason TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
    return conn

def _meta(conn, key, default=None):
    row = conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return row[0] if row else default

def _set_meta(conn, key, value):
    conn.execute("INSERT INTO meta VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))

def enqueue(reading):
    # Capture time before enqueue; do not fabricate a new time during replay.
    if reading.get("origin") == "physical" and not reading.get("sample_time"):
        raise ValueError("Physical packets need sample_time before entering the queue")
    body = json.dumps(reading, allow_nan=False)
    with connect() as conn:
        pending = conn.execute("SELECT COUNT(*) FROM outbound WHERE sent=0").fetchone()[0]
        if pending >= MAX_PENDING:
            _set_meta(conn, "overflows", str(int(_meta(conn, "overflows", "0")) + 1))
            conn.commit()
            raise OverflowError("Gateway queue is full. The packet was not stored.")
        conn.execute("INSERT INTO outbound (body) VALUES (?)", (body,))

def sync():
    sent = 0
    rejected = 0
    with connect() as conn:
        rows = conn.execute("SELECT id, body FROM outbound WHERE sent=0 ORDER BY id LIMIT 500").fetchall()
        for row_id, body in rows:
            request = urllib.request.Request(API, data=body.encode(), headers={"Content-Type":"application/json"})
            try:
                with urllib.request.urlopen(request, timeout=5) as response:
                    result = json.loads(response.read())
                if not (result.get("stored") or result.get("duplicate")):
                    break
                conn.execute("UPDATE outbound SET sent=1 WHERE id=?", (row_id,))
                _set_meta(conn, "last_success", datetime.now(timezone.utc).replace(microsecond=0).isoformat())
                conn.commit()
                sent += 1
            except urllib.error.HTTPError as error:
                if error.code in (400, 404, 409, 422):
                    conn.execute("UPDATE outbound SET sent=-1 WHERE id=?", (row_id,))
                    conn.execute("INSERT OR REPLACE INTO rejected VALUES (?, ?)", (row_id, f"HTTP {error.code}: " + error.read().decode(errors="replace")[:1000]))
                    conn.commit()
                    rejected += 1
                    continue
                break
            except (OSError, ValueError):
                break
        pending = conn.execute("SELECT COUNT(*) FROM outbound WHERE sent=0").fetchone()[0]
        last_success = _meta(conn, "last_success")
        overflows = int(_meta(conn, "overflows", "0"))
    return {"sent":sent, "pending":pending, "rejected_this_sync":rejected, "storage":str(QUEUE), "last_success":last_success, "overflows":overflows, "receiver_buffer":False, "rover_buffer":False}

def status():
    with connect() as conn:
        pending = conn.execute("SELECT COUNT(*) FROM outbound WHERE sent=0").fetchone()[0]
        rejected = conn.execute("SELECT COUNT(*) FROM rejected").fetchone()[0]
        return {
            "pending": pending,
            "rejected": rejected,
            "last_success": _meta(conn, "last_success"),
            "overflows": int(_meta(conn, "overflows", "0")),
            "storage": str(QUEUE),
            "receiver_buffer": False,
            "rover_buffer": False,
        }

if __name__ == "__main__":
    print(sync())
