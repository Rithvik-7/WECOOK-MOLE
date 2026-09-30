export const labels = {
  normal: "Normal",
  watch: "Watch",
  movement: "Movement alert",
  gas: "Gas alert",
  sensor_fault: "Sensor fault",
  stale: "Stale",
  unavailable: "Unavailable",
  unknown: "Unknown",
};
export const channels = {
  ir: { label: "IR detection", unit: "state", precision: 0 },
  linear_raw: { label: "Linear sensor", unit: "counts", precision: 0 },
  temperature_signal_raw: {
    label: "Temperature signal",
    unit: "counts",
    precision: 0,
  },
  tilt_deg: { label: "Tilt", unit: "°", precision: 2 },
  vibration: { label: "Vibration", unit: "rel.", precision: 2 },
  potentiometer_raw: {
    label: "Slider",
    unit: "counts",
    precision: 0,
  },
  gas_raw: { label: "MQ-2 gas signal", unit: "raw", precision: 0 },
  temperature_c: { label: "Temperature", unit: "°C", precision: 1 },
  humidity_pct: { label: "Humidity", unit: "% RH", precision: 0 },
  pressure_hpa: { label: "Pressure", unit: "hPa", precision: 0 },
};
export const value = (n, precision = 1) =>
  n === null || n === undefined || !Number.isFinite(Number(n))
    ? "—"
    : Number(n).toFixed(precision);
export function timeLabel(t) {
  return t
    ? new Date(t).toLocaleTimeString("en-IN", {
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      })
    : "—";
}
export function dateLabel(t) {
  return t
    ? new Date(t).toLocaleString("en-IN", {
        day: "2-digit",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
      })
    : "Not recorded";
}
export function delta(node, key = "tilt_deg") {
  const a = (node?.history || []).filter(
    (r) => r.valid !== false && Number.isFinite(r[key]),
  );
  return a.length > 1 ? a.at(-1)[key] - a[0][key] : null;
}
export const API = process.env.NEXT_PUBLIC_MOLE_API || "";
export async function request(path, body) {
  const token =
    typeof window !== "undefined"
      ? sessionStorage.getItem("mole-capability")
      : null;
  const response = await fetch(`${API}${path}`, {
    method: body === undefined ? "GET" : "POST",
    cache: "no-store",
    signal: AbortSignal.timeout(12000),
    headers: {
      "Content-Type": "application/json",
      ...(token ? { "X-Mole-Capability": token } : {}),
    },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  const result = await response.json().catch(() => ({}));
  if (!response.ok)
    throw new Error(
      typeof result.detail === "string"
        ? result.detail
        : "The request could not be completed. Please try again.",
    );
  return result;
}
