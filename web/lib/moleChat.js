import { API } from "./format";

const STORE = "mole-chat";

export function loadMoleThread() {
  try {
    const parsed = JSON.parse(sessionStorage.getItem(STORE) || "[]");
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function saveMoleThread(messages) {
  sessionStorage.setItem(STORE, JSON.stringify(messages.slice(-40)));
}

export async function moleStatus() {
  const response = await fetch(`${API}/api/assistant/status`, {
    signal: AbortSignal.timeout(4000),
  });
  if (!response.ok) return { ready: false, provider: "none", model: null };
  return response.json();
}

export async function talkToMole({
  question,
  history,
  onMeta,
  onToken,
  signal,
}) {
  const response = await fetch(`${API}/api/assistant`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, history, stream: true }),
    signal: signal || AbortSignal.timeout(90000),
  });
  if (!response.ok) {
    const result = await response.json().catch(() => ({}));
    throw new Error(
      typeof result.detail === "string"
        ? result.detail
        : "Mole could not answer just then.",
    );
  }
  if (!response.body) {
    throw new Error("Mole opened a silent reply.");
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let answer = "";
  let meta = {};
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() || "";
    for (const block of blocks) {
      let event = "message";
      const dataLines = [];
      for (const line of block.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
      }
      if (!dataLines.length) continue;
      const payload = JSON.parse(dataLines.join("\n"));
      if (event === "meta") {
        meta = payload;
        onMeta?.(payload);
      } else if (event === "token" && payload.text) {
        answer += payload.text;
        onToken?.(payload.text, answer);
      } else if (event === "error") {
        throw new Error(payload.detail || "Mole could not finish that answer.");
      } else if (event === "done") {
        return {
          answer: payload.answer || answer,
          sources: payload.sources || [],
          provider: payload.provider || meta.provider,
          model: payload.model || meta.model,
        };
      }
    }
  }
  return { answer, sources: [], ...meta };
}
