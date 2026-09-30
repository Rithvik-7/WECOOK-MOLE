"use client";
import { useEffect, useState } from "react";
import { Badge, Empty } from "./Primitives";
import { SignalChart, SENSOR_INFO } from "./SignalChart";
import { Icon } from "./icons";
import { API, channels, dateLabel, delta, timeLabel, value } from "../lib/format";
import { NAMES, PLACEMENTS } from "./MineOverview";

const HARDWARE = {
  A: {
    pack: "ESP32-S3 · MPU-6050 · slider",
    radio: "Star leaf → ESP32-S3 receiver",
    note: "Slider counts are not millimetres until the slider is fixed and calibrated.",
  },
  B: {
    pack: "ESP32 · MPU-6050 · DS18B20",
    radio: "Star leaf → ESP32-S3 receiver",
    note: "DS18B20 reports air temperature in °C. It is not soil moisture or groundwater.",
  },
  C: {
    pack: "ESP32 · MPU-6050 · 10 kΩ slider · MQ-2",
    radio: "Star leaf → ESP32-S3 receiver",
    note: "Slider counts are not millimetres. MQ-2 is a raw count after warm-up, not a gas concentration.",
  },
  D: {
    pack: "ESP32 · MPU-6050 · BME280 · LCD · buzzer",
    radio: "Star leaf → ESP32-S3 receiver",
    note: "This board's climate chip identifies as a BMP280: temperature and pressure only. Humidity is not measured. There is no MPU on its I2C bus, so tilt is unavailable.",
  },
};

const WATCH = {
  tilt_deg: { mode: "change", watch: 0.6, alert: 1.2, unit: "°" },
  vibration: { mode: "level", watch: 2.5, unit: "rel." },
  gas_raw: { mode: "level", watch: 1800, unit: "raw" },
};

function csvCell(v) {
  const s = String(v ?? "");
  return /[",\n]/.test(s) ? `"${s.replaceAll('"', '""')}"` : s;
}

function downloadFile(filename, mime, text) {
  const blob = new Blob([text], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function nodeCsv(node) {
  const keys = node.capabilities;
  const head = [
    "node_id",
    "sample_time",
    "origin",
    "session_id",
    "sequence",
    "valid",
    ...keys,
  ];
  const lines = [head.join(",")];
  for (const row of node.history || []) {
    lines.push(
      [
        node.id,
        row.sample_time,
        row.origin,
        row.session_id,
        row.sequence,
        row.valid === false ? "false" : "true",
        ...keys.map((k) => (Number.isFinite(row[k]) ? row[k] : "")),
      ]
        .map(csvCell)
        .join(","),
    );
  }
  return `${lines.join("\n")}\n`;
}

function nodeJson(node) {
  return JSON.stringify(
    {
      exported_at: new Date().toISOString(),
      disclaimer:
        "Laboratory watch values from prototype rules. Not certified safe limits.",
      station: {
        id: node.id,
        name: NAMES[node.id] || node.name,
        place: PLACEMENTS[node.id] || node.place,
        condition: node.condition,
        capabilities: node.capabilities,
        hardware: HARDWARE[node.id],
      },
      channels: Object.fromEntries(
        node.capabilities.map((key) => [
          key,
          {
            ...(channels[key] || { label: "IR detection", unit: "state" }),
            ...(SENSOR_INFO[key] || {}),
            watch: WATCH[key] || null,
          },
        ]),
      ),
      latest: node.latest,
      analysis: node.analysis,
      history: node.history,
    },
    null,
    2,
  );
}

function measuredValue(node, key) {
  const spec = WATCH[key];
  const latest = node.latest?.valid !== false ? node.latest?.[key] : null;
  if (!spec) return latest;
  if (spec.mode === "change") {
    const d = node.analysis?.features?.delta_deg;
    return Number.isFinite(d) ? Math.abs(d) : Math.abs(delta(node, key) ?? 0);
  }
  return latest;
}

function watchTone(node, key) {
  const spec = WATCH[key];
  const measured = measuredValue(node, key);
  if (!spec || !Number.isFinite(measured)) return "none";
  if (spec.alert != null && measured >= spec.alert) return "alert";
  if (measured >= spec.watch) return "watch";
  return "ok";
}

function LimitMeter({ node, channel }) {
  const spec = WATCH[channel];
  const info = SENSOR_INFO[channel];
  const measured = measuredValue(node, channel);
  const tone = watchTone(node, channel);
  const ratio = spec && Number.isFinite(measured) ? measured / spec.watch : 0;
  return (
    <div className={`limit-meter is-${tone}`}>
      <div className="limit-meter-copy">
        <strong>{channels[channel]?.label || "IR detection"}</strong>
        <span>{info?.limit}</span>
      </div>
      {spec ? (
        <div
          className="limit-track"
          role="meter"
          aria-label={`${channels[channel]?.label} against laboratory watch`}
          aria-valuemin={0}
          aria-valuemax={spec.alert || spec.watch}
          aria-valuenow={Number.isFinite(measured) ? measured : 0}
        >
          <i style={{ width: `${Math.min(100, Math.max(0, ratio * 100))}%` }} />
          <em>
            {spec.mode === "change" ? "Δ " : ""}
            {value(measured, channels[channel]?.precision ?? 1)}
            {spec.unit} / watch {spec.watch}
            {spec.unit}
            {spec.alert ? ` · alert ${spec.alert}${spec.unit}` : ""}
          </em>
        </div>
      ) : (
        <p className="limit-none">No numeric site limit configured.</p>
      )}
      <small>{info?.note}</small>
    </div>
  );
}

function StationFile({ node, model, onInspect }) {
  const a = node.analysis || {};
  const q = a.quality || {};
  const f = a.features || {};
  const latest = node.latest || {};
  const place = PLACEMENTS[node.id] || node.place;
  const gear = HARDWARE[node.id];
  const alert = ["movement", "gas"].includes(node.condition);
  const validCount = (node.history || []).filter((r) => r.valid !== false).length;
  return (
    <article
      id={`station-${node.id}`}
      className={`station-file ${alert ? "is-alert" : ""}`}
    >
      <header className="station-file-head">
        <div className="station-id" aria-hidden="true">
          {node.id}
        </div>
        <div className="station-identity">
          <p className="station-kicker">{place}</p>
          <h2>{NAMES[node.id] || node.name}</h2>
          <p className="station-pack">{gear?.pack}</p>
        </div>
        <div className="station-head-meta">
          {node.condition !== "normal" ? (
            <Badge condition={node.condition} />
          ) : (
            <span className="station-state">Steady</span>
          )}
          <p>
            {latest.origin || "unknown"} · {dateLabel(latest.sample_time)}
          </p>
        </div>
      </header>

      <dl className="station-facts">
        <div>
          <dt>Origin</dt>
          <dd>{latest.origin || "—"}</dd>
        </div>
        <div>
          <dt>Session</dt>
          <dd>{latest.session_id || "—"}</dd>
        </div>
        <div>
          <dt>Sequence</dt>
          <dd>{latest.sequence ?? "—"}</dd>
        </div>
        <div>
          <dt>Last sample</dt>
          <dd>{timeLabel(latest.sample_time)}</dd>
        </div>
        <div>
          <dt>Valid / window</dt>
          <dd>
            {q.valid_count ?? validCount} / {q.total_count ?? (node.history || []).length}
          </dd>
        </div>
        <div>
          <dt>Coverage</dt>
          <dd>{q.coverage_pct != null ? `${q.coverage_pct}%` : "—"}</dd>
        </div>
        <div>
          <dt>Radio</dt>
          <dd>{gear?.radio}</dd>
        </div>
        <div>
          <dt>Freshness</dt>
          <dd>{q.freshness || (latest.stale ? "stale" : "recorded")}</dd>
        </div>
        <div>
          <dt>Tilt Δ vs reference</dt>
          <dd>
            {value(f.delta_deg, 2)}
            <small>°</small>
          </dd>
        </div>
        <div>
          <dt>Reference tilt</dt>
          <dd>
            {value(f.baseline_deg, 2)}
            <small>°</small>
          </dd>
        </div>
        <div>
          <dt>Trend</dt>
          <dd>
            {value(f.slope_deg_min, 3)}
            <small>°/min</small>
          </dd>
        </div>
        <div>
          <dt>Sustained</dt>
          <dd>
            {f.sustained_samples ?? 0}
            <small> samples</small>
          </dd>
        </div>
        <div>
          <dt>Movement rule</dt>
          <dd>{a.movement_state || node.condition}</dd>
        </div>
        <div>
          <dt>Gas rule</dt>
          <dd>
            {node.capabilities.includes("gas_raw")
              ? `${a.gas_state || "—"}${latest.gas_ready === false ? " · warm-up" : ""}`
              : "Not installed"}
          </dd>
        </div>
        <div>
          <dt>Rule set</dt>
          <dd>{a.rule_version || "prototype-window-v2"}</dd>
        </div>
        <div>
          <dt>Sample valid</dt>
          <dd>{latest.valid === false ? "Invalid" : "Valid"}</dd>
        </div>
      </dl>

      <p className="station-note">{gear?.note}</p>

      <div className="station-downloads">
        <p>Download this station</p>
        <button
          type="button"
          className="button light"
          onClick={() =>
            downloadFile(
              `mole-node-${node.id}.csv`,
              "text/csv;charset=utf-8",
              nodeCsv(node),
            )
          }
        >
          <Icon name="download" size={16} />
          CSV · {NAMES[node.id]}
        </button>
        <button
          type="button"
          className="button light"
          onClick={() =>
            downloadFile(
              `mole-node-${node.id}.json`,
              "application/json;charset=utf-8",
              nodeJson(node),
            )
          }
        >
          <Icon name="download" size={16} />
          JSON · record
        </button>
        <a className="button light" href={`${API}/api/exports/telemetry.csv`}>
          <Icon name="download" size={16} />
          Network CSV
        </a>
        <a className="button light" href={`${API}/api/exports/telemetry.xlsx`}>
          <Icon name="download" size={16} />
          Network Excel
        </a>
        <button type="button" className="button light" onClick={() => onInspect(node.id)}>
          Raw field record
          <Icon name="arrow" size={16} />
        </button>
      </div>

      <h3 className="station-section">Installed channels</h3>
      <dl className="node-readings station-readings">
        {node.capabilities.map((key) => {
          const c = channels[key] || {
            label: "IR detection",
            precision: 0,
            unit: "state",
          };
          return (
            <div key={key} className={`is-${watchTone(node, key)}`}>
              <dt>
                {c.label}
                <small>{SENSOR_INFO[key]?.sensor || "Unconfirmed module"}</small>
              </dt>
              <dd>
                {value(latest[key], c.precision)}
                <small>{c.unit}</small>
              </dd>
            </div>
          );
        })}
      </dl>

      <h3 className="station-section">Laboratory watch limits</h3>
      <p className="station-limit-lead">
        These are the prototype rules used in this console. They are not a
        certified safe working limit for the mine.
      </p>
      <div className="limit-grid">
        {node.capabilities.map((key) => (
          <LimitMeter key={key} node={node} channel={key} />
        ))}
      </div>

      <div className="station-evidence">
        <h3 className="station-section">Why this state</h3>
        <p>{a.summary || "No simulated warning at this node."}</p>
        <ul>
          {(a.evidence || ["Awaiting a complete observation window."]).map(
            (item, i) => (
              <li key={i}>{item}</li>
            ),
          )}
        </ul>
        <p className="station-model">{a.model_state}</p>
      </div>

      <h3 className="station-section">Graphs</h3>
      <div className="station-charts">
        {node.capabilities.map((channel) => (
          <SignalChart
            key={channel}
            node={node}
            channel={channel}
            model={model}
          />
        ))}
      </div>
    </article>
  );
}

export function Nodes({ data, onInspect }) {
  const [query, setQuery] = useState("");
  const [model, setModel] = useState(null);
  useEffect(() => {
    fetch("/models/short-horizon.json")
      .then((r) => (r.ok ? r.json() : null))
      .then(setModel)
      .catch(() => {});
  }, []);
  const found = data.nodes.filter((n) =>
    `${NAMES[n.id] || n.name} ${PLACEMENTS[n.id] || n.place} ${n.condition} ${n.capabilities.join(" ")} ${n.capabilities.map((k) => channels[k]?.label || "IR").join(" ")}`
      .toLowerCase()
      .includes(query.toLowerCase()),
  );
  const open = data.nodes.filter((n) =>
    ["movement", "gas", "watch"].includes(n.condition),
  ).length;
  return (
    <div className="nodes-console">
      <div className="network-strip">
        <div>
          <span>4 fixed stations</span>
          <span>ESP32-S3 receiver</span>
          <span>Local gateway</span>
          <span>Star radio · mesh not implemented</span>
        </div>
        <p>
          {open
            ? `${open} station${open === 1 ? "" : "s"} above a laboratory watch or alert.`
            : "No station is above a laboratory watch."}{" "}
          Installed channels only. Missing sensors are omitted, not estimated.
        </p>
      </div>

      <div className="station-toolbar">
        <nav className="station-jump" aria-label="Jump to station">
          {data.nodes.map((n) => (
            <a
              key={n.id}
              href={`#station-${n.id}`}
              className={
                ["movement", "gas"].includes(n.condition) ? "is-alert" : ""
              }
            >
              <b>{n.id}</b>
              {NAMES[n.id]}
            </a>
          ))}
        </nav>
        <label className="search-field">
          <Icon name="search" size={17} />
          <input
            aria-label="Search stations"
            placeholder="Station, channel or state"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>
      </div>

      <div className="station-stack">
        {found.map((n) => (
          <StationFile
            key={n.id}
            node={n}
            model={model}
            onInspect={onInspect}
          />
        ))}
      </div>
      {!found.length && (
        <Empty icon="search" title="No stations match this search.">
          Try a station name, channel, or condition.
        </Empty>
      )}
      <p className="network-footnote">
        Alternate routing and mesh recovery remain hardware milestones. Node B's
        temperature module and Node C's linear-sensor model are still unnamed.
        Network Excel/CSV download every stored sample. Station CSV/JSON
        download the window loaded here (up to 120 samples).
      </p>
    </div>
  );
}
