"use client";
import { useMemo, useState } from "react";
import Link from "next/link";
import { Experiments } from "./Experiments";
import { Badge } from "./Primitives";
import { Spark, Trend } from "./Trend";
import { Icon } from "./icons";
import { SENSOR_INFO } from "./SignalChart";
import { NAMES, PLACEMENTS } from "./MineOverview";
import { channels, delta, value } from "../lib/format";

const ALERTS = ["movement", "gas"];
const WATCH_DEG = 0.6;
const MOVEMENT_DEG = 1.2;

function pickCompare(nodes, id, channel) {
  return (
    nodes.find((o) => o.id !== id && o.capabilities.includes(channel))?.id || ""
  );
}

function csvCell(v) {
  const s = String(v ?? "");
  return /[",\n]/.test(s) ? `"${s.replaceAll('"', '""')}"` : s;
}

function signed(n, precision) {
  if (!Number.isFinite(n)) return "—";
  return `${n > 0 ? "+" : ""}${value(n, precision)}`;
}

function downloadOverlay(node, other, channel, history, compareHist) {
  const meta = channels[channel] || { label: channel, unit: "" };
  const rows = [
    [
      "sample_time",
      `${node.id}_${channel}`,
      other ? `${other.id}_${channel}` : "",
      "unit",
    ]
      .filter(Boolean)
      .join(","),
  ];
  const times = new Set([
    ...(history || []).map((r) => r.sample_time),
    ...(compareHist || []).map((r) => r.sample_time),
  ]);
  [...times]
    .sort()
    .forEach((t) => {
      const a = (history || []).find((r) => r.sample_time === t);
      const b = (compareHist || []).find((r) => r.sample_time === t);
      rows.push(
        [
          t,
          Number.isFinite(a?.[channel]) ? a[channel] : "",
          other ? (Number.isFinite(b?.[channel]) ? b[channel] : "") : "",
          meta.unit,
        ]
          .filter((_, i) => other || i !== 2)
          .map(csvCell)
          .join(","),
      );
    });
  const blob = new Blob([`${rows.join("\n")}\n`], {
    type: "text/csv;charset=utf-8",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `mole-overlay-${node.id}${other ? `-vs-${other.id}` : ""}-${channel}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

function tiltBands(baseline) {
  if (!Number.isFinite(baseline)) return [];
  return [
    { value: baseline, label: "Window ref", tone: "ref" },
    { value: baseline + WATCH_DEG, label: `Watch +${WATCH_DEG.toFixed(2)}°`, tone: "watch" },
    { value: baseline - WATCH_DEG, label: `Watch −${WATCH_DEG.toFixed(2)}°`, tone: "watch" },
    {
      value: baseline + MOVEMENT_DEG,
      label: `Move +${MOVEMENT_DEG.toFixed(2)}°`,
      tone: "alert",
    },
    {
      value: baseline - MOVEMENT_DEG,
      label: `Move −${MOVEMENT_DEG.toFixed(2)}°`,
      tone: "alert",
    },
  ];
}

export function Analytics({ data }) {
  const [id, setId] = useState("B");
  const [channel, setChannel] = useState("tilt_deg");
  const [compareId, setCompareId] = useState("A");
  const [range, setRange] = useState("all");
  const n = data.nodes.find((node) => node.id === id) || data.nodes[0];
  const a = n.analysis || {};
  const peers = data.nodes.filter(
    (o) => o.id !== n.id && o.capabilities.includes(channel),
  );
  const other = data.nodes.find((o) => o.id === compareId && o.id !== n.id);
  const slice = (node) =>
    range === "last" ? node.history.slice(-6) : node.history;
  const history = slice(n);
  const compareHist = other ? slice(other) : null;
  const meta = channels[channel] || {
    label: "IR detection",
    unit: "state",
    precision: 0,
  };
  const change = delta({ ...n, history }, channel);
  const latest = n.latest?.valid !== false ? n.latest?.[channel] : null;
  const otherLatest =
    other?.latest?.valid !== false ? other.latest?.[channel] : null;
  const vs =
    Number.isFinite(latest) && Number.isFinite(otherLatest)
      ? latest - otherLatest
      : null;
  const alert = ALERTS.includes(n.condition);
  const info = SENSOR_INFO[channel];
  const bands = channel === "tilt_deg" ? tiltBands(a.features?.baseline_deg) : [];
  const multiples = useMemo(() => {
    const scored = data.nodes.map((node) => {
      const hist =
        range === "last" ? node.history.slice(-6) : node.history;
      const has = node.capabilities.includes(channel);
      const d = has ? delta({ ...node, history: hist }, channel) : null;
      return {
        node,
        has,
        delta: d,
        tiltDelta: node.analysis?.features?.delta_deg,
        baseline: node.analysis?.features?.baseline_deg,
        hot: ALERTS.includes(node.condition),
      };
    });
    const order = [...scored].sort((x, y) => {
      const ax = Math.abs(x.delta ?? -Infinity);
      const ay = Math.abs(y.delta ?? -Infinity);
      if (Number.isFinite(ax) !== Number.isFinite(ay))
        return Number.isFinite(ay) ? 1 : -1;
      return ay - ax;
    });
    return order.map((row, i) => ({ ...row, rank: i + 1 }));
  }, [data.nodes, channel, range]);

  function selectStation(nextId) {
    const node = data.nodes.find((item) => item.id === nextId);
    const nextChannel = node?.capabilities.includes(channel)
      ? channel
      : node?.capabilities.includes("tilt_deg")
        ? "tilt_deg"
        : node?.capabilities[0] || "tilt_deg";
    setId(nextId);
    setChannel(nextChannel);
    setCompareId(pickCompare(data.nodes, nextId, nextChannel));
  }

  function selectChannel(nextChannel) {
    setChannel(nextChannel);
    setCompareId((current) => {
      const keep = data.nodes.find(
        (o) =>
          o.id === current &&
          o.id !== n.id &&
          o.capabilities.includes(nextChannel),
      );
      return keep ? current : pickCompare(data.nodes, n.id, nextChannel);
    });
  }

  return (
    <div className="analysis-desk">
      <section className="multiples" aria-label="Station ranking on this channel">
        {multiples.map((row) => {
          const selected = row.node.id === n.id;
          const sparkColor = row.hot ? "#e15b55" : "#8fd0d6";
          return (
            <button
              key={row.node.id}
              type="button"
              className={`multiple ${selected ? "is-active" : ""} ${row.hot ? "is-alert" : ""}`}
              aria-pressed={selected}
              onClick={() => selectStation(row.node.id)}
            >
              <header>
                <b>{row.node.id}</b>
                <span className="rank-index">
                  {String(row.rank).padStart(2, "0")}
                </span>
                <div>
                  <small>{PLACEMENTS[row.node.id]}</small>
                  <strong>{NAMES[row.node.id]}</strong>
                </div>
                {row.node.condition !== "normal" ? (
                  <Badge condition={row.node.condition} />
                ) : (
                  <em>Steady</em>
                )}
              </header>
              {row.has ? (
                <Spark
                  history={
                    range === "last"
                      ? row.node.history.slice(-6)
                      : row.node.history
                  }
                  channel={channel}
                  color={sparkColor}
                />
              ) : (
                <p className="not-installed">
                  {meta.label} is not installed here.
                </p>
              )}
              <footer>
                <span>
                  Window Δ
                  <b>
                    {row.has
                      ? `${signed(row.delta, meta.precision)} ${meta.unit}`
                      : "—"}
                  </b>
                </span>
                <span>
                  Tilt vs own ref
                  <b>{signed(row.tiltDelta, 2)}°</b>
                </span>
              </footer>
            </button>
          );
        })}
      </section>

      <div className="desk-grid">
        <article className={`stage ${alert ? "is-alert" : ""}`}>
          <header className="stage-head">
            <div>
              <p className="station-kicker">
                Same clock · {n.latest?.origin || "unknown"} origin
              </p>
              <h2>
                {NAMES[n.id]}
                {other ? ` overlay vs ${NAMES[other.id]}` : " · this station only"}
              </h2>
              <p>
                Two traces share one time axis and one installed channel.
                {channel === "tilt_deg"
                  ? " The pale dotted line is this station’s window reference. Cyan is watch (±0.60°). Red is movement (±1.20°). Those bands are laboratory settings, not a certified safe angle."
                  : ` This chart is ${meta.label.toLowerCase()}. The laboratory warning still reads the tilt window.`}
              </p>
            </div>
            {n.condition !== "normal" ? (
              <Badge condition={n.condition} />
            ) : (
              <span className="station-state">Steady</span>
            )}
          </header>

          <div className="stage-controls">
            <div>
              <p>Channel</p>
              <div className="chip-row">
                {n.capabilities.map((key) => (
                  <button
                    key={key}
                    type="button"
                    aria-pressed={channel === key}
                    onClick={() => selectChannel(key)}
                  >
                    {channels[key]?.label || "IR detection"}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <p>Overlay</p>
              <div className="chip-row">
                <button
                  type="button"
                  aria-pressed={!other}
                  onClick={() => setCompareId("")}
                >
                  This station only
                </button>
                {peers.map((o) => (
                  <button
                    key={o.id}
                    type="button"
                    aria-pressed={compareId === o.id}
                    onClick={() => setCompareId(o.id)}
                  >
                    {NAMES[o.id]}
                  </button>
                ))}
                {!peers.length && (
                  <span className="chip-empty">
                    No other station carries {meta.label.toLowerCase()}.
                  </span>
                )}
              </div>
            </div>
            <div>
              <p>Window</p>
              <div className="chip-row">
                <button
                  type="button"
                  aria-pressed={range === "all"}
                  onClick={() => setRange("all")}
                >
                  Full window
                </button>
                <button
                  type="button"
                  aria-pressed={range === "last"}
                  onClick={() => setRange("last")}
                >
                  Last 6
                </button>
              </div>
            </div>
          </div>

          <dl className="readout">
            <div>
              <dt>Latest {meta.label.toLowerCase()}</dt>
              <dd>
                {value(latest, meta.precision)}
                <small>{meta.unit}</small>
              </dd>
            </div>
            <div>
              <dt>Window change</dt>
              <dd>
                {signed(change, meta.precision)}
                <small>{meta.unit}</small>
              </dd>
            </div>
            <div>
              <dt>
                {other
                  ? `${NAMES[n.id]} − ${NAMES[other.id]}`
                  : "Overlay difference"}
              </dt>
              <dd>
                {vs == null ? "—" : signed(vs, meta.precision)}
                <small>{other ? meta.unit : ""}</small>
              </dd>
            </div>
            <div>
              <dt>Tilt Δ vs own reference</dt>
              <dd>
                {signed(a.features?.delta_deg, 2)}
                <small>°</small>
              </dd>
            </div>
          </dl>

          <p className="sensor-line">
            {info?.sensor} · {info?.limit} {info?.note}
          </p>

          <Trend
            history={history}
            channel={channel}
            compare={compareHist}
            primaryName={NAMES[n.id]}
            compareName={other ? NAMES[other.id] : ""}
            alert={alert && channel === "tilt_deg"}
            bands={bands}
          />

          <div className="overlay-toolbar">
            <button
              type="button"
              className="button light"
              onClick={() =>
                downloadOverlay(n, other, channel, history, compareHist)
              }
            >
              <Icon name="download" size={16} />
              Overlay CSV
            </button>
            <Link className="button light" href="/nodes">
              Open station dossiers
              <Icon name="arrow" size={16} />
            </Link>
          </div>
        </article>

        <aside className="dock" aria-label="Rule evidence">
          <article>
            <p className="station-kicker">Why this state</p>
            <h3>The rule, in order.</h3>
            <ol>
              {(a.evidence || ["Awaiting sufficient measurements."]).map(
                (item, i) => (
                  <li key={i}>
                    <span>{String(i + 1).padStart(2, "0")}</span>
                    <p>{item}</p>
                  </li>
                ),
              )}
            </ol>
            <dl className="stat-row">
              <div>
                <dt>Window ref</dt>
                <dd>
                  {value(a.features?.baseline_deg, 2)}
                  <small>°</small>
                </dd>
              </div>
              <div>
                <dt>Robust z</dt>
                <dd>{value(a.features?.robust_z, 2)}</dd>
              </div>
              <div>
                <dt>Trend</dt>
                <dd>
                  {value(a.features?.slope_deg_min, 3)}
                  <small>°/min</small>
                </dd>
              </div>
              <div>
                <dt>Sustained</dt>
                <dd>{a.features?.sustained_samples ?? "—"}</dd>
              </div>
            </dl>
            <p className="footnote">
              Prototype rules use laboratory settings. They are not a certified
              safe working limit.
            </p>
          </article>

          <article>
            <p className="station-kicker">Input quality</p>
            <h3>Coverage is not safety.</h3>
            <div className="quality-row">
              <strong>
                {a.quality?.coverage_pct ?? "—"}
                <small>%</small>
              </strong>
              <div>
                <div className="coverage-track">
                  <i style={{ width: `${a.quality?.coverage_pct || 0}%` }} />
                </div>
                <p>
                  {a.quality?.valid_count ?? "—"} /{" "}
                  {a.quality?.total_count ?? "—"} valid · {n.latest?.origin || "—"}{" "}
                  · {value(a.features?.duration_min, 0)} min
                </p>
              </div>
            </div>
          </article>

          <article>
            <p className="station-kicker">What is running</p>
            <h3>Authority stays with the rule.</h3>
            <ul className="rule-stack">
              <li className="is-on">
                <i />
                <div>
                  <strong>Rules &amp; robust trends</strong>
                  <p>
                    {a.rule_version || "prototype-window-v2"} · this is the
                    warning.
                  </p>
                </div>
              </li>
              <li className="is-on">
                <i />
                <div>
                  <strong>Window shift</strong>
                  <p>
                    {a.features?.window_shift_deg == null
                      ? "No median-half shift of 0.40° in this window."
                      : `Descriptive shift ${value(a.features.window_shift_deg, 2)}°.`}
                  </p>
                </div>
              </li>
              <li>
                <i />
                <div>
                  <strong>Isolation Forest</strong>
                  <p>
                    {a.shadow?.reason ||
                      "Not loaded. Does not change the warning."}
                  </p>
                </div>
              </li>
              <li>
                <i />
                <div>
                  <strong>20-second forecast</strong>
                  <p>
                    Synthetic-trained ridge. Experimental overlay on station
                    graphs, not a safety prediction.
                  </p>
                </div>
              </li>
              <li>
                <i />
                <div>
                  <strong>Calibrated displacement forecast</strong>
                  <p>Awaiting millimetre calibration of the potentiometer.</p>
                </div>
              </li>
            </ul>
            <p className="footnote">
              {a.model_state ||
                "No trained artifact loaded. Window statistics and laboratory rules only."}{" "}
              A future model cannot silently dismiss an active local warning.
            </p>
          </article>
        </aside>
      </div>

      <section className="archive-block">
        <Experiments />
      </section>
    </div>
  );
}
