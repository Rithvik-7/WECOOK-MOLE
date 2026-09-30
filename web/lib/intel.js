import { channels, value, timeLabel } from "./format";

export const RISK_STATES = [
  { id: "normal", label: "Normal" },
  { id: "watch", label: "Watch" },
  { id: "warning", label: "Warning" },
  { id: "movement", label: "Movement alert" },
  { id: "critical", label: "Critical" },
];

export function reporting(node) {
  const latest = node?.latest;
  if (!latest) return false;
  if (latest.stale) return false;
  if (latest.valid === false) return false;
  return true;
}

export function latestStamp(nodes) {
  return nodes
    .map((n) => n.latest?.sample_time)
    .filter(Boolean)
    .sort()
    .at(-1);
}

export function riskState(node) {
  const a = node?.analysis;
  const movement = a?.movement_state;
  const gas = a?.gas_state;
  if (movement === "movement" && gas === "gas") return "critical";
  if (node?.condition === "movement" || movement === "movement")
    return "movement";
  if (node?.condition === "gas" || gas === "gas") return "warning";
  if (node?.condition === "watch" || movement === "watch") return "watch";
  if (node?.condition === "sensor_fault" || node?.condition === "stale")
    return "warning";
  return "normal";
}

const STEP = {
  tilt_deg: 0.08,
  vibration: 0.15,
  potentiometer_raw: 2,
  gas_raw: 8,
  temperature_c: 0.15,
  humidity_pct: 1,
  pressure_hpa: 0.4,
};

export function series(history, channel) {
  return (history || []).filter(
    (row) => row.valid !== false && Number.isFinite(Number(row[channel])),
  );
}

export function trendWord(history, channel, stale) {
  if (stale) return "Data stale";
  const rows = series(history, channel);
  if (rows.length < 2) return "Not enough samples";
  const first = Number(rows[0][channel]);
  const last = Number(rows.at(-1)[channel]);
  const delta = last - first;
  const step = Math.abs(Number(rows.at(-1)[channel]) - Number(rows.at(-2)[channel]));
  const limit = STEP[channel] ?? 0.1;
  if (step >= limit * 4) return "Sudden change";
  if (Math.abs(delta) < limit) return "Stable";
  return delta > 0 ? "Trend increasing" : "Trend falling";
}

export function arrowFor(word) {
  if (word === "Trend increasing") return "↑";
  if (word === "Trend falling") return "↓";
  if (word === "Sudden change") return "↕";
  return "→";
}

export function sensorRows(node) {
  const latest = node?.latest || {};
  const caps = new Set(node?.capabilities || []);
  const specs = [
    ["tilt_deg", "MPU tilt", caps.has("tilt_deg")],
    ["potentiometer_raw", "Slider", caps.has("potentiometer_raw")],
    ["linear_raw", "Linear sensor", caps.has("linear_raw")],
    ["gas_raw", "MQ-2 gas signal", caps.has("gas_raw")],
    ["temperature_signal_raw", "Temperature signal", caps.has("temperature_signal_raw")],
    ["temperature_c", "BME280 temperature", caps.has("temperature_c")],
  ];
  const rows = specs.map(([key, name, present]) => {
    const meta = channels[key];
    const word = present
      ? trendWord(node.history, key, latest.stale)
      : "Not on this node";
    let status = "Unavailable";
    if (!present) status = "Not fitted";
    else if (latest.stale) status = "Stale";
    else if (key === "gas_raw" && latest.gas_ready === false) status = "Warm-up";
    else if (key === "tilt_deg") {
      status =
        {
          normal: "Normal",
          watch: "Watch",
          movement: "Movement alert",
          gas: "Gas alert",
          sensor_fault: "Sensor fault",
          stale: "Stale",
        }[node.condition] || "Recorded";
    } else if (Number.isFinite(Number(latest[key]))) status = "Recorded";
    return {
      key,
      name,
      value: present ? value(latest[key], meta.precision) : "—",
      unit: present && latest[key] != null ? meta.unit : "",
      status,
      trend: word,
      arrow: present ? arrowFor(word) : "·",
      updated: present ? timeLabel(latest.sample_time) : "—",
      note:
        key === "potentiometer_raw"
          ? "Counts only. Not calibrated to millimetres."
          : key === "gas_raw"
            ? "MQ-2 raw signal. Not a gas concentration."
            : key === "linear_raw"
              ? "Counts only. The linear-sensor model is not confirmed."
              : key === "temperature_signal_raw"
                ? "ADC count. The temperature module name is not confirmed."
            : "",
    };
  });
  rows.push({
    key: "signal",
    name: "Signal",
    value: latest.rssi != null ? value(latest.rssi, 0) : "—",
    unit: latest.rssi != null ? "dBm" : "",
    status: latest.stale ? "Stale" : latest.origin || "Unreported",
    trend: latest.rssi != null ? "Reported" : "RSSI not in this packet",
    arrow: "·",
    updated: timeLabel(latest.received_time || latest.sample_time),
    note: "Link quality is shown only when the gateway sends it.",
  });
  return rows;
}

export function sliceWindow(history, minutes) {
  if (!minutes) return history || [];
  const times = (history || [])
    .map((row) => Date.parse(row.sample_time))
    .filter(Number.isFinite);
  if (!times.length) return [];
  const end = Math.max(...times);
  return history.filter((row) => Date.parse(row.sample_time) >= end - minutes * 60000);
}

export function windowStats(history, channel) {
  const rows = series(history, channel);
  if (!rows.length) return null;
  const nums = rows.map((row) => Number(row[channel]));
  return {
    current: nums.at(-1),
    min: Math.min(...nums),
    max: Math.max(...nums),
    trend: trendWord(history, channel, false),
  };
}
