"""MOLE API: shared persistence for the website, app, gateway, and rover."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import sqlite3
import time
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from fpdf import FPDF
from openpyxl import Workbook
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Literal

from analysis import classify_window
from mole_chat import (  # Groq free API by default; Ollama only if MOLE_LLM_BACKEND=ollama
    LLMUnavailable,
    build_messages,
    iter_llm_tokens,
    llm_status,
    related_sources,
)

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.environ.get("MOLE_DB", ROOT / "data" / "mole.db"))
EVIDENCE_DIR = Path(os.environ.get("MOLE_EVIDENCE", DB_PATH.parent / "evidence"))
TOKEN = os.environ.get("MOLE_OPERATOR_TOKEN", "")
MODEL_VERSION = "rules-window-v1"
PUBLIC_URL = os.environ.get("MOLE_PUBLIC_URL", "http://127.0.0.1:3000")

app = FastAPI(title="MOLE", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

NODES = {
    "A": {"name": "Node A", "x": 28, "y": 42, "place": "Mine entrance", "channels": ["tilt_deg", "vibration", "potentiometer_raw"]},
    "B": {"name": "Node B", "x": 48, "y": 38, "place": "Removable ground panel", "channels": ["tilt_deg", "vibration", "temperature_c"]},
    "C": {"name": "Node C", "x": 62, "y": 58, "place": "Ventilation shaft", "channels": ["tilt_deg", "vibration", "potentiometer_raw", "gas_raw"]},
    "D": {"name": "Node D", "x": 74, "y": 34, "place": "Beside ventilation, right side", "channels": ["tilt_deg", "vibration", "temperature_c", "humidity_pct", "pressure_hpa"]},
}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS sos_receipts (
              request_id TEXT PRIMARY KEY, sos_id TEXT UNIQUE
            );
            CREATE TABLE IF NOT EXISTS session_reviews (
              node_id TEXT, session_id TEXT, label TEXT, note TEXT, reviewed_at TEXT,
              PRIMARY KEY(node_id, session_id)
            );
            CREATE TABLE IF NOT EXISTS sites (
              id TEXT PRIMARY KEY, name TEXT, schematic INTEGER, note TEXT
            );
            CREATE TABLE IF NOT EXISTS nodes (
              id TEXT PRIMARY KEY, site_id TEXT, name TEXT, x REAL, y REAL, place TEXT, condition TEXT
            );
            CREATE TABLE IF NOT EXISTS telemetry (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              node_id TEXT, session_id TEXT, sequence INTEGER,
              sample_time TEXT, received_time TEXT, origin TEXT,
              payload TEXT, valid INTEGER,
              UNIQUE(node_id, session_id, sequence)
            );
            CREATE TABLE IF NOT EXISTS incidents (
              id TEXT PRIMARY KEY, node_id TEXT, status TEXT, severity TEXT,
              title TEXT, explanation TEXT, evidence TEXT, origin TEXT,
              opened_at TEXT, updated_at TEXT, closure_reason TEXT
            );
            CREATE TABLE IF NOT EXISTS actions (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              incident_id TEXT, action TEXT, reason TEXT, actor TEXT, at TEXT
            );
            CREATE TABLE IF NOT EXISTS sos (
              id TEXT PRIMARY KEY, status TEXT, lat REAL, lon REAL, accuracy_m REAL,
              located_at TEXT, landmark TEXT, message TEXT, contact TEXT,
              created_at TEXT, origin TEXT
            );
            CREATE TABLE IF NOT EXISTS missions (
              id TEXT PRIMARY KEY, incident_id TEXT, state TEXT, note TEXT,
              created_at TEXT, evidence TEXT
            );
            CREATE TABLE IF NOT EXISTS mission_meta (
              mission_id TEXT PRIMARY KEY, unit TEXT, checklist TEXT, position TEXT,
              last_contact TEXT, simulation INTEGER
            );
            CREATE TABLE IF NOT EXISTS commands (
              id TEXT PRIMARY KEY, mission_id TEXT, kind TEXT, expires_at TEXT,
              status TEXT, created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS reports (
              id TEXT PRIMARY KEY, incident_id TEXT, revision INTEGER, created_at TEXT, snapshot TEXT
            );
            CREATE TABLE IF NOT EXISTS features (
              node_id TEXT, session_id TEXT, sequence INTEGER, computed_at TEXT,
              model_version TEXT, result TEXT,
              PRIMARY KEY (node_id, session_id, sequence)
            );
            CREATE TABLE IF NOT EXISTS jobs (
              id TEXT PRIMARY KEY, kind TEXT, status TEXT, payload TEXT, error TEXT,
              attempts INTEGER, created_at TEXT, updated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS evidence_objects (
              id TEXT PRIMARY KEY, mission_id TEXT, file_name TEXT, sha256 TEXT,
              byte_count INTEGER, origin TEXT, created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS sync_jobs (
              id TEXT PRIMARY KEY, source TEXT, sent INTEGER, pending INTEGER,
              rejected INTEGER, created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS calibrations (
              id INTEGER PRIMARY KEY AUTOINCREMENT, node_id TEXT, channel TEXT, note TEXT, created_at TEXT,
              mode TEXT, baseline_value REAL, reference_value REAL, tolerance REAL,
              sample_count INTEGER, status TEXT, unit TEXT
            );
            CREATE TABLE IF NOT EXISTS link_events (
              id INTEGER PRIMARY KEY AUTOINCREMENT, node_id TEXT, session_id TEXT,
              sequence INTEGER, kind TEXT, at TEXT
            );
            CREATE TABLE IF NOT EXISTS model_versions (
              id TEXT PRIMARY KEY, state TEXT, note TEXT
            );
            CREATE TABLE IF NOT EXISTS weather_observations (
              id TEXT PRIMARY KEY, kind TEXT, value REAL, unit TEXT, source TEXT,
              observed_at TEXT, freshness TEXT
            );
            CREATE TABLE IF NOT EXISTS imports (
              id TEXT PRIMARY KEY, filename TEXT, stored_name TEXT, created_at TEXT,
              status TEXT, issues TEXT, rows_json TEXT
            );
            """
        )
        calibration_columns = {row["name"] for row in conn.execute("PRAGMA table_info(calibrations)")}
        for name, sql_type in {
            "mode": "TEXT", "baseline_value": "REAL", "reference_value": "REAL",
            "tolerance": "REAL", "sample_count": "INTEGER", "status": "TEXT", "unit": "TEXT",
        }.items():
            if name not in calibration_columns:
                conn.execute(f"ALTER TABLE calibrations ADD COLUMN {name} {sql_type}")
        conn.execute(
            "INSERT OR IGNORE INTO model_versions VALUES (?, 'active', ?)",
            (MODEL_VERSION, "Prototype rules only. Isolation Forest is not loaded."),
        )
        conn.execute(
            "INSERT OR IGNORE INTO weather_observations VALUES ('weather-none', 'observed_rain', NULL, 'mm', NULL, ?, 'unavailable')",
            (now(),),
        )
        conn.execute(
            "INSERT OR IGNORE INTO sites VALUES (?, ?, 1, ?)",
            ("east-panel", "East Panel Demonstration", "Demonstration schematic. Real coordinates have not been supplied."),
        )
        for node_id, meta in NODES.items():
            conn.execute(
                "INSERT OR IGNORE INTO nodes VALUES (?, ?, ?, ?, ?, ?, 'normal')",
                (node_id, "east-panel", meta["name"], meta["x"], meta["y"], meta["place"]),
            )
        if conn.execute("SELECT COUNT(*) c FROM telemetry").fetchone()["c"] == 0:
            seed(conn)


def seed(conn: sqlite3.Connection) -> None:
    base = time.time() - 3600
    series = {
        "A": [0.4, 0.5, 0.45, 0.5, 0.48, 0.5],
        "B": [0.6, 0.9, 1.4, 2.1, 2.8, 3.4],
        "C": [0.3, 0.3, 0.35, 0.32, 0.3, 0.31],
        "D": [0.2, 0.25, 0.22, 0.24, 0.23, 0.22],
    }
    for node_id, tilts in series.items():
        for index, tilt in enumerate(tilts):
            payload = {
                "tilt_deg": tilt,
                "vibration": 0.2 if node_id != "B" else 0.4,
                "origin_note": "demonstration seed",
            }
            if node_id == "A":
                payload["potentiometer_raw"] = 410 + index
                payload["potentiometer_mm"] = None
                payload["potentiometer_note"] = "Millimetres unavailable until mechanical calibration."
            if node_id == "B":
                payload["temperature_c"] = None
                payload["temperature_note"] = "DS18B20 air temperature in degrees Celsius. Not soil moisture or groundwater."
            if node_id == "C":
                payload["potentiometer_raw"] = 380 + index
                payload["potentiometer_mm"] = None
                payload["gas_raw"] = 240
                payload["gas_ready"] = True
            if node_id == "D":
                payload.update({"temperature_c": 27.4, "humidity_pct": 61, "pressure_hpa": 1008})
            conn.execute(
                "INSERT INTO telemetry (node_id, session_id, sequence, sample_time, received_time, origin, payload, valid) VALUES (?, ?, ?, ?, ?, ?, ?, 1)",
                (
                    node_id,
                    "seed",
                    index + 1,
                    datetime.fromtimestamp(base + index * 600, timezone.utc).isoformat(),
                    now(),
                    "simulated",
                    json.dumps(payload),
                ),
            )
    refresh_conditions(conn)


def rows(conn: sqlite3.Connection, node_id: str) -> list[dict]:
    active = conn.execute(
        """SELECT session_id FROM telemetry
           WHERE node_id=?
           ORDER BY sample_time DESC, id DESC LIMIT 1""",
        (node_id,),
    ).fetchone()
    if not active:
        return []
    found = conn.execute(
        """SELECT * FROM telemetry
           WHERE node_id=? AND session_id=?
           ORDER BY sequence ASC, id ASC LIMIT 120""",
        (node_id, active["session_id"]),
    ).fetchall()
    parsed = []
    for row in found:
        payload = json.loads(row["payload"])
        payload["valid"] = bool(row["valid"])
        payload["sample_time"] = row["sample_time"]
        payload["received_time"] = row["received_time"]
        payload["origin"] = row["origin"]
        payload["session_id"] = row["session_id"]
        payload["sequence"] = row["sequence"]
        if row["origin"] == "physical":
            try:
                received = datetime.fromisoformat(row["received_time"])
                sampled = datetime.fromisoformat(row["sample_time"].replace("Z", "+00:00"))
                ages = [(datetime.now(timezone.utc) - t).total_seconds() for t in (received, sampled)]
                payload["stale"] = payload.get("stale", False) or any(age > 120 or age < -30 for age in ages)
            except (ValueError, TypeError):
                payload["stale"] = True
        parsed.append(payload)
    return parsed


def active_tilt_baseline(conn: sqlite3.Connection, node_id: str) -> float | None:
    row = conn.execute(
        """SELECT baseline_value FROM calibrations
           WHERE node_id=? AND channel='tilt_deg' AND status='active'
             AND baseline_value IS NOT NULL ORDER BY id DESC LIMIT 1""",
        (node_id,),
    ).fetchone()
    return row["baseline_value"] if row else None


def refresh_conditions(conn: sqlite3.Connection) -> None:
    conditions = {}
    packets = {node_id: rows(conn, node_id) for node_id in NODES}
    for node_id, samples in packets.items():
        neighbors = []
        for other, other_samples in packets.items():
            if other == node_id or other == "C" or node_id == "C" or not other_samples:
                continue
            other_result = classify_window(other_samples, [], active_tilt_baseline(conn, other))
            neighbors.append({"node_id": other, "condition": other_result["movement_state"], "valid": other_samples[-1].get("valid", False) and not other_samples[-1].get("stale")})
        result = classify_window(samples, neighbors, active_tilt_baseline(conn, node_id))
        conditions[node_id] = result
        conn.execute("UPDATE nodes SET condition=? WHERE id=?", (result["condition"], node_id))
        open_row = conn.execute(
            "SELECT id FROM incidents WHERE node_id=? AND status!='CLOSED' ORDER BY opened_at DESC LIMIT 1",
            (node_id,),
        ).fetchone()
        if result["condition"] in {"movement", "gas", "sensor_fault", "stale", "watch"}:
            if not open_row:
                incident_id = f"INC-{node_id}-{uuid4().hex[:6].upper()}"
                conn.execute(
                    "INSERT INTO incidents VALUES (?, ?, 'OPEN', ?, ?, ?, ?, ?, ?, ?, NULL)",
                    (
                        incident_id,
                        node_id,
                        result["condition"],
                        f"{NODES[node_id]['name']} {result['condition'].replace('_', ' ')}",
                        " ".join(result["evidence"]),
                        json.dumps(result),
                        samples[-1]["origin"] if samples else "simulated",
                        now(),
                        now(),
                    ),
                )
            else:
                conn.execute(
                    "UPDATE incidents SET severity=?, explanation=?, evidence=?, updated_at=? WHERE id=?",
                    (result["condition"], " ".join(result["evidence"]), json.dumps(result), now(), open_row["id"]),
                )
        if result["condition"] in {"movement", "gas"}:
            raise_local_sos(conn, node_id, result)
        conn.commit()


def raise_local_sos(conn: sqlite3.Connection, node_id: str, result: dict) -> None:
    """Tell miners and residents on the field page. This is not an SMS or a rescue dispatch."""
    if result.get("condition") not in {"movement", "gas"}:
        return
    marker = f"{node_id}:%"
    existing = conn.execute(
        "SELECT id FROM sos WHERE origin='analysis' AND status='QUEUED' AND landmark LIKE ?",
        (marker,),
    ).fetchone()
    if existing:
        return
    place = NODES[node_id]["place"]
    summary = result.get("summary") or result["condition"].replace("_", " ")
    conn.execute(
        "INSERT INTO sos VALUES (?, 'QUEUED', NULL, NULL, NULL, NULL, ?, ?, NULL, ?, 'analysis')",
        (
            f"SOS-{uuid4().hex.upper()}",
            f"{node_id}:{place}",
            f"Leave this area now. Monitoring check at {NODES[node_id]['name']}, {place}: {summary}",
            now(),
        ),
    )


class Reading(BaseModel):
    model_config = {"allow_inf_nan": False}
    node_id: str
    session_id: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_.-]+$")
    sequence: int = Field(ge=0)
    sample_time: str | None = None
    origin: str = "simulated"
    valid: bool = True
    tilt_deg: float | None = None
    vibration: float | None = None
    potentiometer_raw: float | None = None
    gas_raw: float | None = None
    gas_ready: bool | None = None
    temperature_c: float | None = None
    humidity_pct: float | None = None
    pressure_hpa: float | None = None
    fault: bool = False
    fault_reason: str | None = None
    stale: bool = False
    ir: float | None = None
    linear_raw: float | None = None
    temperature_signal_raw: float | None = None

    @field_validator("sample_time")
    @classmethod
    def timestamp_with_zone(cls, value):
        if value is None:
            return value
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("sample_time needs an explicit timezone")
        return parsed.astimezone(timezone.utc).isoformat()


class ActionIn(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)

    @field_validator("reason")
    @classmethod
    def meaningful_reason(cls, value):
        if len(value.strip()) < 3:
            raise ValueError("Provide a meaningful review note")
        return value.strip()


class SosIn(BaseModel):
    model_config = {"allow_inf_nan": False}
    request_id: str | None = Field(default=None, pattern=r"^[a-f0-9-]{36}$")
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    accuracy_m: float | None = Field(default=None, ge=0)
    located_at: str | None = None
    landmark: str | None = None
    message: str | None = None
    contact: str | None = None
    delivered: bool = False

    @model_validator(mode="after")
    def coordinates_together(self):
        if (self.lat is None) != (self.lon is None):
            raise ValueError("Latitude and longitude must be supplied together")
        if any(len(value or "") > 2000 for value in (self.landmark, self.message, self.contact)):
            raise ValueError("SOS text fields must be at most 2000 characters")
        return self


class MissionIn(BaseModel):
    incident_id: str
    note: str = "Inspection requested from the fixed-node incident."


class EvidenceIn(BaseModel):
    note: str
    finding: str = "Reviewed candidate. Dimensions are not inferred."


class CommandIn(BaseModel):
    mission_id: str
    kind: str
    expires_at: str


class PositionIn(BaseModel):
    known: bool
    note: str = Field(min_length=3, max_length=500)


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8000)


class AssistantIn(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=16)
    stream: bool = False


class JobIn(BaseModel):
    kind: Literal["telemetry_export", "report_file"]
    report_id: str | None = None

    @model_validator(mode="after")
    def report_required(self):
        if self.kind == "report_file" and not self.report_id:
            raise ValueError("report_file jobs need a report_id")
        return self


class CalibrationIn(BaseModel):
    node_id: str
    channel: Literal[
        "tilt_deg", "vibration", "potentiometer_raw", "gas_raw", "ir", "linear_raw",
        "temperature_signal_raw", "temperature_c", "humidity_pct", "pressure_hpa"
    ]
    note: str = Field(min_length=3, max_length=500)
    mode: Literal["baseline", "reference_check", "maintenance"] = "maintenance"
    baseline_value: float | None = None
    reference_value: float | None = None
    tolerance: float | None = Field(default=None, ge=0)
    sample_count: int | None = Field(default=None, ge=1, le=120)
    status: Literal["active", "draft", "failed"] = "active"
    unit: str | None = Field(default=None, max_length=24)

    @field_validator("note")
    @classmethod
    def meaningful_note(cls, value):
        if len(value.strip()) < 3:
            raise ValueError("Provide a meaningful calibration note")
        return value.strip()


class SyncIn(BaseModel):
    source: str = Field(min_length=1, max_length=80)
    sent: int = Field(ge=0)
    pending: int = Field(ge=0)
    rejected: int = Field(ge=0)


class ImportIn(BaseModel):
    filename: str = Field(min_length=1, max_length=120)
    csv_text: str = Field(min_length=1, max_length=200000)


def require_operator(credential: str | None) -> None:
    if not TOKEN or credential != TOKEN:
        raise HTTPException(status_code=403, detail="A paired operator credential is required.")


@app.on_event("startup")
def startup() -> None:
    init()


init()


@app.get("/health")
def health() -> dict:
    status = llm_status()
    return {
        "ok": DB_PATH.exists(),
        "database": str(DB_PATH),
        "llm": (
            f"{status['provider']}:{status['model']}"
            if status["ok"]
            else "unavailable"
        ),
        "deployment": "local",
        "https": False,
    }


@app.get("/api/state")
def state() -> dict:
    with connect() as conn:
        nodes = []
        for row in conn.execute("SELECT * FROM nodes ORDER BY id"):
            history = rows(conn, row["id"])
            latest = history[-1] if history else {}
            analysis = classify_window(history, [], active_tilt_baseline(conn, row["id"]))
            calibration = conn.execute(
                "SELECT channel, baseline_value, reference_value, tolerance, sample_count, status, unit, note, created_at FROM calibrations WHERE node_id=? ORDER BY id DESC",
                (row["id"],),
            ).fetchall()
            latest_calibrations = {}
            for item in calibration:
                if item["channel"] not in latest_calibrations:
                    latest_calibrations[item["channel"]] = dict(item)
            nodes.append({**dict(row), "place": NODES[row["id"]]["place"], "condition": analysis["condition"], "analysis": analysis, "latest": latest, "history": history[-120:], "capabilities": NODES[row["id"]]["channels"], "calibrations": latest_calibrations})
        incidents = [dict(item) for item in conn.execute("SELECT * FROM incidents ORDER BY updated_at DESC")]
        for incident in incidents:
            report = conn.execute("SELECT id FROM reports WHERE incident_id=? ORDER BY revision DESC LIMIT 1", (incident["id"],)).fetchone()
            incident["report_id"] = report["id"] if report else None
        missions = [decorate_mission(conn, dict(item)) for item in conn.execute("SELECT * FROM missions ORDER BY created_at DESC")]
        for node in nodes:
            if node["condition"] in {"movement", "gas"}:
                raise_local_sos(conn, node["id"], node["analysis"])
        conn.commit()
        sos_rows = [dict(item) for item in conn.execute(
            """SELECT id, status, created_at, origin,
                      lat IS NOT NULL AS has_location
               FROM sos ORDER BY created_at DESC LIMIT 40"""
        )]
        bulletins = []
        for row in conn.execute(
            "SELECT id, landmark, message, created_at FROM sos WHERE origin='analysis' AND status='QUEUED' ORDER BY created_at DESC"
        ):
            node_id, _, place = (row["landmark"] or "").partition(":")
            node = next((item for item in nodes if item["id"] == node_id), None)
            if node and node["condition"] in {"movement", "gas"}:
                bulletins.append({
                    "id": row["id"],
                    "node_id": node_id,
                    "place": place or node.get("place"),
                    "message": row["message"],
                    "created_at": row["created_at"],
                    "audience": "miners and residents with this page open",
                })
        jobs_failed = conn.execute("SELECT COUNT(*) c FROM jobs WHERE status='FAILED'").fetchone()["c"]
        jobs_pending = conn.execute("SELECT COUNT(*) c FROM jobs WHERE status IN ('PENDING','RUNNING')").fetchone()["c"]
    return {
        "site": {"id": "east-panel", "name": "East Panel Demonstration", "schematic": True},
        "weather": {"observed_rain_mm": None, "forecast_rain_mm": None, "source": None, "freshness": "unavailable"},
        "nodes": nodes,
        "incidents": incidents,
        "missions": missions,
        "sos": sos_rows,
        "bulletins": bulletins,
        "model_state": "Prototype persistence rules, robust window reference, trend rate and median shift are active. No trained ML artifact is loaded.",
        "persistence": {
            "engine": "sqlite",
            "features_kept_separate": True,
            "jobs_failed": jobs_failed,
            "jobs_pending": jobs_pending,
        },
    }


@app.get("/api/operator/check")
def operator_check(x_mole_capability: str | None = Header(default=None)) -> dict:
    require_operator(x_mole_capability)
    return {"paired": True}


CHECKLIST = ("incident_link", "observation", "position_recorded")


def fresh_checklist() -> list[dict]:
    return [{"id": item, "done": item == "incident_link"} for item in CHECKLIST]


def decorate_mission(conn: sqlite3.Connection, row: dict) -> dict:
    meta = conn.execute("SELECT * FROM mission_meta WHERE mission_id=?", (row["id"],)).fetchone()
    checklist = json.loads(meta["checklist"]) if meta else fresh_checklist()
    position = json.loads(meta["position"]) if meta and meta["position"] else {
        "known": False, "uncertainty_m": None, "note": "Last contact unavailable",
    }
    row.update({
        "unit": "R1",
        "simulation": True,
        "checklist": checklist,
        "inspection_complete": all(item["done"] for item in checklist),
        "position": position,
        "last_contact": None,
        "camera": "not equipped",
        "drive": "not enabled",
    })
    return row


def save_checklist(conn: sqlite3.Connection, mission_id: str, checklist: list[dict], position: dict | None = None) -> None:
    current = conn.execute("SELECT position FROM mission_meta WHERE mission_id=?", (mission_id,)).fetchone()
    stored = json.dumps(position) if position is not None else (current["position"] if current else None)
    conn.execute(
        """INSERT INTO mission_meta VALUES (?, 'R1', ?, ?, NULL, 1)
           ON CONFLICT(mission_id) DO UPDATE SET checklist=excluded.checklist, position=excluded.position""",
        (mission_id, json.dumps(checklist), stored),
    )


def evidence_dir() -> Path:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    return EVIDENCE_DIR


def workbook_bytes(conn: sqlite3.Connection) -> bytes:
    book = Workbook()
    sheet = book.active
    sheet.title = "Telemetry"
    for row in telemetry_table(conn):
        sheet.append(row)
    buffer = BytesIO()
    book.save(buffer)
    return buffer.getvalue()


CHANNEL_UNITS = {
    "tilt_deg": "deg",
    "vibration": "relative",
    "potentiometer_raw": "count",
    "gas_raw": "raw",
    "temperature_c": "C",
    "humidity_pct": "%RH",
    "pressure_hpa": "hPa",
    "linear_raw": "count",
    "temperature_signal_raw": "count",
}


def telemetry_table(conn: sqlite3.Connection) -> list[list]:
    rows = [["node_id", "sample_time", "received_time", "origin", "valid", "channel", "value", "unit"]]
    for row in conn.execute("SELECT * FROM telemetry ORDER BY id"):
        payload = json.loads(row["payload"])
        for key, unit in CHANNEL_UNITS.items():
            if key in payload:
                value = payload[key]
                rows.append([row["node_id"], row["sample_time"], row["received_time"], row["origin"], row["valid"], key, "unavailable" if value is None else value, unit])
    return rows


def render_report_pdf(report: sqlite3.Row) -> bytes:
    incident = json.loads(report["snapshot"])
    actions = incident.get("actions", [])
    mission = incident.get("mission")
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(False)
    pdf.add_page()
    pdf.set_fill_color(247, 241, 222)
    pdf.rect(0, 0, 210, 297, "F")
    pdf.set_text_color(78, 34, 15)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_xy(12, 12)
    pdf.cell(0, 10, "MOLE")
    pdf.set_font("Helvetica", "", 11)
    pdf.set_xy(12, 22)
    pdf.multi_cell(186, 6, f"Incident report {report['id']}  |  revision {report['revision']}  |  {incident['status']}")
    pdf.set_xy(12, 36)
    lines = [
        f"Site: East Panel Demonstration (schematic). Node: {incident['node_id']}.",
        f"Highest recorded severity: {incident['severity']}.",
        f"Opened: {incident['opened_at']}. Updated: {incident['updated_at']}.",
        f"Why it was flagged: {incident['explanation'][:420]}",
        "Model: prototype rules and robust window statistics. No trained ML artifact. Origin: " + incident.get("origin", "unavailable") + ".",
        f"Closure reason: {incident['closure_reason'] or 'Not closed.'}",
        "Actions: " + ("; ".join(f"{item['action']} at {item['at']}" for item in actions) or "None recorded."),
        "Rover: " + (f"{mission['id']} {mission['state']}" if mission else "No rover evidence linked."),
        f"Evidence link: {PUBLIC_URL}/incidents?focus={incident['id']}",
        "Origin of the frozen snapshot is stored with the report. This demonstration is not field certification.",
    ]
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(186, 4.6, "\n".join(lines).encode("latin-1", "replace").decode("latin-1"))
    tilts = [item.get("tilt_deg") for item in (incident.get("telemetry") or []) if isinstance(item.get("tilt_deg"), (int, float))]
    pdf.set_draw_color(157, 102, 56)
    pdf.rect(14, 168, 180, 28)
    if len(tilts) >= 2:
        low, high = min(tilts), max(tilts)
        span = high - low or 1
        coords = []
        for index, value in enumerate(tilts[:40]):
            x = 16 + (index / max(len(tilts[:40]) - 1, 1)) * 176
            y = 194 - ((value - low) / span) * 22
            coords.append((x, y))
        for start, end in zip(coords, coords[1:]):
            pdf.line(start[0], start[1], end[0], end[1])
    else:
        pdf.set_xy(18, 178)
        pdf.cell(0, 8, "Graph unavailable in the frozen snapshot.")
    pdf.set_xy(12, 202)
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(186, 4.6, "Follow-up: confirm sensor calibration and whether the movement remains after the next physical inspection. ML uncertainty: unavailable. Generated without an LLM. One page.")
    if pdf.page_no() != 1:
        raise RuntimeError("Closure report must stay on one page")
    return bytes(pdf.output())


def session_samples(conn: sqlite3.Connection, node_id: str, session_id: str) -> list[dict]:
    parsed = []
    found = conn.execute(
        "SELECT payload, sample_time, received_time, origin, valid, session_id, sequence FROM telemetry WHERE node_id=? AND session_id=? ORDER BY sequence",
        (node_id, session_id),
    ).fetchall()
    for row in found:
        payload = json.loads(row["payload"])
        payload.update({key: row[key] for key in ("sample_time", "received_time", "origin", "session_id", "sequence")})
        payload["valid"] = bool(row["valid"])
        parsed.append(payload)
    return parsed


def store_feature(conn: sqlite3.Connection, node_id: str, session_id: str, sequence: int) -> None:
    result = classify_window(session_samples(conn, node_id, session_id), [])
    conn.execute(
        """INSERT INTO features VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(node_id, session_id, sequence) DO UPDATE SET
           computed_at=excluded.computed_at, model_version=excluded.model_version, result=excluded.result""",
        (node_id, session_id, sequence, now(), MODEL_VERSION, json.dumps(result)),
    )


def create_job(conn: sqlite3.Connection, kind: str, payload: dict) -> str:
    job_id = f"JOB-{uuid4().hex[:10].upper()}"
    conn.execute(
        "INSERT INTO jobs VALUES (?, ?, 'PENDING', ?, NULL, 0, ?, ?)",
        (job_id, kind, json.dumps(payload), now(), now()),
    )
    return job_id


def job_view(row: sqlite3.Row) -> dict:
    return {key: row[key] for key in ("id", "kind", "status", "error", "attempts", "created_at", "updated_at")}


def execute_job(conn: sqlite3.Connection, job_id: str) -> dict:
    row = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Job not found")
    if row["status"] == "SUCCEEDED":
        raise HTTPException(409, "A completed job is not run again.")
    if row["status"] == "RUNNING":
        raise HTTPException(409, "This job is already running.")
    conn.execute("UPDATE jobs SET status='RUNNING', attempts=attempts+1, updated_at=? WHERE id=?", (now(), job_id))
    conn.commit()
    payload = json.loads(row["payload"])
    try:
        folder = evidence_dir()
        if row["kind"] == "telemetry_export":
            name = f"{job_id}.xlsx"
            (folder / name).write_bytes(workbook_bytes(conn))
            payload["file"] = name
        elif row["kind"] == "report_file":
            report = conn.execute("SELECT * FROM reports WHERE id=?", (payload.get("report_id"),)).fetchone()
            if not report:
                raise LookupError("Report not found")
            name = f"{job_id}.pdf"
            (folder / name).write_bytes(render_report_pdf(report))
            payload["file"] = name
        else:
            raise LookupError("Unknown job")
        conn.execute(
            "UPDATE jobs SET status='SUCCEEDED', payload=?, error=NULL, updated_at=? WHERE id=?",
            (json.dumps(payload), now(), job_id),
        )
    except Exception as exc:
        conn.execute(
            "UPDATE jobs SET status='FAILED', error=?, updated_at=? WHERE id=?",
            (str(exc)[:500], now(), job_id),
        )
    conn.commit()
    return job_view(conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone())


@app.post("/api/telemetry")
def ingest(reading: Reading) -> dict:
    if reading.node_id not in NODES:
        raise HTTPException(404, "Unknown node")
    if reading.origin not in {"physical", "simulated", "imported", "inferred"}:
        raise HTTPException(400, "origin must be physical, simulated, imported, or inferred")
    payload = reading.model_dump(exclude={"node_id", "session_id", "sequence", "sample_time", "origin", "valid"})
    if reading.node_id == "B":
        payload["temperature_note"] = "DS18B20 air temperature in degrees Celsius. Not soil moisture or groundwater."
    if reading.node_id == "C" and reading.linear_raw is not None:
        payload["linear_note"] = "Linear sensor model is not confirmed. Counts are not millimetres."
    if reading.node_id in {"A", "C"}:
        payload["potentiometer_mm"] = None
        payload["slider_note"] = "Slider counts are not millimetres until the slider is fixed and calibrated."
    if reading.origin == "physical" and reading.sample_time is None:
        raise HTTPException(422, "Physical readings require sample_time from the gateway clock.")
    if reading.origin == "physical" and (datetime.fromisoformat(reading.sample_time) - datetime.now(timezone.utc)).total_seconds() > 30:
        raise HTTPException(422, "Physical sample_time is ahead of the server clock; synchronize the gateway.")
    with connect() as conn:
        existing = conn.execute("SELECT origin FROM telemetry WHERE node_id=? AND session_id=? LIMIT 1", (reading.node_id, reading.session_id)).fetchone()
        if existing and existing["origin"] != reading.origin:
            raise HTTPException(409, "A session cannot mix data origins; start a new session.")
        session_id = reading.session_id
        stored_session = None
        sample_time = reading.sample_time or now()
        for _ in range(6):
            try:
                conn.execute(
                    "INSERT INTO telemetry (node_id, session_id, sequence, sample_time, received_time, origin, payload, valid) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        reading.node_id,
                        session_id,
                        reading.sequence,
                        sample_time,
                        now(),
                        reading.origin,
                        json.dumps(payload),
                        1 if reading.valid else 0,
                    ),
                )
                stored_session = session_id
                break
            except sqlite3.IntegrityError:
                previous = conn.execute(
                    "SELECT sample_time FROM telemetry WHERE node_id=? AND session_id=? AND sequence=?",
                    (reading.node_id, session_id, reading.sequence),
                ).fetchone()
                if not previous or sample_time <= (previous["sample_time"] or ""):
                    return {"stored": False, "duplicate": True}
                base, sep, generation = session_id.rpartition("~")
                if sep and generation.isdigit():
                    session_id = f"{base}~{int(generation) + 1}"
                else:
                    session_id = f"{session_id}~2"
        if stored_session is None:
            raise HTTPException(409, "Reading could not be stored")
        store_feature(conn, reading.node_id, stored_session, reading.sequence)
        conn.execute(
            "INSERT INTO link_events (node_id, session_id, sequence, kind, at) VALUES (?, ?, ?, 'accepted', ?)",
            (reading.node_id, stored_session, reading.sequence, now()),
        )
        refresh_conditions(conn)
        incident = conn.execute(
            "SELECT * FROM incidents WHERE node_id=? ORDER BY updated_at DESC LIMIT 1",
            (reading.node_id,),
        ).fetchone()
    return {"stored": True, "duplicate": False, "incident": dict(incident) if incident else None}



class SessionReview(BaseModel):
    label: Literal["unreviewed", "baseline", "movement", "disturbance", "sensor_fault"]
    note: str = Field(min_length=3, max_length=2000)


@app.get("/api/experiments")
def experiments() -> dict:
    with connect() as conn:
        groups = conn.execute("""SELECT node_id, session_id, origin, COUNT(*) sample_count,
            SUM(valid) valid_count, MIN(sample_time) started_at, MAX(sample_time) ended_at,
            MIN(sequence) first_sequence, MAX(sequence) last_sequence
            FROM telemetry GROUP BY node_id, session_id, origin ORDER BY MAX(id) DESC""").fetchall()
        result = []
        for group in groups:
            item = dict(group)
            review = conn.execute("SELECT label, note, reviewed_at FROM session_reviews WHERE node_id=? AND session_id=?", (item["node_id"], item["session_id"])).fetchone()
            item.update(dict(review) if review else {"label": "unreviewed", "note": "", "reviewed_at": None})
            item["sequence_gaps"] = max(0, item["last_sequence"] - item["first_sequence"] + 1 - item["sample_count"])
            item["coverage_pct"] = round(100 * item["valid_count"] / item["sample_count"], 1)
            result.append(item)
    physical = [x for x in result if x["origin"] == "physical"]
    return {"sessions": result, "readiness": {
        "physical_sessions": len(physical),
        "reviewed_physical_sessions": sum(x["label"] != "unreviewed" for x in physical),
        "trained_model": False,
        "next_step": "Collect independent calibrated experiments, review labels, and split by experiment before training. Session counts alone do not establish readiness."
    }}


@app.post("/api/experiments/{node_id}/{session_id}/review")
def review_session(node_id: str, session_id: str, body: SessionReview, x_mole_capability: str | None = Header(default=None)):
    require_operator(x_mole_capability)
    if len(body.note.strip()) < 3:
        raise HTTPException(422, "A meaningful annotation note is required.")
    with connect() as conn:
        if not conn.execute("SELECT 1 FROM telemetry WHERE node_id=? AND session_id=?", (node_id, session_id)).fetchone():
            raise HTTPException(404, "Session not found")
        conn.execute("INSERT INTO session_reviews VALUES (?, ?, ?, ?, ?) ON CONFLICT(node_id,session_id) DO UPDATE SET label=excluded.label,note=excluded.note,reviewed_at=excluded.reviewed_at", (node_id, session_id, body.label, body.note.strip(), now()))
    return {"saved": True, "label": body.label}


@app.get("/api/experiments/{node_id}/{session_id}/export")
def export_session(node_id: str, session_id: str):
    with connect() as conn:
        found = conn.execute("SELECT * FROM telemetry WHERE node_id=? AND session_id=? ORDER BY sequence", (node_id, session_id)).fetchall()
        if not found:
            raise HTTPException(404, "Session not found")
        review = conn.execute("SELECT label, note, reviewed_at FROM session_reviews WHERE node_id=? AND session_id=?", (node_id, session_id)).fetchone()
    records = [{**json.loads(r["payload"]), **{k:r[k] for k in ("node_id","session_id","sequence","sample_time","received_time","origin")}, "valid": bool(r["valid"])} for r in found]
    return {"schema_version": "mole-experiment-v1", "annotation": dict(review) if review else None, "readings": records}


@app.post("/api/incidents/{incident_id}/acknowledge")
def acknowledge(incident_id: str, body: ActionIn, x_mole_capability: str | None = Header(default=None)) -> dict:
    require_operator(x_mole_capability)
    with connect() as conn:
        row = conn.execute("SELECT * FROM incidents WHERE id=?", (incident_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Incident not found")
        if row["status"] != "OPEN":
            raise HTTPException(409, "Only open incidents can be acknowledged.")
        conn.execute("UPDATE incidents SET status='ACKNOWLEDGED', updated_at=? WHERE id=?", (now(), incident_id))
        conn.execute(
            "INSERT INTO actions (incident_id, action, reason, actor, at) VALUES (?, 'ACKNOWLEDGED', ?, 'paired-device', ?)",
            (incident_id, body.reason, now()),
        )
    return {"status": "ACKNOWLEDGED", "note": "Acknowledgement does not resolve the incident."}


@app.post("/api/incidents/{incident_id}/review")
def review(incident_id: str, body: ActionIn, x_mole_capability: str | None = Header(default=None)) -> dict:
    require_operator(x_mole_capability)
    with connect() as conn:
        row = conn.execute("SELECT status FROM incidents WHERE id=?", (incident_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Incident not found")
        if row["status"] != "ACKNOWLEDGED":
            raise HTTPException(409, "Acknowledge this incident before recording the review.")
        conn.execute(
            "UPDATE incidents SET status='RECOVERED/PENDING REVIEW', updated_at=? WHERE id=?",
            (now(), incident_id),
        )
        conn.execute(
            "INSERT INTO actions (incident_id, action, reason, actor, at) VALUES (?, 'PENDING_REVIEW', ?, 'paired-device', ?)",
            (incident_id, body.reason, now()),
        )
    return {"status": "RECOVERED/PENDING REVIEW"}


@app.post("/api/incidents/{incident_id}/close")
def close(incident_id: str, body: ActionIn, x_mole_capability: str | None = Header(default=None)) -> dict:
    require_operator(x_mole_capability)
    with connect() as conn:
        row = conn.execute("SELECT * FROM incidents WHERE id=?", (incident_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Incident not found")
        if row["status"] != "RECOVERED/PENDING REVIEW":
            raise HTTPException(409, "Close only after pending review. Missing data cannot establish recovery.")
        conn.execute(
            "UPDATE incidents SET status='CLOSED', closure_reason=?, updated_at=? WHERE id=?",
            (body.reason, now(), incident_id),
        )
        conn.execute(
            "INSERT INTO actions (incident_id, action, reason, actor, at) VALUES (?, 'CLOSED', ?, 'paired-device', ?)",
            (incident_id, body.reason, now()),
        )
        revision = conn.execute("SELECT COUNT(*) c FROM reports WHERE incident_id=?", (incident_id,)).fetchone()["c"] + 1
        report_id = f"RPT-{incident_id}-R{revision}"
        snapshot = dict(row) | {"closure_reason": body.reason, "status": "CLOSED", "updated_at": now()}
        snapshot["actions"] = [dict(a) for a in conn.execute("SELECT action, reason, at FROM actions WHERE incident_id=? ORDER BY id", (incident_id,))]
        snapshot["telemetry"] = rows(conn, row["node_id"])
        linked_mission = conn.execute("SELECT id, state, evidence FROM missions WHERE incident_id=? ORDER BY created_at DESC LIMIT 1", (incident_id,)).fetchone()
        snapshot["mission"] = dict(linked_mission) if linked_mission else None
        conn.execute(
            "INSERT INTO reports VALUES (?, ?, ?, ?, ?)",
            (report_id, incident_id, revision, now(), json.dumps(snapshot)),
        )
        job_id = create_job(conn, "report_file", {"report_id": report_id})
        execute_job(conn, job_id)
    return {"status": "CLOSED", "report_id": report_id}


@app.post("/api/sos")
def sos(body: SosIn) -> dict:
    note = "Received by the server. No external responder delivery provider is configured."
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        if body.request_id:
            existing = conn.execute("SELECT s.id, s.status FROM sos_receipts r JOIN sos s ON s.id=r.sos_id WHERE r.request_id=?", (body.request_id,)).fetchone()
            if existing:
                return {**dict(existing), "duplicate": True, "note": note}
        sos_id = f"SOS-{uuid4().hex.upper()}"
        conn.execute("INSERT INTO sos VALUES (?, 'QUEUED', ?, ?, ?, ?, ?, ?, ?, ?, 'physical')",
            (sos_id, body.lat, body.lon, body.accuracy_m, body.located_at, body.landmark, body.message, body.contact, now()))
        if body.request_id:
            conn.execute("INSERT INTO sos_receipts VALUES (?, ?)", (body.request_id, sos_id))
    return {"id": sos_id, "status": "QUEUED", "duplicate": False, "note": note}


@app.get("/api/sos/operator")
def operator_sos(x_mole_capability: str | None = Header(default=None)):
    require_operator(x_mole_capability)
    with connect() as conn:
        return {"requests": [dict(r) for r in conn.execute("SELECT * FROM sos ORDER BY created_at DESC LIMIT 100")]}


@app.post("/api/sos/{sos_id}/acknowledge")
def acknowledge_sos(sos_id: str, body: ActionIn, x_mole_capability: str | None = Header(default=None)):
    require_operator(x_mole_capability)
    with connect() as conn:
        row = conn.execute("SELECT status FROM sos WHERE id=?", (sos_id,)).fetchone()
        if not row:
            raise HTTPException(404, "SOS not found")
        if row["status"] != "QUEUED":
            raise HTTPException(409, "This SOS has already been acknowledged")
        conn.execute("UPDATE sos SET status='ACKNOWLEDGED' WHERE id=?", (sos_id,))
        conn.execute("INSERT INTO actions (incident_id, action, reason, actor, at) VALUES (?, 'SOS_ACKNOWLEDGED', ?, 'paired-device', ?)", (sos_id, body.reason, now()))
    return {"status": "ACKNOWLEDGED", "note": "Operator acknowledgement recorded. This does not confirm rescue or external dispatch."}


@app.post("/api/missions")
def mission(body: MissionIn, x_mole_capability: str | None = Header(default=None)) -> dict:
    require_operator(x_mole_capability)
    mission_id = f"MSN-{uuid4().hex[:6].upper()}"
    with connect() as conn:
        if not conn.execute("SELECT id FROM incidents WHERE id=?", (body.incident_id,)).fetchone():
            raise HTTPException(404, "Incident not found")
        previous = [item["id"] for item in conn.execute("SELECT id FROM missions WHERE incident_id=? ORDER BY created_at", (body.incident_id,))]
        conn.execute(
            "INSERT INTO missions (id, incident_id, state, note, created_at, evidence) VALUES (?, ?, 'PLANNED', ?, ?, '[]')",
            (mission_id, body.incident_id, body.note, now()),
        )
        save_checklist(conn, mission_id, fresh_checklist())
    return {"id": mission_id, "state": "PLANNED", "mode": "simulation", "unit": "R1", "previous_mission_ids": previous, "drive": "not enabled"}


@app.post("/api/missions/{mission_id}/evidence")
def evidence(mission_id: str, body: EvidenceIn, x_mole_capability: str | None = Header(default=None)) -> dict:
    require_operator(x_mole_capability)
    with connect() as conn:
        row = conn.execute("SELECT * FROM missions WHERE id=?", (mission_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Mission not found")
        record = {"note": body.note, "finding": body.finding, "at": now(), "origin": "simulated"}
        blob = json.dumps(record).encode()
        object_id = f"EVD-{uuid4().hex[:10].upper()}"
        file_name = f"{object_id}.json"
        (evidence_dir() / file_name).write_bytes(blob)
        conn.execute(
            "INSERT INTO evidence_objects VALUES (?, ?, ?, ?, ?, 'simulated', ?)",
            (object_id, mission_id, file_name, hashlib.sha256(blob).hexdigest(), len(blob), record["at"]),
        )
        items = json.loads(row["evidence"])
        items.append({**record, "object_id": object_id, "dimensions_inferred": False})
        conn.execute("UPDATE missions SET state='EVIDENCE ATTACHED', evidence=? WHERE id=?", (json.dumps(items), mission_id))
        meta = conn.execute("SELECT checklist FROM mission_meta WHERE mission_id=?", (mission_id,)).fetchone()
        checklist = json.loads(meta["checklist"]) if meta else fresh_checklist()
        for item in checklist:
            if item["id"] == "observation":
                item["done"] = True
        save_checklist(conn, mission_id, checklist)
    return {"state": "EVIDENCE ATTACHED", "finding": body.finding, "dimensions_inferred": False}


@app.post("/api/commands")
def command(body: CommandIn, x_mole_capability: str | None = Header(default=None)) -> dict:
    require_operator(x_mole_capability)
    expires = datetime.fromisoformat(body.expires_at)
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    with connect() as conn:
        if not conn.execute("SELECT id FROM missions WHERE id=?", (body.mission_id,)).fetchone():
            raise HTTPException(404, "Mission not found")
        active = conn.execute("SELECT id FROM commands WHERE status='ACTIVE' AND mission_id=?", (body.mission_id,)).fetchone()
        if active:
            raise HTTPException(409, "One controller is already recorded for this mission.")
        status = "EXPIRED" if expires <= datetime.now(timezone.utc) else "NOT_EXECUTED"
        conn.execute(
            "INSERT INTO commands VALUES (?, ?, ?, ?, ?, ?)",
            (f"CMD-{uuid4().hex[:6]}", body.mission_id, body.kind, body.expires_at, status, now()),
        )
    if status == "EXPIRED":
        return {"executed": False, "status": "EXPIRED", "note": "Stale movement commands are not executed."}
    raise HTTPException(409, "Physical driving is unavailable until the rover controller and protocol are confirmed. Simulation cannot issue motion.")


@app.get("/api/missions/{mission_id}")
def mission_detail(mission_id: str) -> dict:
    with connect() as conn:
        row = conn.execute("SELECT * FROM missions WHERE id=?", (mission_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Mission not found")
        detail = decorate_mission(conn, dict(row))
        incident = conn.execute("SELECT node_id FROM incidents WHERE id=?", (row["incident_id"],)).fetchone()
        others = conn.execute(
            """SELECT m.id FROM missions m JOIN incidents i ON i.id=m.incident_id
               WHERE i.node_id=? AND m.id!=? ORDER BY m.created_at""",
            (incident["node_id"], mission_id),
        ).fetchall()
    return {**detail, "same_node_mission_ids": [item["id"] for item in others], "distinct_from": "Node C"}


@app.post("/api/missions/{mission_id}/position")
def mission_position(mission_id: str, body: PositionIn, x_mole_capability: str | None = Header(default=None)) -> dict:
    require_operator(x_mole_capability)
    if body.known:
        raise HTTPException(409, "Position cannot be marked known until localization is confirmed.")
    with connect() as conn:
        row = conn.execute("SELECT checklist FROM mission_meta WHERE mission_id=?", (mission_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Mission not found")
        checklist = json.loads(row["checklist"])
        for item in checklist:
            if item["id"] == "position_recorded":
                item["done"] = True
        position = {"known": False, "uncertainty_m": None, "note": body.note.strip()}
        save_checklist(conn, mission_id, checklist, position)
        done = all(item["done"] for item in checklist)
    return {"known": False, "inspection_complete": done}


@app.post("/api/missions/{mission_id}/link-lost")
def link_lost(mission_id: str, x_mole_capability: str | None = Header(default=None)) -> dict:
    require_operator(x_mole_capability)
    with connect() as conn:
        if not conn.execute("SELECT id FROM missions WHERE id=?", (mission_id,)).fetchone():
            raise HTTPException(404, "Mission not found")
        conn.execute(
            "INSERT INTO commands VALUES (?, ?, 'link-lost', ?, 'NOT_EXECUTED', ?)",
            (f"CMD-{uuid4().hex[:6]}", mission_id, now(), now()),
        )
    return {"executed": False, "status": "NOT_EXECUTED", "note": "No vehicle stop is implemented. The lost link was recorded only."}


@app.get("/api/exports/telemetry.xlsx")
def export_xlsx() -> Response:
    with connect() as conn:
        content = workbook_bytes(conn)
    return Response(
        content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=mole-telemetry.xlsx"},
    )


@app.get("/api/exports/telemetry.csv")
def export_csv() -> Response:
    with connect() as conn:
        buffer = io.StringIO()
        csv.writer(buffer).writerows(telemetry_table(conn))
    return Response(buffer.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=mole-telemetry.csv"})


def parse_import(text: str) -> tuple[list[dict], list[str]]:
    reader = csv.DictReader(io.StringIO(text))
    required = {"node_id", "sample_time", "channel", "value", "unit"}
    if not reader.fieldnames or not required <= set(reader.fieldnames):
        return [], ["Columns must include node_id, sample_time, channel, value, and unit."]
    rows = []
    issues = []
    seen = set()
    for index, row in enumerate(reader, start=2):
        node_id = (row.get("node_id") or "").strip()
        channel = (row.get("channel") or "").strip()
        raw_time = (row.get("sample_time") or "").strip()
        raw_value = (row.get("value") or "").strip()
        if node_id not in NODES:
            issues.append(f"Row {index}: unknown node.")
            continue
        if channel not in CHANNEL_UNITS:
            issues.append(f"Row {index}: unknown channel.")
            continue
        if (row.get("unit") or "").strip() != CHANNEL_UNITS[channel]:
            issues.append(f"Row {index}: unit does not match {channel}.")
            continue
        try:
            parsed = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
        except ValueError:
            issues.append(f"Row {index}: sample_time is not a timestamp.")
            continue
        if parsed.tzinfo is None:
            issues.append(f"Row {index}: sample_time needs a timezone.")
            continue
        key = (node_id, parsed.isoformat(), channel)
        if key in seen:
            issues.append(f"Row {index}: duplicate reading.")
            continue
        seen.add(key)
        if raw_value in {"", "unavailable"}:
            value = None
        else:
            try:
                value = float(raw_value)
            except ValueError:
                issues.append(f"Row {index}: value is not a number or unavailable.")
                continue
        rows.append({"node_id": node_id, "sample_time": parsed.astimezone(timezone.utc).isoformat(), "channel": channel, "value": value, "unit": CHANNEL_UNITS[channel]})
    return rows, issues


@app.get("/api/history")
def history(node_id: str, channel: str = "tilt_deg", limit: int = Query(default=24, ge=1, le=200)) -> dict:
    if node_id not in NODES or channel not in CHANNEL_UNITS:
        raise HTTPException(404, "Unknown node or channel")
    points = []
    previous = None
    with connect() as conn:
        for row in conn.execute("SELECT * FROM telemetry WHERE node_id=? ORDER BY sample_time, sequence", (node_id,)):
            payload = json.loads(row["payload"])
            if channel not in payload:
                continue
            if previous is not None and row["sequence"] > previous + 1 and row["session_id"] == points[-1].get("session_id"):
                points.append({"gap": True, "after_sequence": previous})
            previous = row["sequence"]
            value = payload[channel]
            points.append({"sample_time": row["sample_time"], "value": None if value is None or not row["valid"] else value, "valid": bool(row["valid"]), "origin": row["origin"], "unit": CHANNEL_UNITS[channel], "session_id": row["session_id"], "gap": False})
    readings = [item for item in points if not item["gap"]]
    step = max(1, (len(readings) + limit - 1) // limit) if readings else 1
    shown = readings[::step]
    if readings and shown[-1] is not readings[-1]:
        shown.append(readings[-1])
    return {"node_id": node_id, "channel": channel, "original_count": len(readings), "returned_count": len(shown), "points": shown, "gaps": [item for item in points if item["gap"]]}


@app.post("/api/imports/preview")
def import_preview(body: ImportIn) -> dict:
    rows, issues = parse_import(body.csv_text)
    import_id = f"IMP-{uuid4().hex[:10].upper()}"
    stored_name = f"{import_id}.csv"
    (evidence_dir() / stored_name).write_text(body.csv_text, encoding="utf-8")
    with connect() as conn:
        conn.execute(
            "INSERT INTO imports VALUES (?, ?, ?, ?, 'PREVIEW', ?, ?)",
            (import_id, body.filename, stored_name, now(), json.dumps(issues), json.dumps(rows)),
        )
    return {"id": import_id, "rows": len(rows), "issues": issues, "source_kept": True}


@app.post("/api/imports/{import_id}/commit")
def import_commit(import_id: str, x_mole_capability: str | None = Header(default=None)) -> dict:
    require_operator(x_mole_capability)
    with connect() as conn:
        row = conn.execute("SELECT * FROM imports WHERE id=?", (import_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Import not found")
        if row["status"] == "COMMITTED":
            raise HTTPException(409, "This import was already committed.")
        issues = json.loads(row["issues"])
        if issues:
            raise HTTPException(409, "Fix the preview issues before committing.")
        stored = 0
        for sequence, item in enumerate(json.loads(row["rows_json"])):
            payload = {item["channel"]: item["value"]}
            try:
                conn.execute(
                    "INSERT INTO telemetry (node_id, session_id, sequence, sample_time, received_time, origin, payload, valid) VALUES (?, ?, ?, ?, ?, 'imported', ?, ?)",
                    (item["node_id"], import_id, sequence, item["sample_time"], now(), json.dumps(payload), 0 if item["value"] is None else 1),
                )
                stored += 1
            except sqlite3.IntegrityError:
                continue
        conn.execute("UPDATE imports SET status='COMMITTED' WHERE id=?", (import_id,))
    return {"stored": stored, "origin": "imported", "source_file": row["stored_name"]}


@app.get("/api/reports/{report_id}.pdf")
def report_pdf(report_id: str) -> Response:
    with connect() as conn:
        report = conn.execute("SELECT * FROM reports WHERE id=?", (report_id,)).fetchone()
        if not report:
            raise HTTPException(404, "Report not found")
        content = render_report_pdf(report)
    return Response(content, media_type="application/pdf", headers={"Content-Disposition": f"inline; filename={report_id}.pdf"})


@app.post("/api/jobs")
def enqueue(body: JobIn) -> dict:
    with connect() as conn:
        job_id = create_job(conn, body.kind, {"report_id": body.report_id} if body.report_id else {})
        return execute_job(conn, job_id)


@app.get("/api/jobs")
def list_jobs() -> dict:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT 50").fetchall()
    return {"jobs": [job_view(row) for row in rows]}


@app.post("/api/jobs/{job_id}/retry")
def retry_job(job_id: str) -> dict:
    with connect() as conn:
        return execute_job(conn, job_id)


@app.get("/api/jobs/{job_id}/file")
def job_file(job_id: str) -> Response:
    with connect() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    if not row or row["status"] != "SUCCEEDED":
        raise HTTPException(404, "Completed job file not found")
    name = json.loads(row["payload"]).get("file")
    path = (evidence_dir() / name).resolve()
    if not name or evidence_dir().resolve() not in path.parents or not path.is_file():
        raise HTTPException(404, "Completed job file not found")
    media = "application/pdf" if path.suffix == ".pdf" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return Response(path.read_bytes(), media_type=media, headers={"Content-Disposition": f"attachment; filename={path.name}"})


@app.get("/api/calibrations")
def list_calibrations() -> dict:
    with connect() as conn:
        records = [dict(row) for row in conn.execute(
            "SELECT id, node_id, channel, mode, baseline_value, reference_value, tolerance, sample_count, status, unit, note, created_at FROM calibrations ORDER BY id DESC"
        )]
    return {"records": records, "effect": "An active tilt baseline is used by the prototype movement rule. Other records document calibration only; raw readings are never rewritten, converted to millimetres, or relabelled as engineering units."}


@app.post("/api/calibrations")
def add_calibration(body: CalibrationIn, x_mole_capability: str | None = Header(default=None)) -> dict:
    require_operator(x_mole_capability)
    if body.node_id not in NODES:
        raise HTTPException(404, "Unknown node")
    if body.channel not in NODES[body.node_id]["channels"]:
        raise HTTPException(422, "That channel is not installed on this node")
    if body.mode == "baseline" and body.baseline_value is None:
        raise HTTPException(422, "A baseline value is required")
    with connect() as conn:
        if body.status == "active":
            conn.execute(
                "UPDATE calibrations SET status='superseded' WHERE node_id=? AND channel=? AND status='active'",
                (body.node_id, body.channel),
            )
        conn.execute(
            """INSERT INTO calibrations
               (node_id, channel, note, created_at, mode, baseline_value, reference_value,
                tolerance, sample_count, status, unit)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (body.node_id, body.channel, body.note, now(), body.mode, body.baseline_value,
             body.reference_value, body.tolerance, body.sample_count, body.status, body.unit),
        )
        if body.channel == "tilt_deg" and body.status == "active":
            refresh_conditions(conn)
    return {"saved": True, "readings_changed": False, "analysis_reference_changed": body.channel == "tilt_deg" and body.status == "active"}


@app.post("/api/sync-jobs")
def record_sync(body: SyncIn) -> dict:
    sync_id = f"SYNC-{uuid4().hex[:10].upper()}"
    with connect() as conn:
        conn.execute(
            "INSERT INTO sync_jobs VALUES (?, ?, ?, ?, ?, ?)",
            (sync_id, body.source, body.sent, body.pending, body.rejected, now()),
        )
    return {"id": sync_id, "stored": True}


@app.get("/api/sync-jobs")
def list_sync() -> dict:
    with connect() as conn:
        rows = [dict(row) for row in conn.execute("SELECT * FROM sync_jobs ORDER BY created_at DESC LIMIT 50")]
    return {"jobs": rows}


@app.get("/api/events")
def events() -> StreamingResponse:
    def stream():
        last = ""
        while True:
            body = json.dumps(state(), default=str)
            if body != last:
                yield f"data: {body}\n\n"
                last = body
            else:
                yield "event: ping\ndata: {}\n\n"
            time.sleep(1)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/assistant/status")
def assistant_status() -> dict:
    status = llm_status()
    return {
        "ready": status["ok"],
        "provider": status["provider"],
        "model": status["model"],
        "companion": "Mole",
    }


@app.post("/api/assistant")
def assistant(body: AssistantIn):
    question = body.question.strip()
    snapshot = state()
    messages = build_messages(
        question, [item.model_dump() for item in body.history], snapshot
    )
    sources = related_sources(question, snapshot)
    status = llm_status()

    if not body.stream:
        try:
            answer = "".join(iter_llm_tokens(messages))
        except LLMUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return {
            "provider": status["provider"],
            "model": status["model"],
            "answer": answer,
            "sources": sources,
            "companion": "Mole",
        }

    def generate():
        yield f"event: meta\ndata: {json.dumps({'provider': status['provider'], 'model': status['model'], 'companion': 'Mole'})}\n\n"
        collected = []
        try:
            for token in iter_llm_tokens(messages):
                collected.append(token)
                yield f"event: token\ndata: {json.dumps({'text': token})}\n\n"
        except LLMUnavailable as exc:
            yield f"event: error\ndata: {json.dumps({'detail': str(exc)})}\n\n"
            return
        except Exception:
            yield f"event: error\ndata: {json.dumps({'detail': 'Mole could not finish that answer.'})}\n\n"
            return
        yield f"event: done\ndata: {json.dumps({'answer': ''.join(collected), 'sources': sources, 'provider': status['provider'], 'model': status['model']})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
