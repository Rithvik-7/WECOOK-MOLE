"""Mole companion: a real LLM grounded in this mine's records and build facts."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Iterable

OLLAMA_HOST = os.environ.get("MOLE_OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
MISTRAL_BASE = "https://api.mistral.ai/v1"
GROQ_BASE = "https://api.groq.com/openai/v1"
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/openai"
OPENROUTER_BASE = "https://openrouter.ai/api/v1"
MISTRAL_MODEL = "mistral-small-latest"
GROQ_MODEL = "qwen/qwen3.8-27b"
GEMINI_MODEL = "gemini-2.0-flash"
OPENROUTER_MODEL = "meta-llama/llama-3.2-3b-instruct:free"

_PROVIDER_MODELS = {
    "mistral": MISTRAL_MODEL,
    "groq": GROQ_MODEL,
    "gemini": GEMINI_MODEL,
    "openrouter": OPENROUTER_MODEL,
    "openai-compatible": "gpt-4o-mini",
}
_MODEL_HINTS = {
    "mistral": ("mistral", "ministral", "codestral", "pixtral"),
    "groq": ("llama", "gemma", "mixtral", "qwen", "gpt-oss"),
    "gemini": ("gemini",),
    "openrouter": ("/",),
}


def _load_dotenv() -> None:
    root = Path(__file__).resolve().parents[1]
    for name in (".env", ".env.local"):
        path = root / name
        if not path.exists():
            continue
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if not key or not value:
                continue
            if not os.environ.get(key, "").strip():
                os.environ[key] = value


def _secret(*names: str) -> str:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return ""

PROJECT_BRIEF = """
You are Mole, the companion for MOLE — Mine Observation & Land Evaluation.
You live as a small chat on the operator console. Speak as Mole: warm, precise,
short when the facts are short, and never theatrical. You are not a certified
mine engineer and you do not issue safety clearances.

What this project is
- A local Next.js + FastAPI console for four surface stations around an
  underground demonstration panel named East Panel Demonstration.
- The geometry on the Monitor cutaway is illustrative, not a surveyed map.
- Demo ticks and simulated origin samples are honest: they are not a live
  instrument feed unless a row says otherwise.
- Persistence is SQLite. There is no cloud mesh.

Stations (software ids A–D)
- A Entrance / Node 1: ESP32-S3, MPU-6050, slider. tilt, vibration,
  potentiometer_raw. Slider counts are ADC counts, not millimetres.
- B Surface / Node 2: classic ESP32, MPU-6050, DS18B20. temperature_c is air
  temperature in degrees Celsius. Rain, soil moisture and groundwater are not
  installed.
- C Shaft / Node 3: classic ESP32, MPU-6050, 10 kΩ slider, MQ-2.
  gas_raw is a warmed raw MQ-2 response, not a concentration. The slider is
  ADC counts, not millimetres. Node C is not the rover.
- D Vent / Node 4: classic ESP32, LCD, buzzer, and a Bosch chip at 0x76.
  The chip ID is BMP280, so temperature_c and pressure_hpa are air readings.
  Humidity is not measured. No MPU is on this board's I2C bus, so tilt is
  unavailable. The LCD must not say the mine is safe.

Radio and receiver
- Star collection to an ESP32-S3 receiver. Mesh is not implemented.
- Missing readings are unavailable, not zero. An offline node is not normal.

Prototype laboratory rules (not certified working limits)
- Tilt watch: |delta| ≥ 0.6° from the window reference.
- Tilt movement: 1.2° change sustained for 3 consecutive valid samples, with
  at least 6 valid tilts in the window.
- Vibration watch: recent vibration ≥ 2.5 without sustained tilt.
- Gas watch uses a raw-count prototype around 1800. It is not a ppm alarm.
- Window reference is the median of the first three valid tilts. It is not a
  surveyed commissioning baseline.
- Analysis engine: prototype-window-v2. No trained ML artifact is loaded.
  Forecasts on charts are experimental synthetic-ridge sessions, not safety
  predictions.

Console pages
- Monitor: mine cutaway and station focus.
- Nodes: per-station channel dossiers, limits, graphs, downloads.
- Analysis: overlay of two stations on one clock, ranking, tilt bands.
- Incidents: acknowledge / review / close. Acknowledging does not clear the
  physical condition.
- Rover R1: inspection unit, distinct from Node C. Camera not equipped, drive
  not enabled, localization unavailable. /api/commands refuses physical motion.
  Planning a mission records a note against an incident; it does not move R1.
- Operator pairing uses MOLE_OPERATOR_TOKEN in the browser session.

Hardware honesty from the build manifest
- Driving is not claimed. Live rover video is not claimed.
- MQ-2/MQ-5 gas concentration is not claimed.
- Millimetres from sliders are not claimed.
- You cannot change thresholds, close incidents, arm SOS, or drive the rover
  from this chat. Tell the operator which page does that.

How to answer
- Prefer the LIVE SITE BRIEF attached to this turn. Quote recorded numbers.
- If a reading is missing, say unavailable. Do not invent it.
- You may answer general questions (what tilt means, how a star radio works,
  how this console is put together) but flag when you leave the recorded brief.
- If you are unsure, say so. Never pretend a certification, a live camera, or
  a trained collapse model.
""".strip()


class LLMUnavailable(Exception):
    pass


def _opener():
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _ollama_tags() -> list[str]:
    try:
        req = urllib.request.Request(f"{OLLAMA_HOST}/api/tags")
        with _opener().open(req, timeout=0.8) as response:
            body = json.loads(response.read().decode())
        return [item.get("name") for item in body.get("models") or [] if item.get("name")]
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return []


def _default_ollama_model(names: list[str] | None = None) -> str:
    configured = os.environ.get("MOLE_LLM_MODEL", "").strip()
    names = names if names is not None else _ollama_tags()
    if configured:
        return configured
    for preferred in ("mistral:latest", "mistral", "llama3.1:8b", "llama3.1"):
        if preferred in names:
            return preferred
    return names[0] if names else "mistral:latest"


def _provider_from_base(base: str) -> str:
    lowered = base.lower()
    if "mistral.ai" in lowered:
        return "mistral"
    if "groq.com" in lowered:
        return "groq"
    if "googleapis.com" in lowered:
        return "gemini"
    if "openrouter.ai" in lowered:
        return "openrouter"
    return "openai-compatible"


def _model_for(provider: str) -> str:
    configured = os.environ.get("MOLE_LLM_MODEL", "").strip()
    fallback = _PROVIDER_MODELS.get(provider, GROQ_MODEL)
    if not configured:
        return fallback
    hints = _MODEL_HINTS.get(provider)
    if hints and not any(hint in configured.lower() for hint in hints):
        return fallback
    return configured


def _cloud(provider: str, key: str, base: str) -> dict:
    return {
        "ok": True,
        "provider": provider,
        "model": _model_for(provider),
        "base": base,
        "key": key,
    }


def llm_status() -> dict:
    _load_dotenv()
    explicit_key = _secret("MOLE_LLM_API_KEY")
    explicit_base = os.environ.get("MOLE_LLM_BASE_URL", "").strip()
    if explicit_key:
        base = explicit_base or GROQ_BASE
        return _cloud(_provider_from_base(base), explicit_key, base)
    groq_key = _secret("GROQ_API_KEY")
    if groq_key:
        return _cloud("groq", groq_key, explicit_base or GROQ_BASE)
    gemini_key = _secret("GEMINI_API_KEY", "GOOGLE_API_KEY")
    if gemini_key:
        return _cloud("gemini", gemini_key, explicit_base or GEMINI_BASE)
    openrouter_key = _secret("OPENROUTER_API_KEY")
    if openrouter_key:
        return _cloud("openrouter", openrouter_key, explicit_base or OPENROUTER_BASE)
    mistral_key = _secret("MISTRAL_API_KEY")
    if mistral_key:
        return _cloud("mistral", mistral_key, explicit_base or MISTRAL_BASE)
    backend = os.environ.get("MOLE_LLM_BACKEND", "").strip().lower()
    if backend == "ollama":
        names = _ollama_tags()
        if names:
            return {
                "ok": True,
                "provider": "ollama",
                "model": _default_ollama_model(names),
                "base": OLLAMA_HOST,
                "key": "",
            }
    return {"ok": False, "provider": "none", "model": None, "base": None, "key": ""}


def live_brief(snapshot: dict) -> str:
    site = snapshot.get("site") or {}
    weather = snapshot.get("weather") or {}
    lines = [
        f"Site: {site.get('name') or 'unlabelled'} · schematic={site.get('schematic')}",
        f"Model state: {snapshot.get('model_state')}",
        f"Weather: {weather.get('freshness') or 'unavailable'} (rain is not connected).",
    ]
    for node in snapshot.get("nodes") or []:
        latest = node.get("latest") or {}
        analysis = node.get("analysis") or {}
        features = analysis.get("features") or {}
        channels = ", ".join(node.get("capabilities") or [])
        tilt = latest.get("tilt_deg")
        tilt_text = f"{tilt:.2f}°" if isinstance(tilt, (int, float)) else "unavailable"
        lines.append(
            "Node {id} {place}: condition={condition}; tilt={tilt}; "
            "delta={delta}; origin={origin}; channels={channels}.".format(
                id=node.get("id"),
                place=node.get("place") or node.get("name"),
                condition=analysis.get("condition") or node.get("condition"),
                tilt=tilt_text,
                delta=features.get("delta_deg"),
                origin=latest.get("origin") or "unknown",
                channels=channels or "none listed",
            )
        )
        for item in (analysis.get("evidence") or [])[:2]:
            lines.append(f"  evidence: {item}")
    incidents = snapshot.get("incidents") or []
    open_ones = [item for item in incidents if item.get("status") != "CLOSED"]
    lines.append(f"Incidents: {len(incidents)} stored, {len(open_ones)} open.")
    for item in open_ones[:6]:
        lines.append(
            f"  {item.get('id')} node={item.get('node_id')} status={item.get('status')} "
            f"title={item.get('title')} :: {item.get('explanation') or item.get('summary') or ''}"
        )
    missions = snapshot.get("missions") or []
    lines.append(f"Rover R1 missions: {len(missions)}. Camera not equipped. Drive not enabled.")
    for item in missions[:4]:
        lines.append(
            f"  {item.get('id')} state={item.get('state')} incident={item.get('incident_id')} "
            f"note={item.get('note')}"
        )
    sos = snapshot.get("sos") or []
    if sos:
        latest = sos[0]
        lines.append(f"SOS latest: {latest.get('id')} status={latest.get('status')}")
    else:
        lines.append("SOS: none stored.")
    return "\n".join(lines)


def related_sources(question: str, snapshot: dict) -> list[str]:
    q = question.lower()
    found = []
    for item in snapshot.get("incidents") or []:
        ident = str(item.get("id") or "")
        node = str(item.get("node_id") or "")
        title = str(item.get("title") or "").lower()
        if ident.lower() in q or f"node {node.lower()}" in q or (title and title in q):
            found.append(ident)
    return found[:6]


def build_messages(question: str, history: list[dict], snapshot: dict) -> list[dict]:
    turns = []
    for item in history[-12:]:
        role = item.get("role")
        content = str(item.get("content") or "").strip()
        if role in {"user", "assistant"} and content:
            turns.append({"role": role, "content": content[:4000]})
    return [
        {"role": "system", "content": PROJECT_BRIEF},
        {
            "role": "system",
            "content": "LIVE SITE BRIEF\n" + live_brief(snapshot),
        },
        *turns,
        {"role": "user", "content": question.strip()},
    ]


def iter_llm_tokens(messages: list[dict]) -> Iterable[str]:
    status = llm_status()
    if not status["ok"]:
        raise LLMUnavailable(
            "Mole uses Groq's free API. Add GROQ_API_KEY from "
            "https://console.groq.com/keys to the project .env file, then restart the API."
        )
    if status["provider"] == "ollama":
        yield from _iter_ollama(messages, status["model"])
        return
    yield from _iter_openai(messages, status)


def _iter_ollama(messages: list[dict], model: str) -> Iterable[str]:
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "keep_alive": "60m",
        "options": {"temperature": 0.4, "num_ctx": 4096},
    }
    req = urllib.request.Request(
        f"{OLLAMA_HOST}/api/chat",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with _opener().open(req, timeout=90) as response:
            for raw in response:
                line = raw.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if chunk.get("error"):
                    raise LLMUnavailable(str(chunk["error"]))
                text = (chunk.get("message") or {}).get("content") or ""
                if text:
                    yield text
                if chunk.get("done"):
                    break
    except LLMUnavailable:
        raise
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise LLMUnavailable(f"Mole could not reach Ollama. {exc}") from exc


def _iter_openai(messages: list[dict], status: dict) -> Iterable[str]:
    url = status["base"].rstrip("/") + "/chat/completions"
    payload = {
        "model": status["model"],
        "messages": messages,
        "stream": True,
        "temperature": 0.4,
        "max_tokens": 800,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {status.get('key') or ''}",
        "User-Agent": "MOLE/1.0",
    }
    if status.get("provider") == "openrouter":
        headers["HTTP-Referer"] = os.environ.get("MOLE_PUBLIC_URL", "http://127.0.0.1:3000")
        headers["X-Title"] = "MOLE"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers=headers,
        method="POST",
    )
    try:
        with _opener().open(req, timeout=90) as response:
            for raw in response:
                line = raw.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue
                choices = chunk.get("choices") or [{}]
                delta = choices[0].get("delta") or {}
                text = delta.get("content") or ""
                if not text and delta.get("reasoning"):
                    continue
                if text:
                    yield text
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        raise LLMUnavailable(
            f"Mole could not reach {status.get('provider') or 'the language model'} ({exc.code}). {detail}"
        ) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise LLMUnavailable(f"Mole could not reach the language model. {exc}") from exc
