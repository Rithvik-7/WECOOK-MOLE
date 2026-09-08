export const $ = (id) => document.getElementById(id);

export function fmt(value, digits = 2, fallback = "—") {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return fallback;
  }
  return Number(value).toFixed(digits);
}

export function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

export function badge(status, label = status) {
  const safeStatus = [
    "NORMAL", "WATCH", "ALERT", "UNKNOWN", "READY", "UNUSUAL",
    "INACTIVE", "LEARNING", "GOOD", "FAIR", "LOW", "INSUFFICIENT_DATA",
    "COMMON", "LOCAL_A", "LOCAL_B", "QUIET",
  ].includes(status) ? status : "UNKNOWN";
  return `<span class="badge ${safeStatus}">${escapeHtml(label)}</span>`;
}

let toastTimer = null;
export function toast(message, error = false) {
  const node = $("toast");
  if (!node) return;
  node.textContent = message;
  node.className = `toast show${error ? " error" : ""}`;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    node.className = "toast";
  }, 3400);
}

export async function getJson(url) {
  const response = await fetch(url, { cache: "no-store" });
  const text = await response.text();
  let body = {};
  try {
    body = text ? JSON.parse(text) : {};
  } catch {
    throw new Error(`HTTP ${response.status}`);
  }
  if (!response.ok) throw new Error(body.detail || body.error || `HTTP ${response.status}`);
  return body;
}

export async function postJson(url, body = {}) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const text = await response.text();
  let result = {};
  try {
    result = text ? JSON.parse(text) : {};
  } catch {
    throw new Error(`HTTP ${response.status}`);
  }
  if (!response.ok || result.ok === false) {
    throw new Error(result.detail || result.error || `HTTP ${response.status}`);
  }
  return result;
}

export function setModeBanner(simulated) {
  const banner = $("modeBanner");
  if (banner) banner.classList.toggle("show", Boolean(simulated));
}

export function timeAgo(seconds) {
  if (seconds === null || seconds === undefined) return "never";
  if (seconds < 1) return "now";
  if (seconds < 60) return `${Math.round(seconds)} s ago`;
  return `${Math.round(seconds / 60)} min ago`;
}
