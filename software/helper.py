"""Pip helper: Mistral API first, local Ollama fallback, then FAQ."""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Optional

import requests

STOP = {
    "a", "an", "and", "are", "can", "do", "does", "for", "how", "i", "in", "is",
    "it", "me", "my", "of", "on", "or", "please", "tell", "the", "this", "to",
    "us", "we", "what", "when", "where", "which", "who", "why", "with", "you",
}

DISCLAIMER = "Laptop helper. Not a mine-safety certificate. Product AI is sklearn."
FAST_SYSTEM = """You are Pip, a friendly laptop assistant for the MOLE tabletop demo (SIH26025, team WE COOK).

Help with whatever the operator asks: this dashboard, live Node A/B/rover numbers, flashing, wiring, calibration, demo script, troubleshooting, writing a short pitch line, checklists, explanations, and ordinary assistant questions.

You are a helper, not the product mine-AI. Product AI is sklearn on the laptop (Isolation Forest + LOF + joint forest + 30 s sensor-trend forecast with MAE).

Hard limits — never violate, even if asked:
- No collapse / subsidence probability, and never say a roof will fail.
- No CO ppm from the uncalibrated MQ-7 (raw ADC + local HIGH/NORMAL only).
- Green/NORMAL is not a certified-safe mine.
- Rover is remote hold-to-move. IR GPIO19 does not auto-brake. No autonomy, no LoRa, no camera vision.
- Do not invent boards, pins, or radio paths.

When the question is about this rig, use the LIVE RIG JSON and these facts. When it is general, answer it helpfully in plain language, then offer a useful next step on this tabletop if it fits.

Facts: Node A ESP32 MPU GPIO21/22 + 10 kΩ slider GPIO34. Node B same MPU, no slider. Receiver Waveshare ESP32-S3-Zero USB JSON 115200. Rover AP Mine-Rover-AP 192.168.4.1; L298N 13/12/14/27; IR GPIO19 does not stop motors; MQ-7 GPIO36 raw ADC not ppm.
Rules: WATCH 3°/2 mm ×3; ALERT 6°/4 mm latches; UNKNOWN >5 s. ML cannot clear a latch.

Be warm, concrete, and useful. Prefer 5–10 short sentences or a short checklist. Use millimetres, degrees, GPIOs, and file names when relevant. If you are unsure, say so.
"""
ROOT = Path(__file__).resolve().parent
MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"
MISTRAL_MODELS_URL = "https://api.mistral.ai/v1/models"
OLLAMA = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
PREFERRED_MODELS = (
    "mistral",
    "mistral:latest",
    "mistral:instruct",
    "mistral:7b",
    "llama3.1:8b",
    "llama3.1",
    "qwen2.5-coder:7b",
)
_model_cache: dict[str, Any] = {"t": 0.0, "name": None}
_last_llm_error: Optional[str] = None
_quota_dead_until = 0.0


def _load_dotenv() -> None:
    """Load software/.env and repo .env without overriding a real environment variable."""
    for path in (ROOT / ".env", ROOT.parent / ".env"):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for raw in text.splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("'").strip('"')
            if key and key not in os.environ:
                os.environ[key] = value


_load_dotenv()
OLLAMA = os.environ.get("OLLAMA_HOST", OLLAMA).rstrip("/")

FAQ: list[dict[str, Any]] = [
    {
        "id": "hello",
        "keys": ("hello", "hi", "hey", "who are you", "your name", "assistant", "who is pip"),
        "answer": (
            "I'm Pip, your helper and assistant for this MOLE tabletop. Ask me anything: "
            "flashing, Node A/B, the S3-Zero USB receiver, rules, sklearn, calibration, "
            "the rover, the demo script, or a general question. I will warn you if a "
            "claim is too strong. I do not guess geology or collapse probability."
        ),
    },
    {
        "id": "mole",
        "keys": ("mole", "project", "sih", "sih26025", "hackathon", "we cook", "what is mole"),
        "answer": (
            "MOLE is a tabletop mine-monitoring demo for SIH26025 (Ministry of Coal). "
            "Node A + Node B watch tilt/vibration/crack, the laptop runs rules + "
            "Isolation Forest + a 30 s sensor forecast, then you inspect with a remote rover. "
            "Readings show disturbance on this rig. They do not prove a collapse."
        ),
    },
    {
        "id": "flash",
        "keys": (
            "flash", "upload", "arduino", "firmware", "put code", "program",
            "sketch", "ino", "board", "hardware", "the code",
        ),
        "answer": (
            "Use Arduino IDE, one USB board at a time. Node A: firmware/node/node.ino "
            "(ESP32 Dev Module). Node B: firmware/node_b/node.ino. Receiver: "
            "firmware/receiver_s3/receiver_s3.ino on the Waveshare ESP32-S3-Zero with "
            "USB CDC On Boot Enabled. Rover: firmware/rover/rover.ino. If upload stalls, "
            "hold BOOT, tap RESET, then upload."
        ),
    },
    {
        "id": "nodes",
        "keys": ("node a", "node b", "slider", "mpu", "crack", "fixed node"),
        "answer": (
            "Both nodes are classic ESP32-WROOM-32 + MPU6050 on GPIO21/22. Node A has "
            "the 10 kΩ crack slider on GPIO34 (NODE_ID 1). Node B is comparison only, "
            "no slider (NODE_ID 2). They send ESP-NOW on channel 1. They do not compute "
            "alerts or millimetres — the laptop does."
        ),
    },
    {
        "id": "receiver",
        "keys": ("receiver", "s3", "usb", "com port", "serial", "json", "s3-zero"),
        "answer": (
            "The Waveshare ESP32-S3-Zero receives ESP-NOW and prints one JSON line per "
            "packet at 115200. No sensors on that board. Plug it into the laptop, prove "
            "node_id 1 and 2 in Serial Monitor, close the monitor, then "
            "python app.py --mode live --serial auto. Live never fakes data if USB drops."
        ),
    },
    {
        "id": "run",
        "keys": ("run", "website", "dashboard", "simulate", "live", "flask", "localhost"),
        "answer": (
            "From software/: python app.py --mode simulate for rehearsal, or "
            "--mode live --serial auto after the S3-Zero is talking. Then open "
            "http://127.0.0.1:5000/monitoring and /rover. Simulate is labelled and "
            "cannot persist-train Isolation Forest."
        ),
    },
    {
        "id": "rules",
        "keys": ("rule", "watch", "alert", "unknown", "latch", "threshold", "tilt", "warning"),
        "answer": (
            "Tabletop rules (not mine trigger levels): WATCH if tilt ≥ 3° or crack ≥ 2 mm "
            "for 3 samples; ALERT if ≥ 6° or ≥ 4 mm for 3 samples. ALERT latches. "
            "UNKNOWN means stale (>5 s), invalid IMU, or Node A slider not calibrated. "
            "Ack records awareness. Clear needs 3 fresh NORMAL samples. ML cannot clear a latch."
        ),
    },
    {
        "id": "ml",
        "keys": (
            "ml", "ai", "isolation", "forest", "lof", "ridge", "forecast",
            "sklearn", "prediction", "anomaly", "model",
        ),
        "answer": (
            "Laptop sklearn only: Isolation Forest + LOF vs this rig's normal, a joint "
            "A-vs-B forest, and a holdout-selected 30 s forecast of tilt / vibration / "
            "crack mm with MAE. Priors are quiet-tabletop, not a real mine. This is not "
            "a collapse probability and not a chatbot brain."
        ),
    },
    {
        "id": "calibrate",
        "keys": ("calibrat", "baseline", "slider", "adc", "millimetre", "mm"),
        "answer": (
            "Keep mounts still. Capture Baseline A then Baseline B. For the Node A slider, "
            "record ADC+mm at two different ruler positions and save two-point calibration. "
            "Node A cannot show NORMAL until that scale exists. Changing calibration resets "
            "Node A anomaly features."
        ),
    },
    {
        "id": "ack",
        "keys": ("ack", "acknowledge", "clear", "reset alert", "inspection done"),
        "answer": (
            "Ack only records that you saw the warning. It does not erase history and does "
            "not un-latch ALERT. After you inspect with the rover, click Inspection done on "
            "monitoring — that closes recovered latches on Node A and Node B together. "
            "If a node is still over the tabletop ALERT threshold, recover the mount first. "
            "Clear A/B still needs 3 consecutive NORMAL samples. Isolation Forest cannot clear a rule."
        ),
    },
    {
        "id": "green",
        "keys": ("green", "normal", "safe", "colour", "color", "badge"),
        "answer": (
            "NORMAL / green means fresh valid packets and no configured tabletop trigger. "
            "It does not certify a mine, a roof, or a workplace as safe."
        ),
        "warn": True,
    },
    {
        "id": "rover",
        "keys": ("rover", "drive", "motor", "wifi", "mine-rover", "inspect", "wheels", "raise"),
        "answer": (
            "Rover is a core unit on its own Wi-Fi AP Mine-Rover-AP (192.168.4.1), not ESP-NOW. "
            "Join that AP, open /rover, raise wheels first, then hold FWD/REV/LEFT/RIGHT. "
            "Release or Space sends STOP. Firmware also stops after 400 ms. Driving is remote, "
            "not autonomous. Open rover because a warning appeared — not as a maze robot."
        ),
    },
    {
        "id": "ir",
        "keys": ("ir", "infrared", "gpio19", "obstacle", "brake"),
        "answer": (
            "IR OUT is GPIO19, active LOW = near. It is a digital flag, not range, and it "
            "does not stop the motors. Do not treat it as collision avoidance."
        ),
        "warn": True,
    },
    {
        "id": "sonar",
        "keys": ("ultrasonic", "hc-sr04", "distance", "echo", "sonar"),
        "answer": (
            "HC-SR04 TRIG=GPIO5, ECHO=GPIO18 after a 1 kΩ / 2 kΩ divider. Never feed 5 V "
            "ECHO into the ESP32. The dashboard shows centimetres, not a lidar map."
        ),
    },
    {
        "id": "mq7",
        "keys": ("mq-7", "mq7", "gas", "carbon", "co", "ppm"),
        "answer": (
            "MQ-7 on GPIO36 is raw 12-bit ADC plus a local NORMAL/HIGH flag (threshold 2500). "
            "It is not calibrated CO ppm. Do not quote parts-per-million from this sensor."
        ),
        "warn": True,
    },
    {
        "id": "pins",
        "keys": ("pin", "gpio", "l298", "wiring", "wire"),
        "answer": (
            "Frozen pins: MPU 21/22; Node A slider GPIO34 via 1 kΩ; rover L298N IN1=13 IN2=12 "
            "IN3=14 IN4=27; IR=19; ultrasonic 5/18; MQ-7=36. Leave L298N ENA/ENB jumpers ON. "
            "GPIO19 is IR, not a motor pin. Do not invent a new board or radio path."
        ),
    },
    {
        "id": "demo",
        "keys": ("demo", "judge", "pitch", "script", "rehearsal", "rising"),
        "answer": (
            "Show both nodes updating, name Isolation Forest + forecast MAE, then Rising trend "
            "or a real Node A tilt while B stays quieter. WATCH → ALERT with the measured reason. "
            "Open Rover Inspection because a warning appeared. Say it is not collapse %."
        ),
    },
    {
        "id": "notllm",
        "keys": ("llm", "chatgpt", "chatbot", "camera", "vision", "login", "cloud", "lora"),
        "answer": (
            "I am Pip, a helper chatbot. I am not the product mine-AI. The SIH AI pillar is "
            "sklearn on the laptop: Isolation Forest + a 30 s sensor-trend forecast. There is "
            "no camera vision, login, LoRa, or collapse %."
        ),
    },
    {
        "id": "train",
        "keys": ("train", "prior", "joblib", "120"),
        "answer": (
            "Tabletop prior .joblib files already load so Isolation Forest can be READY. "
            "They describe quiet-tabletop NORMAL, not your physical MPU. Optional live retrain "
            "needs ≥120 NORMAL samples, live mode only, and is blocked during WATCH/ALERT/UNKNOWN."
        ),
    },
    {
        "id": "stale",
        "keys": ("stale", "offline", "unknown", "no data", "waiting"),
        "answer": (
            "If a node is UNKNOWN: check power, ESP-NOW channel 1, S3-Zero USB, 115200 JSON, "
            "and that Serial Monitor is closed. Live mode retries USB every 2 s and never "
            "silently switches to simulation. Nodes go UNKNOWN after 5 s without a valid packet."
        ),
    },
    {
        "id": "now",
        "keys": (
            "happening now", "right now", "live status", "current status",
            "what is happening", "what's happening", "status now",
        ),
        "answer": (
            "Here is the live tabletop condition from this laptop. "
            "Use Next action on the monitoring page if a baseline or slider cal is still needed."
        ),
    },
    {
        "id": "next",
        "keys": ("what should i do", "next step", "next action", "i'm stuck", "im stuck", "help me"),
        "answer": (
            "Work in this order: 1) both nodes sending JSON, 2) Baseline A and Baseline B while still, "
            "3) Node A slider two-point millimetre cal, 4) watch tilt/crack vs Node B, "
            "5) if WATCH/ALERT, open Rover Inspection and drive because a warning appeared. "
            "Ask me any follow-up."
        ),
    },
]


def _tokens(text: str) -> set[str]:
    return {tok for tok in re.findall(r"[a-z0-9]+", text.lower()) if tok not in STOP and len(tok) > 1}


def _has_phrase(question: str, key: str) -> bool:
    if " " in key or len(key) > 4:
        return key in question
    return re.search(r"\b" + re.escape(key) + r"\b", question) is not None


def _live_blurb(snapshot: Optional[dict[str, Any]]) -> str:
    if not snapshot:
        return ""
    nodes = snapshot.get("nodes") or {}
    a = nodes.get("1") or snapshot.get("1") or {}
    b = nodes.get("2") or {}
    a_status = a.get("status", "UNKNOWN") if isinstance(a, dict) else "UNKNOWN"
    b_status = b.get("status", "UNKNOWN") if isinstance(b, dict) else "UNKNOWN"
    status = snapshot.get("system_status", "UNKNOWN")
    mode = snapshot.get("mode", "")
    extra = " Simulated rehearsal, not USB hardware." if mode == "simulate" else ""
    rover = snapshot.get("rover") or {}
    rover_bit = ""
    if rover.get("ok") is False and mode == "live":
        rover_bit = " Rover link is down."
    detail = ""
    if isinstance(a, dict):
        tilt = a.get("tilt_change_deg")
        gap = a.get("relative_mm")
        bits = []
        if tilt is not None:
            try:
                bits.append(f"A tilt {float(tilt):.2f}°")
            except (TypeError, ValueError):
                pass
        if gap is not None:
            try:
                bits.append(f"crack {float(gap):.2f} mm")
            except (TypeError, ValueError):
                pass
        if bits:
            detail = " " + ", ".join(bits) + "."
    action = snapshot.get("next_action") or ""
    action_bit = f" Next: {action}" if action else ""
    return (
        f" Live now: system {status}; Node A {a_status}; Node B {b_status}."
        f"{detail}{extra}{rover_bit}{action_bit}"
    )


def _handbook_snippets(question: str, limit: int = 2) -> str:
    path = ROOT / "helper_handbook.md"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    qtokens = _tokens(question)
    if not qtokens:
        return ""
    blocks = [p.strip() for p in re.split(r"\n\s*\n", text) if len(p.strip()) > 60]
    scored: list[tuple[int, str]] = []
    for block in blocks:
        low = block.lower()
        if low.startswith("#"):
            continue
        score = len(qtokens & _tokens(block))
        if score:
            scored.append((score, re.sub(r"\s+", " ", block)[:420]))
    scored.sort(key=lambda item: item[0], reverse=True)
    return " ".join(chunk for _, chunk in scored[:limit])


def _mood(snapshot: Optional[dict[str, Any]], warn: bool) -> str:
    status = (snapshot or {}).get("system_status")
    if status == "ALERT":
        return "alert"
    if warn or status in ("WATCH", "UNKNOWN"):
        return "warn"
    return "ok"


def _hard_warning(question: str) -> Optional[str]:
    q = question.lower()
    if re.search(r"collapse|cave[- ]?in|roof will fail|subsidence %|probability of (a )?collapse", q):
        return (
            "Warning: MOLE does not predict collapse, name a cause, or output a "
            "subsidence probability. Rules latch tabletop tilt/crack thresholds. "
            "sklearn flags unusual combinations vs this rig and forecasts the next "
            "30 s of those same signals with MAE — that's it."
        )
    if re.search(r"\bppm\b|parts per million|carbon monoxide|\bco level\b", q):
        return (
            "Warning: do not read CO ppm from this MQ-7. The rover only reports raw ADC "
            "and a local HIGH/NORMAL flag. Uncalibrated gas numbers would mislead a judge."
        )
    if re.search(r"mine is safe|certified safe|workplace is safe|all clear for miners", q):
        return (
            "Warning: green/NORMAL is only 'fresh data, no tabletop trigger'. "
            "It is not a certified-safe mine and not permission to enter a working."
        )
    if re.search(r"autonomous|self[- ]?driv|auto[- ]?brake|collision avoid", q):
        return (
            "Warning: the rover is remote hold-to-move only. IR does not auto-brake. "
            "There is no autonomous navigation."
        )
    return None


def llm_enabled() -> bool:
    if os.environ.get("PYTEST_CURRENT_TEST") and os.environ.get("MOLE_HELPER_LLM_TEST") != "1":
        return False
    flag = os.environ.get("MOLE_HELPER_LLM")
    if flag is not None and flag.strip().lower() in ("0", "false", "no", "off", "faq"):
        return False
    return True


def mistral_key() -> str:
    return (os.environ.get("MISTRAL_API_KEY") or os.environ.get("MOLE_MISTRAL_KEY") or "").strip()


def mistral_model_name() -> str:
    return (os.environ.get("MISTRAL_MODEL") or "mistral-small-latest").strip() or "mistral-small-latest"


def ollama_enabled() -> bool:
    return os.environ.get("MOLE_OLLAMA", "").strip().lower() in ("1", "true", "yes", "on")


def mistral_blocked() -> bool:
    return time.time() < _quota_dead_until


def _set_llm_error(msg: Optional[str]) -> None:
    global _last_llm_error
    _last_llm_error = msg


def _mark_quota_dead(seconds: float = 45.0) -> None:
    global _quota_dead_until
    _quota_dead_until = time.time() + seconds


def compact_live(snapshot: Optional[dict[str, Any]]) -> dict[str, Any]:
    if not snapshot:
        return {}
    nodes = {}
    for key, node in (snapshot.get("nodes") or {}).items():
        nodes[key] = {
            field: node.get(field)
            for field in (
                "status", "latched_alert", "acked", "tilt_change_deg", "relative_mm",
                "vibration_g", "age_s", "reason", "baseline", "valid", "seen", "adc_raw",
            )
        }
    ai = {}
    for key, card in (snapshot.get("ai") or {}).items():
        ai[key] = {
            field: card.get(field)
            for field in ("state", "score", "top_feature", "n_train", "prior", "reason")
        }
    forecast = {}
    for key, card in (snapshot.get("forecast") or {}).items():
        tilt = (card or {}).get("tilt") or {}
        forecast[key] = {
            "label": (card or {}).get("label"),
            "mae": tilt.get("mae") or tilt.get("holdout_mae"),
            "model": tilt.get("model") or tilt.get("chosen"),
        }
    rover = snapshot.get("rover") or {}
    data = rover.get("data") if isinstance(rover, dict) else None
    joint = snapshot.get("joint") or {}
    return {
        "mode": snapshot.get("mode"),
        "simulated": snapshot.get("simulated"),
        "system_status": snapshot.get("system_status"),
        "next_action": snapshot.get("next_action"),
        "serial_connected": snapshot.get("serial_connected"),
        "serial_error": snapshot.get("serial_error"),
        "calibration": snapshot.get("calibration"),
        "nodes": nodes,
        "ai": ai,
        "joint": {
            "pattern": joint.get("pattern"),
            "state": joint.get("state"),
            "score": joint.get("score"),
            "reason": joint.get("reason"),
        },
        "forecast": forecast,
        "rover": {
            "ok": rover.get("ok") if isinstance(rover, dict) else None,
            "error": rover.get("error") if isinstance(rover, dict) else None,
            "distance_cm": None if not isinstance(data, dict) else data.get("distance_cm"),
            "ir_obstacle": None if not isinstance(data, dict) else data.get("ir_obstacle"),
            "mq7_raw": None if not isinstance(data, dict) else data.get("mq7_raw"),
            "mq7_level": None if not isinstance(data, dict) else data.get("mq7_level"),
            "driving": None if not isinstance(data, dict) else data.get("driving"),
        },
        "honesty": snapshot.get("honesty"),
    }


def _installed_models() -> list[str]:
    response = requests.get(f"{OLLAMA}/api/tags", timeout=2)
    response.raise_for_status()
    rows = response.json().get("models") or []
    names = []
    for row in rows:
        name = row.get("name") or row.get("model")
        if name:
            names.append(str(name))
    return names


def resolve_model() -> Optional[str]:
    now = time.time()
    cached = _model_cache.get("name")
    if cached and now - float(_model_cache["t"]) < 12:
        return str(cached)
    env = (os.environ.get("MOLE_OLLAMA_MODEL") or "").strip()
    names = _installed_models()
    chosen = None
    if env:
        for name in names:
            if name == env or name.startswith(env + ":"):
                chosen = name
                break
    if chosen is None:
        for pref in PREFERRED_MODELS:
            for name in names:
                if name == pref or name.startswith(pref.split(":")[0] + ":"):
                    chosen = name
                    break
            if chosen:
                break
    if chosen is None and names:
        chosen = names[0]
    _model_cache["t"] = now
    _model_cache["name"] = chosen
    return chosen


def helper_status() -> dict[str, Any]:
    error = None
    model = None
    provider = "faq"
    if not llm_enabled():
        return {
            "ok": True,
            "llm": False,
            "provider": provider,
            "model": None,
            "error": None,
            "disclaimer": DISCLAIMER,
        }
    if mistral_key():
        return {
            "ok": True,
            "llm": True,
            "provider": "mistral",
            "model": mistral_model_name(),
            "error": _last_llm_error,
            "blocked": mistral_blocked(),
            "disclaimer": DISCLAIMER,
        }
    if not ollama_enabled():
        return {
            "ok": True,
            "llm": False,
            "provider": "faq",
            "model": None,
            "error": None,
            "disclaimer": DISCLAIMER,
        }
    try:
        model = resolve_model()
        if model:
            provider = "ollama"
    except Exception as exc:
        error = str(exc)
    return {
        "ok": True,
        "llm": bool(model),
        "provider": provider,
        "model": model,
        "error": error,
        "disclaimer": DISCLAIMER,
    }


def _clean_history(raw: Any) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []
    cleaned: list[dict[str, str]] = []
    for item in raw[-12:]:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        if role not in ("user", "assistant"):
            continue
        content = str(item.get("content") or "").strip()[:800]
        if content:
            cleaned.append({"role": role, "content": content})
    return cleaned


def _llm_overclaim(text: str) -> bool:
    low = text.lower()
    if re.search(r"\b\d{1,3}\s*%", text) and re.search(r"collapse|subsidence", low):
        return True
    if re.search(r"mine is safe|certified safe|collapse is imminent", low):
        return True
    if re.search(r"\b\d+(\.\d+)?\s*ppm\b", low):
        return True
    return False


def _chat_messages(
    question: str,
    snapshot: Optional[dict[str, Any]],
    history: Optional[list[dict[str, str]]] = None,
) -> list[dict[str, str]]:
    live = json.dumps(compact_live(snapshot), ensure_ascii=False, separators=(",", ":"))
    note = _handbook_snippets(question, 1)
    extra = f"\nHANDBOOK:{note}" if note else ""
    return [
        {"role": "system", "content": FAST_SYSTEM},
        *(history or [])[-8:],
        {"role": "user", "content": f"{question}\nLIVE:{live}{extra}"},
    ]


def ask_llm(
    question: str,
    snapshot: Optional[dict[str, Any]],
    history: Optional[list[dict[str, str]]] = None,
) -> Optional[dict[str, str]]:
    acc: list[str] = []
    model = None
    for event in iter_llm(question, snapshot, history):
        if event.get("model"):
            model = event["model"]
        if event.get("delta"):
            acc.append(event["delta"])
        if event.get("error"):
            return None
    text = "".join(acc).strip()
    if not text or not model:
        return None
    return {"answer": text, "model": model}


def ask_ollama(
    question: str,
    snapshot: Optional[dict[str, Any]],
    history: Optional[list[dict[str, str]]] = None,
) -> Optional[dict[str, str]]:
    return ask_llm(question, snapshot, history)


def iter_mistral(
    question: str,
    snapshot: Optional[dict[str, Any]],
    history: Optional[list[dict[str, str]]] = None,
):
    key = mistral_key()
    if not key:
        yield {"error": "No Mistral API key."}
        return
    if mistral_blocked():
        yield {"error": _last_llm_error or "Mistral quota paused. Using FAQ."}
        return
    model = mistral_model_name()
    yield {"model": model, "provider": "mistral"}
    payload = {
        "model": model,
        "messages": _chat_messages(question, snapshot, history),
        "stream": False,
        "temperature": 0.4,
        "max_tokens": 520,
    }
    try:
        response = requests.post(
            MISTRAL_URL,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=(3, 20),
        )
        if response.status_code == 429:
            limit = str(response.headers.get("x-ratelimit-limit-req-minute") or "")
            if limit == "0":
                msg = (
                    "Mistral chat quota is 0. Activate billing at console.mistral.ai, then restart."
                )
                _set_llm_error(msg)
                _mark_quota_dead(60)
                yield {"error": msg}
                return
            _set_llm_error("Mistral is busy. Using the short FAQ.")
            yield {"error": "Mistral is busy."}
            return
        if response.status_code == 401:
            msg = "Mistral rejected the API key. Check software/.env."
            _set_llm_error(msg)
            yield {"error": msg}
            return
        if response.status_code != 200:
            msg = f"Mistral HTTP {response.status_code}"
            _set_llm_error(msg)
            yield {"error": msg}
            return
        body = response.json()
        text = str((((body.get("choices") or [{}])[0].get("message") or {}).get("content") or "")).strip()
        if not text:
            yield {"error": "Mistral returned an empty answer."}
            return
        _set_llm_error(None)
        yield {"delta": text}
    except requests.Timeout:
        msg = "Mistral timed out."
        _set_llm_error(msg)
        yield {"error": msg}
    except requests.RequestException:
        msg = "Mistral request failed."
        _set_llm_error(msg)
        yield {"error": msg}


def iter_ollama(
    question: str,
    snapshot: Optional[dict[str, Any]],
    history: Optional[list[dict[str, str]]] = None,
):
    try:
        model = resolve_model()
    except Exception:
        yield {"error": "Ollama not reachable."}
        return
    if not model:
        yield {"error": "No local Ollama model is installed."}
        return
    yield {"model": model, "provider": "ollama"}
    messages = _chat_messages(question, snapshot, history)
    try:
        with requests.post(
            f"{OLLAMA}/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": True,
                "keep_alive": "10m",
                "options": {"temperature": 0.2, "num_predict": 280, "num_ctx": 4096},
            },
            timeout=(1, 5),
            stream=True,
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line:
                    continue
                chunk = json.loads(line)
                delta = str(((chunk.get("message") or {}).get("content") or ""))
                if delta:
                    yield {"delta": delta}
                if chunk.get("done"):
                    return
    except requests.RequestException:
        yield {"error": "Ollama request failed."}


def iter_llm(
    question: str,
    snapshot: Optional[dict[str, Any]],
    history: Optional[list[dict[str, str]]] = None,
):
    if mistral_key():
        yield from iter_mistral(question, snapshot, history)
        return
    if ollama_enabled():
        yield from iter_ollama(question, snapshot, history)
        return
    yield {"error": "No LLM configured."}


def answer_from_faq(question: str, snapshot: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    raw = (question or "").strip()
    if len(raw) > 2000:
        raw = raw[:2000]
    if not raw:
        return {
            "ok": True,
            "llm": False,
            "warn": False,
            "mood": _mood(snapshot, False),
            "topic": "hello",
            "model": None,
            "answer": (
                "Hi — I'm Pip, your helper. Ask me anything about this dashboard, "
                "the hardware, the rover, the demo, or a general question."
            ) + _live_blurb(snapshot),
            "disclaimer": DISCLAIMER,
        }

    hard = _hard_warning(raw)
    if hard:
        return {
            "ok": True,
            "llm": False,
            "warn": True,
            "mood": "alert",
            "topic": "warning",
            "model": None,
            "answer": hard,
            "disclaimer": DISCLAIMER,
        }

    q = raw.lower()
    qtokens = _tokens(q)
    best: Optional[dict[str, Any]] = None
    best_score = 0
    for item in FAQ:
        score = 0
        for key in item["keys"]:
            if _has_phrase(q, key):
                score += 6 + 3 * max(1, len(key.split()))
        overlap = len(qtokens & _tokens(" ".join(item["keys"]) + " " + item["id"]))
        score += overlap
        if score > best_score:
            best = item
            best_score = score

    if best is None or best_score < 2:
        snippets = _handbook_snippets(raw)
        live = _live_blurb(snapshot)
        extra = f" Handbook note: {snippets}" if snippets else ""
        return {
            "ok": True,
            "llm": False,
            "warn": False,
            "mood": _mood(snapshot, False),
            "topic": "unknown",
            "model": None,
            "answer": (
                "I'm Pip, your helper. I will answer what I can from this tabletop handbook "
                "and the live node numbers."
                f"{live}{extra} "
                "Ask follow-ups in plain language — flashing, calibration, badges, sklearn, "
                "rover driving, the judge script, or any other question. "
                "I still will not give collapse probability, CO ppm, or a certified-safe mine."
            ),
            "disclaimer": DISCLAIMER,
        }

    warn = bool(best.get("warn"))
    answer = best["answer"]
    if best["id"] in ("hello", "rules", "ml", "green", "stale", "now", "next") or any(
        word in q for word in ("status", "now", "happening", "condition")
    ):
        answer += _live_blurb(snapshot)
    return {
        "ok": True,
        "llm": False,
        "warn": warn,
        "mood": _mood(snapshot, warn),
        "topic": best["id"],
        "model": None,
        "answer": answer,
        "disclaimer": DISCLAIMER,
    }


def _local_assist(question: str) -> Optional[str]:
    """Small offline helpers when Mistral is unavailable."""
    q = question.lower()
    math = re.search(r"(-?\d+)\s*(plus|\+|minus|-)\s*(-?\d+)", q)
    if math and not re.search(r"collapse|ppm|mine is safe", q):
        a, op, b = int(math.group(1)), math.group(2), int(math.group(3))
        if op in ("plus", "+"):
            return f"{a} plus {b} is {a + b}."
        if op in ("minus", "-"):
            return f"{a} minus {b} is {a - b}."
    if any(key in q for key in ("one-sentence", "one sentence", "intro i can say", "pitch sentence", "elevator")):
        return (
            "Say: MOLE is a SIH26025 tabletop — Node A and Node B watch tilt, vibration, and a crack slider; "
            "the laptop latches rules and runs Isolation Forest plus a 30 s sensor forecast; "
            "then we inspect with a remote rover. These readings show disturbance on this rig, not a collapse probability."
        )
    return None


def answer_question(
    question: str,
    snapshot: Optional[dict[str, Any]] = None,
    history: Optional[list[dict[str, str]]] = None,
    allow_llm: Optional[bool] = None,
) -> dict[str, Any]:
    use_llm = llm_enabled() if allow_llm is None else allow_llm
    raw = (question or "").strip()
    if len(raw) > 2000:
        raw = raw[:2000]
    faq = answer_from_faq(raw, snapshot)
    # Honesty guards stay local. Everything else may use the assistant.
    if faq["topic"] == "warning" or (faq.get("warn") and faq["topic"] != "unknown"):
        return faq
    if use_llm and not mistral_blocked():
        try:
            result = ask_llm(
                raw or "Introduce yourself as Pip, a helpful assistant for this MOLE tabletop, and wait for a question.",
                snapshot,
                _clean_history(history),
            )
        except Exception:
            result = None
        if result:
            warn = bool(_hard_warning(raw)) or _llm_overclaim(result["answer"])
            answer = result["answer"]
            if _llm_overclaim(answer):
                hard = _hard_warning(raw) or (
                    "Warning: that reading is not a collapse probability, CO ppm, or a certified-safe mine."
                )
                answer = hard + "\n\n" + answer
            return {
                "ok": True,
                "llm": True,
                "warn": warn,
                "mood": "alert" if warn else _mood(snapshot, False),
                "topic": "llm",
                "model": result["model"],
                "answer": answer,
                "disclaimer": DISCLAIMER,
            }
    local = _local_assist(raw)
    if local:
        return {
            "ok": True,
            "llm": False,
            "warn": False,
            "mood": _mood(snapshot, False),
            "topic": "assistant",
            "model": None,
            "answer": local + _live_blurb(snapshot),
            "disclaimer": DISCLAIMER,
        }
    if faq["topic"] == "unknown" and _last_llm_error:
        faq = dict(faq)
        faq["answer"] = (
            f"{faq['answer']} Cloud helper note: {_last_llm_error}"
        )
    return faq
