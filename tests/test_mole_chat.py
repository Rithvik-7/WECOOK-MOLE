import os
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MOLE_DB", str(ROOT / "data" / "mole.db"))
os.environ.setdefault("MOLE_OPERATOR_TOKEN", "test-token")

import sys

sys.path.insert(0, str(ROOT / "api"))
from fastapi.testclient import TestClient
from main import app
from mole_chat import live_brief, llm_status

client = TestClient(app)


def test_live_brief_mentions_nodes():
  snapshot = client.get("/api/state").json()
  brief = live_brief(snapshot)
  assert "Node A" in brief
  assert "Rover R1" in brief


def test_assistant_uses_language_model_not_keyword_script():
  tokens = ["Node B is on a recorded movement watch. "]

  def fake_tokens(_messages):
    yield from tokens

  with patch("main.iter_llm_tokens", fake_tokens), patch(
    "main.llm_status",
    return_value={
      "ok": True,
      "provider": "ollama",
      "model": "mistral:latest",
      "base": "http://127.0.0.1:11434",
    },
  ):
    response = client.post(
      "/api/assistant",
      json={"question": "What is happening at the surface panel?"},
    )
  assert response.status_code == 200
  body = response.json()
  assert "movement watch" in body["answer"]
  assert body["provider"] == "ollama"
  assert body["companion"] == "Mole"
  assert "No open incidents are recorded." not in body["answer"]


def test_llm_status_prefers_groq(monkeypatch):
  monkeypatch.setenv("MISTRAL_API_KEY", "mistral_test")
  monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
  monkeypatch.setenv("MOLE_LLM_MODEL", "mistral-small-latest")
  monkeypatch.delenv("MOLE_LLM_API_KEY", raising=False)
  monkeypatch.delenv("MOLE_LLM_BASE_URL", raising=False)
  monkeypatch.delenv("GEMINI_API_KEY", raising=False)
  monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
  monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
  status = llm_status()
  assert status["ok"] is True
  assert status["provider"] == "groq"
  assert status["model"] == "qwen/qwen3.8-27b"
  assert status["base"] == "https://api.groq.com/openai/v1"
  assert status["key"] == "gsk_test"


def test_llm_status_uses_groq_without_mistral(monkeypatch):
  monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
  monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
  monkeypatch.delenv("MOLE_LLM_API_KEY", raising=False)
  monkeypatch.delenv("MOLE_LLM_BASE_URL", raising=False)
  monkeypatch.delenv("MOLE_LLM_MODEL", raising=False)
  monkeypatch.delenv("GEMINI_API_KEY", raising=False)
  monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
  monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
  status = llm_status()
  assert status["ok"] is True
  assert status["provider"] == "groq"
  assert status["model"] == "qwen/qwen3.8-27b"
  assert status["base"] == "https://api.groq.com/openai/v1"
  assert status["key"] == "gsk_test"


def test_llm_status_without_cloud_key_is_unavailable(monkeypatch):
  monkeypatch.setattr("mole_chat._load_dotenv", lambda: None)
  for name in (
    "MISTRAL_API_KEY",
    "GROQ_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "OPENROUTER_API_KEY",
    "MOLE_LLM_API_KEY",
    "MOLE_LLM_BACKEND",
  ):
    monkeypatch.delenv(name, raising=False)
  status = llm_status()
  assert status["ok"] is False
  assert status["provider"] == "none"


def test_assistant_stream_tokens():
  def fake_tokens(_messages):
    yield "Hello "
    yield "from Mole."

  with patch("main.iter_llm_tokens", fake_tokens), patch(
    "main.llm_status",
    return_value={
      "ok": True,
      "provider": "ollama",
      "model": "mistral:latest",
      "base": "http://127.0.0.1:11434",
    },
  ):
    response = client.post(
      "/api/assistant",
      json={"question": "Who are you?", "stream": True},
    )
  assert response.status_code == 200
  text = response.text
  assert "event: token" in text
  assert "Hello " in text
  assert "from Mole." in text
