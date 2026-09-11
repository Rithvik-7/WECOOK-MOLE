import { escapeHtml, getJson, postJson } from "/assets/common.js";

const MOLE_SVG = `
<svg class="mole-svg" viewBox="0 0 72 72" aria-hidden="true">
  <ellipse class="mole-shadow" cx="36" cy="66" rx="16" ry="3.2"/>
  <ellipse class="mole-ear" cx="18" cy="28" rx="8" ry="9"/>
  <ellipse class="mole-ear" cx="54" cy="28" rx="8" ry="9"/>
  <ellipse class="mole-ear-in" cx="18" cy="29" rx="4" ry="5"/>
  <ellipse class="mole-ear-in" cx="54" cy="29" rx="4" ry="5"/>
  <ellipse class="mole-body" cx="36" cy="40" rx="22" ry="20"/>
  <ellipse class="mole-belly" cx="36" cy="48" rx="13" ry="10"/>
  <path class="mole-hat" d="M16 26c2-10 38-10 40 0v4H16z"/>
  <ellipse class="mole-hat-brim" cx="36" cy="28" rx="24" ry="4"/>
  <circle class="mole-lamp" cx="36" cy="18" r="5"/>
  <circle class="mole-lamp-glow" cx="36" cy="18" r="3.2"/>
  <g class="mole-eyes">
    <ellipse cx="27" cy="38" rx="5" ry="5.4" fill="#fff"/>
    <ellipse cx="45" cy="38" rx="5" ry="5.4" fill="#fff"/>
    <circle class="mole-pupil" cx="28" cy="39" r="2.1"/>
    <circle class="mole-pupil" cx="46" cy="39" r="2.1"/>
    <circle fill="#fff" cx="27" cy="37.4" r="0.7"/>
    <circle fill="#fff" cx="45" cy="37.4" r="0.7"/>
  </g>
  <ellipse class="mole-snout" cx="36" cy="47" rx="8" ry="5.5"/>
  <ellipse class="mole-nose" cx="36" cy="45.5" rx="2.6" ry="2"/>
  <path class="mole-smile" d="M31 50.5 Q36 53.5 41 50.5"/>
  <ellipse class="mole-paw" cx="18" cy="54" rx="6" ry="4"/>
  <ellipse class="mole-paw" cx="54" cy="54" rx="6" ry="4"/>
</svg>`;

const MONITOR_CHIPS = [
  "What's happening now?",
  "What should I do next?",
  "How do I flash?",
  "Is this a collapse prediction?",
  "Help me explain this to a judge",
];
const ROVER_CHIPS = [
  "How do I drive the rover?",
  "Does IR stop the motors?",
  "Is MQ-7 in ppm?",
  "Raise wheels first?",
  "What should I check before driving?",
];

function formatHelperText(text) {
  const safe = escapeHtml(text);
  return safe.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
}

function onRoverPage() {
  return location.pathname.includes("rover");
}

function chips() {
  return onRoverPage() ? ROVER_CHIPS : MONITOR_CHIPS;
}

function warningFromState(state) {
  if (!state) return null;
  if (onRoverPage()) {
    const rover = state.rover || {};
    const data = rover.data || {};
    const ir = data.ir || {};
    if (state.simulated) {
      return { mood: "warn", text: "Simulated rover — no motor command is reaching hardware." };
    }
    if (!rover.ok) {
      return { mood: "warn", text: "Rover link is down. Join Wi-Fi Mine-Rover-AP, then try again." };
    }
    if (ir.near || data.ir_obstacle) {
      return { mood: "warn", text: "IR says near. It does not auto-brake — you still have to STOP." };
    }
    return null;
  }
  const status = state.system_status || "UNKNOWN";
  const a = state.nodes?.["1"] || {};
  const b = state.nodes?.["2"] || {};
  if (status === "ALERT") {
    const who = a.status === "ALERT" ? "Node A" : b.status === "ALERT" ? "Node B" : "a node";
    return { mood: "alert", text: `ALERT latched on ${who}. Inspect with the rover. This is not collapse proof.` };
  }
  if (status === "WATCH") {
    return { mood: "warn", text: "WATCH is on. Rules fired first. sklearn cannot clear this." };
  }
  if (state.simulated) {
    return { mood: "ok", text: "Rehearsal data. Ask me anything about MOLE — I will warn if a claim is too strong." };
  }
  if (status === "UNKNOWN") {
    return { mood: "warn", text: "Waiting for valid node packets. Don't read a quiet screen as a safe mine." };
  }
  return null;
}

function mount() {
  if (document.getElementById("moleHelper")) return;
  const root = document.createElement("aside");
  root.id = "moleHelper";
  root.className = "mole-helper mood-ok";
  root.innerHTML = `
    <div class="mole-panel" id="molePanel" hidden>
      <header class="mole-panel-head">
        <div>
          <strong>Pip</strong>
          <p id="moleHelperLabel">Helper &amp; assistant · ask anything</p>
        </div>
        <button type="button" class="mole-close" id="moleClose" aria-label="Close helper">×</button>
      </header>
      <div class="mole-messages" id="moleMessages" role="log" aria-live="polite"></div>
      <div class="mole-chips" id="moleChips"></div>
      <form class="mole-form" id="moleForm">
        <label class="sr-only" for="moleInput">Ask Pip</label>
        <input id="moleInput" name="question" maxlength="2000" autocomplete="off"
          placeholder="Ask anything — Pip will help">
        <button type="submit" class="button primary">Ask</button>
      </form>
    </div>
    <div class="mole-dock">
      <div class="mole-bubble" id="moleBubble" hidden></div>
      <button type="button" class="mole-face" id="moleFace" aria-expanded="false" aria-controls="molePanel">
        ${MOLE_SVG}
        <span>Ask anything</span>
      </button>
    </div>
  `;
  document.body.appendChild(root);

  const panel = document.getElementById("molePanel");
  const face = document.getElementById("moleFace");
  const bubble = document.getElementById("moleBubble");
  const messages = document.getElementById("moleMessages");
  const form = document.getElementById("moleForm");
  const input = document.getElementById("moleInput");
  const chipWrap = document.getElementById("moleChips");

  chipWrap.innerHTML = chips().map((label) => (
    `<button type="button" class="mole-chip">${escapeHtml(label)}</button>`
  )).join("");

  function setOpen(open) {
    panel.hidden = !open;
    face.setAttribute("aria-expanded", open ? "true" : "false");
    root.classList.toggle("open", open);
    if (open) {
      bubble.hidden = true;
      input.focus();
    }
  }

  let chatHistory = [];

  function setHelperLabel(text) {
    const label = document.getElementById("moleHelperLabel");
    if (label && text) label.textContent = text;
  }

  getJson("/api/helper/status").then((status) => {
    if (status.blocked && status.error) {
      setHelperLabel(status.error);
    } else if (status.llm && status.model) {
      const who = status.provider === "mistral" ? "Mistral" : status.provider === "ollama" ? "Local" : "Helper";
      setHelperLabel(`${who} ${status.model} · assistant · not a mine expert`);
    } else {
      setHelperLabel("Handbook + live nodes · ask anything");
    }
  }).catch(() => {});

  function addMessage(role, text, warn = false) {
    const row = document.createElement("div");
    row.className = `mole-msg ${role}${warn ? " warn" : ""}`;
    row.innerHTML = `<p>${formatHelperText(text)}</p>`;
    messages.appendChild(row);
    messages.scrollTop = messages.scrollHeight;
  }

  async function ask(question) {
    const text = String(question || "").trim();
    if (text) addMessage("user", text);
    addMessage("pip", "Pip is thinking…");
    const pending = messages.lastElementChild;
    pending.classList.add("thinking");
    const pendingText = pending.querySelector("p");
    const abort = new AbortController();
    const timer = setTimeout(() => abort.abort(), 25000);
    try {
      const response = await fetch("/api/helper", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: text, history: chatHistory }),
        signal: abort.signal,
      });
      const data = await response.json();
      const answer = String(data.answer || "").trim();
      if (!answer) throw new Error("Helper returned an empty answer.");
      pendingText.innerHTML = formatHelperText(answer);
      pending.classList.remove("thinking");
      pending.classList.toggle("warn", Boolean(data.warn));
      if (text) {
        chatHistory.push({ role: "user", content: text });
        chatHistory.push({ role: "assistant", content: answer });
        if (chatHistory.length > 16) chatHistory = chatHistory.slice(-16);
      }
      if (data.llm && data.model) {
        setHelperLabel(`Mistral ${data.model} · assistant · not a mine expert`);
      }
      const mood = data.mood || "ok";
      root.classList.remove("mood-ok", "mood-warn", "mood-alert");
      root.classList.add(`mood-${mood}`);
      if (data.warn) {
        bubble.hidden = false;
        bubble.textContent = "Warning — read that answer before acting.";
      }
      messages.scrollTop = messages.scrollHeight;
    } catch (error) {
      const msg = error.name === "AbortError"
        ? "That took too long. Ask again, or try a shorter question."
        : (error.message || "Helper is offline.");
      pendingText.textContent = msg;
      pending.classList.remove("thinking");
      pending.classList.add("warn");
    } finally {
      clearTimeout(timer);
    }
  }

  face.addEventListener("click", () => setOpen(panel.hidden));
  document.getElementById("moleClose").addEventListener("click", () => setOpen(false));
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const value = input.value.trim();
    if (!value) return;
    input.value = "";
    ask(value);
  });
  chipWrap.addEventListener("click", (event) => {
    const button = event.target.closest(".mole-chip");
    if (!button) return;
    setOpen(true);
    ask(button.textContent);
  });

  addMessage(
    "pip",
    "Hi, I'm Pip — your helper and assistant on this laptop. Ask me anything about the dashboard, nodes, rover, flashing, or the demo. I can also help with general questions. I will warn you if a mine-safety claim is too strong. Product AI is still sklearn, not me.",
  );

  let lastWarn = "";
  async function watch() {
    try {
      const url = onRoverPage() ? "/api/rover/state" : "/api/state";
      const state = await getJson(url);
      const warning = warningFromState(state);
      const mood = warning?.mood || "ok";
      root.classList.remove("mood-ok", "mood-warn", "mood-alert");
      root.classList.add(`mood-${mood}`);
      if (warning && warning.text !== lastWarn) {
        lastWarn = warning.text;
        bubble.hidden = false;
        bubble.textContent = warning.text;
        if (mood === "alert" || mood === "warn") {
          addMessage("pip", warning.text, true);
        }
      }
    } catch {
      /* helper stays quiet if the API blips */
    } finally {
      setTimeout(watch, 2500);
    }
  }
  watch();
}

mount();
