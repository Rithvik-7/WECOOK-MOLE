"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Badge } from "./Primitives";
import { SignalChart, SENSOR_INFO } from "./SignalChart";
import { Icon } from "./icons";
import { channels, delta, labels, timeLabel, value } from "../lib/format";

export const PLACEMENTS = {
  A: "Mine entrance",
  B: "Central surface panel",
  C: "Ventilation shaft",
  D: "Beside ventilation · right side",
};
export const NAMES = {
  A: "Entrance",
  B: "Surface",
  C: "Shaft",
  D: "Vent",
};
const MARKERS = {
  A: { x: 16, y: 50, lx: 12, ly: 78 },
  B: { x: 46, y: 30, lx: 40, ly: 9 },
  C: { x: 73, y: 15, lx: 62, ly: 5 },
  D: { x: 90, y: 42, lx: 92, ly: 64 },
};
const ALERTS = ["movement", "gas"];
function tone(n) {
  return ALERTS.includes(n.condition)
    ? "danger"
    : n.condition === "watch"
      ? "watch"
      : n.condition === "normal"
        ? "calm"
        : "unknown";
}

export function MineScene({ nodes, selected, onSelect, compact = false }) {
  return (
    <div className={`mine-scene ${compact ? "scene-compact" : ""}`}>
      <img
        src="/images/mine-cutaway.png"
        width="1118"
        height="720"
        alt="Isolated 3D cutaway of the underground mine. Entrance at left, surface road on top, ventilation shaft at right, coal gallery below."
        fetchPriority={compact ? "auto" : "high"}
        loading={compact ? "lazy" : "eager"}
      />
      <svg viewBox="0 0 1000 667" className="mine-leaders" aria-hidden="true">
        {nodes.map((n) => {
          const p = MARKERS[n.id];
          return p ? (
            <path
              key={n.id}
              d={`M${p.x * 10} ${p.y * 6.67} L${p.lx * 10} ${p.ly * 6.67}`}
              className={tone(n)}
            />
          ) : null;
        })}
      </svg>
      {nodes.map((n) => {
        const p = MARKERS[n.id];
        return p ? (
          <div key={n.id}>
            <button
              className={`mine-pin ${tone(n)} ${selected === n.id ? "selected" : ""}`}
              style={{ left: `${p.x}%`, top: `${p.y}%` }}
              onClick={() => onSelect(n.id)}
              aria-label={`Select ${NAMES[n.id]}, ${PLACEMENTS[n.id]}, ${n.condition.replaceAll("_", " ")}`}
              aria-pressed={selected === n.id}
            >
              <span />
            </button>
            <button
              className={`mine-callout ${tone(n)}`}
              style={{ left: `${p.lx}%`, top: `${p.ly}%` }}
              onClick={() => onSelect(n.id)}
            >
              <b>{NAMES[n.id]}</b>
              <span>
                {n.condition === "normal"
                  ? "Steady"
                  : n.condition.replaceAll("_", " ")}
              </span>
            </button>
          </div>
        ) : null;
      })}
    </div>
  );
}

function windowInfo(node, key = "tilt_deg") {
  const rows = (node.history || []).filter(
    (r) => r.valid !== false && Number.isFinite(r[key]),
  );
  const vals = rows.map((r) => r[key]);
  return {
    count: rows.length,
    min: vals.length ? Math.min(...vals) : null,
    max: vals.length ? Math.max(...vals) : null,
    avg: vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : null,
    last: rows.at(-1)?.sample_time,
    origin: rows.at(-1)?.origin || node.latest?.origin || "unknown",
    change: delta(node, key),
  };
}

export function MineOverview({ data, selected, onSelect }) {
  const [model, setModel] = useState(null);
  useEffect(() => {
    fetch("/models/short-horizon.json")
      .then((r) => (r.ok ? r.json() : null))
      .then(setModel)
      .catch(() => setModel(null));
  }, []);
  const nodes = data.nodes
    .map((n) => ({ ...n, place: PLACEMENTS[n.id] || n.place }))
    .sort((a, b) => a.id.localeCompare(b.id));
  const focus = nodes.find((n) => n.id === selected) || nodes[0];
  const openIncidents = (data.incidents || []).filter(
    (i) => i.status !== "CLOSED",
  );
  const latestIncident = openIncidents[0];
  const missionCount = (data.missions || []).length;
  const rank = { movement: 0, gas: 1, watch: 2, sensor_fault: 3, stale: 4 };
  const attention = nodes
    .filter((n) => n.condition !== "normal")
    .sort((a, b) => (rank[a.condition] ?? 9) - (rank[b.condition] ?? 9));
  const lead = attention[0];
  const leadStats = lead ? windowInfo(lead) : null;
  const latestSample = nodes
    .map((n) => windowInfo(n).last)
    .filter(Boolean)
    .sort()
    .at(-1);
  function showStation(id) {
    onSelect(id);
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    document.getElementById("node-network")?.scrollIntoView({
      behavior: reduce ? "auto" : "smooth",
      block: "start",
    });
  }
  return (
    <div className="mine-overview">
      <section className="mine-hero" aria-label="Mine cutaway">
        <div className="hero-copy">
          <h1>MOLE</h1>
          <p className="mole-expansion">Mine Observation &amp; Land Evaluation</p>
          <div className="hero-brief" aria-live="polite">
            <p className="hero-site">{data.site?.name || "Field panel"}</p>
            <p className={`hero-status ${lead ? "is-alert" : "is-clear"}`}>
              {lead
                ? attention.length === 1
                  ? `1 of ${nodes.length} stations needs attention`
                  : `${attention.length} of ${nodes.length} stations need attention`
                : `All ${nodes.length} stations are steady`}
            </p>
            {lead ? (
              <>
                <p className="hero-lead">
                  <strong>{NAMES[lead.id]}</strong>
                  <span>{labels[lead.condition] || lead.condition}</span>
                </p>
                <p className="hero-note">
                  {lead.analysis?.summary || PLACEMENTS[lead.id]}
                </p>
                <p className="hero-meta">
                  Tilt change{" "}
                  {leadStats.change === null
                    ? "—"
                    : `${leadStats.change >= 0 ? "+" : ""}${value(leadStats.change, 2)}°`}
                  {" · "}
                  {timeLabel(leadStats.last)}
                  {leadStats.origin === "physical" ? "" : ` · ${leadStats.origin}`}
                </p>
                <button
                  type="button"
                  className="hero-jump"
                  onClick={() => showStation(lead.id)}
                >
                  Show {NAMES[lead.id]}
                </button>
              </>
            ) : (
              <p className="hero-meta">Last sample {timeLabel(latestSample)}</p>
            )}
          </div>
        </div>
        <div className="hero-map">
          <MineScene nodes={nodes} selected={focus?.id} onSelect={onSelect} compact />
        </div>
      </section>
      <section id="node-network" className="network-section">
        <div className="observations-grid">
          {nodes.map((n) => {
            const stats = windowInfo(n);
            const change = stats.change;
            return (
              <article
                key={n.id}
                className={`observation-card ${tone(n)} ${n.id === focus?.id ? "is-selected" : ""}`}
              >
                <button
                  className="observation-card-head"
                  onClick={() => onSelect(n.id)}
                  aria-pressed={n.id === focus?.id}
                >
                  <div>
                    <p className="station-kicker">{PLACEMENTS[n.id]}</p>
                    <h3>{NAMES[n.id]}</h3>
                  </div>
                  {n.condition !== "normal" ? (
                    <Badge condition={n.condition} />
                  ) : (
                    <span className="station-state">Steady</span>
                  )}
                </button>
                <dl className="node-readings">
                  {n.capabilities.map((k) => {
                    const c = channels[k] || {
                      label: "IR detection",
                      precision: 0,
                      unit: "state",
                    };
                    return (
                      <div key={k}>
                        <dt>
                          {c.label}
                          <small>{SENSOR_INFO[k]?.sensor || "Sensor"}</small>
                        </dt>
                        <dd>
                          {value(
                            n.latest?.valid !== false ? n.latest?.[k] : null,
                            c.precision,
                          )}
                          <small>{c.unit}</small>
                        </dd>
                      </div>
                    );
                  })}
                </dl>
                <p className="card-brief">
                  {n.analysis?.summary || "No warning at this node."}
                </p>
                <ul className="card-instrument">
                  <li>
                    <b>{stats.count}</b> samples
                  </li>
                  <li>
                    <b>{stats.origin}</b> source
                  </li>
                  <li>
                    Last <b>{timeLabel(stats.last)}</b>
                  </li>
                  <li>
                    Δ tilt{" "}
                    <b>
                      {change === null
                        ? "—"
                        : `${change >= 0 ? "+" : ""}${value(change, 2)}°`}
                    </b>
                  </li>
                  <li>
                    Window{" "}
                    <b>
                      {value(stats.min, 2)}–{value(stats.max, 2)}°
                    </b>
                  </li>
                </ul>
                <div className="card-charts">
                  <SignalChart
                    key={`${n.id}-tilt`}
                    node={{ ...n, history: (n.history || []).slice(-40) }}
                    channel="tilt_deg"
                    model={model}
                    forecastEnabled
                    compact
                  />
                </div>
              </article>
            );
          })}
        </div>
      </section>
      <div className="next-destinations">
        <Link
          href="/incidents"
          className={`dest-card ${openIncidents.length ? "is-alert" : ""}`}
        >
          <span className="dest-icon" aria-hidden="true">
            <Icon name="incidents" size={22} />
          </span>
          <div className="dest-copy">
            <p className="dest-kicker">Response log</p>
            <h3>Incidents</h3>
            <p>
              A warning on a node becomes a record here: evidence, who
              acknowledged it, review, then close. Acknowledging does not
              resolve the alert.
            </p>
            <p className="dest-now">
              {openIncidents.length
                ? `${openIncidents.length} open · ${latestIncident.title}`
                : "No open records. Closed history stays in the log."}
            </p>
          </div>
          <span className="dest-go">
            Open the log
            <Icon name="arrow" size={16} />
          </span>
        </Link>
        <Link href="/rover" className="dest-card">
          <span className="dest-icon" aria-hidden="true">
            <Icon name="rover" size={22} />
          </span>
          <div className="dest-copy">
            <p className="dest-kicker">Inspection unit R1</p>
            <h3>Rover</h3>
            <p>
              Plan an inspection against an incident. Camera, position and
              drive stay unavailable until hardware is paired. This page does
              not send a motion command.
            </p>
            <p className="dest-now">
              {missionCount
                ? `${missionCount} planned mission${missionCount === 1 ? "" : "s"} on file.`
                : "No missions yet. Link a plan to an open incident."}
            </p>
          </div>
          <span className="dest-go">
            Open rover station
            <Icon name="arrow" size={16} />
          </span>
        </Link>
      </div>
    </div>
  );
}
