"use client";
import { useId, useState } from "react";
import { channels, timeLabel, value } from "../lib/format";

function curveThrough(pts) {
  if (!pts.length) return "";
  let d = `M${pts[0][0].toFixed(1)},${pts[0][1].toFixed(1)}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[Math.max(i - 1, 0)],
      p1 = pts[i],
      p2 = pts[i + 1],
      p3 = pts[Math.min(i + 2, pts.length - 1)];
    const c1x = p1[0] + (p2[0] - p0[0]) / 3.2,
      c1y = p1[1] + (p2[1] - p0[1]) / 3.2,
      c2x = p2[0] - (p3[0] - p1[0]) / 3.2,
      c2y = p2[1] - (p3[1] - p1[1]) / 3.2;
    d += `C${c1x.toFixed(1)},${c1y.toFixed(1)} ${c2x.toFixed(1)},${c2y.toFixed(1)} ${p2[0].toFixed(1)},${p2[1].toFixed(1)}`;
  }
  return d;
}

function nearestRow(rows, t) {
  if (!rows?.length || !Number.isFinite(t)) return null;
  let best = null;
  let bestD = Infinity;
  for (const row of rows) {
    const rt = Date.parse(row.sample_time);
    if (!Number.isFinite(rt)) continue;
    const d = Math.abs(rt - t);
    if (d < bestD) {
      bestD = d;
      best = row;
    }
  }
  return best;
}

export function Spark({
  history = [],
  color = "currentColor",
  channel = "tilt_deg",
}) {
  const id = useId().replaceAll(":", "");
  const values = history.map((r) =>
    r.valid === false ? null : Number.isFinite(r[channel]) ? r[channel] : null,
  );
  const valid = values.filter(Number.isFinite);
  if (valid.length < 2) return <span className="muted">No trend</span>;
  const min = Math.min(...valid),
    max = Math.max(...valid),
    pad = Math.max((max - min) * 0.22, 0.04),
    lo = min - pad,
    hi = max + pad;
  const W = 280,
    H = 78,
    L = 8,
    R = 8,
    T = 10,
    B = 14;
  const pts = [];
  values.forEach((v, i) => {
    if (!Number.isFinite(v)) return;
    pts.push([
      L + (i / Math.max(values.length - 1, 1)) * (W - L - R),
      T + ((hi - v) / (hi - lo)) * (H - T - B),
    ]);
  });
  const d = curveThrough(pts);
  const last = pts.at(-1);
  const area = `${d}L${last[0].toFixed(1)},${H - B}L${pts[0][0].toFixed(1)},${H - B}Z`;
  return (
    <svg className="spark" viewBox={`0 0 ${W} ${H}`} aria-hidden="true">
      <defs>
        <linearGradient id={`${id}-fill`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={color} stopOpacity="0.28" />
          <stop offset="1" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      {[0, 1, 2].map((row) => (
        <line
          key={row}
          x1={L}
          x2={W - R}
          y1={T + ((H - T - B) * row) / 2}
          y2={T + ((H - T - B) * row) / 2}
          stroke={color}
          strokeOpacity="0.16"
        />
      ))}
      <path d={area} fill={`url(#${id}-fill)`} />
      <path
        d={d}
        stroke={color}
        strokeWidth="5"
        fill="none"
        strokeLinejoin="round"
        strokeLinecap="round"
        opacity="0.22"
      />
      <path
        d={d}
        stroke={color}
        strokeWidth="1.8"
        fill="none"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      <circle cx={last[0]} cy={last[1]} r="2.4" fill={color} />
    </svg>
  );
}

export function Trend({
  history = [],
  channel = "tilt_deg",
  compare = null,
  compact = false,
  primaryName = "",
  compareName = "",
  alert = false,
  bands = [],
}) {
  const id = useId().replaceAll(":", "");
  const [hover, setHover] = useState(null);
  const [focus, setFocus] = useState(null);
  const meta = channels[channel] || { label: channel, unit: "", precision: 2 };
  const points = history.map((r, i) => ({
    i,
    t: Date.parse(r.sample_time),
    v: r.valid !== false && Number.isFinite(r[channel]) ? r[channel] : null,
  }));
  const good = points.filter((p) => p.v !== null);
  if (good.length < 2)
    return (
      <div className="chart-empty">
        A trend needs at least two valid {meta.label.toLowerCase()} readings.
      </div>
    );
  const tall = !compact && (Boolean(compare) || bands.length > 0);
  const W = 640,
    H = compact ? 150 : tall ? 268 : 214,
    L = 48,
    R = 16,
    T = 18,
    B = 34;
  const comp = (compare || []).filter(
    (r) => r.valid !== false && Number.isFinite(r[channel]),
  );
  const vals = [...good.map((p) => p.v), ...comp.map((p) => p[channel])];
  const rawMin = Math.min(...vals),
    rawMax = Math.max(...vals),
    padding = Math.max((rawMax - rawMin) * 0.16, 0.05);
  const min = rawMin - padding,
    max = rawMax + padding;
  const t0 = points[0].t,
    t1 = points.at(-1).t,
    timed = Number.isFinite(t0) && t1 > t0;
  const x = (p) =>
    L +
    (timed ? (p.t - t0) / (t1 - t0) : p.i / Math.max(points.length - 1, 1)) *
      (W - L - R);
  const y = (v) => T + ((max - v) / (max - min)) * (H - T - B);
  const runsOf = (items) => {
    const runs = [];
    let run = [];
    items.forEach((p) => {
      if (p.v === null || !Number.isFinite(x(p))) {
        if (run.length) runs.push(run);
        run = [];
        return;
      }
      run.push([x(p), y(p.v)]);
    });
    if (run.length) runs.push(run);
    return runs;
  };
  const makePath = (items) => runsOf(items).map(curveThrough).join(" ");
  const stroke = alert ? "#e15b55" : "#8fd0d6";
  const compareStroke = "#e0b15a";
  const pick = hover ?? focus;
  const active =
    pick === null
      ? good.at(-1)
      : good.reduce(
          (a, p) => (Math.abs(x(p) - pick) < Math.abs(x(a) - pick) ? p : a),
          good[0],
        );
  const peer = active ? nearestRow(comp, active.t) : null;
  const peerV = peer && Number.isFinite(peer[channel]) ? peer[channel] : null;
  const deltaV =
    Number.isFinite(active?.v) && Number.isFinite(peerV)
      ? active.v - peerV
      : null;
  const ribbon = (() => {
    if (!comp.length) return "";
    const top = [];
    const bottom = [];
    good.forEach((p) => {
      const row = nearestRow(comp, p.t);
      if (!row) return;
      top.push([x(p), y(p.v)]);
      bottom.push([x(p), y(row[channel])]);
    });
    if (top.length < 2) return "";
    return `${top
      .map(
        (pt, i) =>
          `${i ? "L" : "M"}${pt[0].toFixed(1)},${pt[1].toFixed(1)}`,
      )
      .join(" ")} ${bottom
      .slice()
      .reverse()
      .map((pt) => `L${pt[0].toFixed(1)},${pt[1].toFixed(1)}`)
      .join(" ")} Z`;
  })();
  const toneStroke = (tone) =>
    tone === "alert" ? "#e15b55" : tone === "watch" ? "#8fd0d6" : "#f2f6f3";
  const visibleBands = bands.filter(
    (band) =>
      Number.isFinite(band.value) && band.value >= min && band.value <= max,
  );
  const bandLegend = [];
  for (const band of visibleBands) {
    if (bandLegend.some((item) => item.tone === band.tone)) continue;
    bandLegend.push({
      tone: band.tone,
      label:
        band.tone === "ref"
          ? "Window ref"
          : band.tone === "watch"
            ? "Watch ±0.60°"
            : "Move ±1.20°",
      dash: band.tone === "ref" ? "1 3" : "5 4",
    });
  }
  function moveActive(step) {
    const idx = good.findIndex((p) => p.i === active.i);
    const next = good[Math.min(good.length - 1, Math.max(0, idx + step))];
    if (next) setFocus(x(next));
  }
  return (
    <div className="chart-wrap">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="trend-chart"
        role="img"
        aria-labelledby={id}
        tabIndex={0}
        onMouseMove={(e) => {
          const r = e.currentTarget.getBoundingClientRect();
          setHover(((e.clientX - r.left) / r.width) * W);
        }}
        onMouseLeave={() => setHover(null)}
        onKeyDown={(e) => {
          if (e.key === "ArrowLeft") {
            e.preventDefault();
            moveActive(-1);
          }
          if (e.key === "ArrowRight") {
            e.preventDefault();
            moveActive(1);
          }
        }}
      >
        <title id={id}>
          {primaryName || meta.label}
          {compareName ? ` overlay versus ${compareName}` : ""}: {good[0].v} to{" "}
          {good.at(-1).v} {meta.unit}. Solid line is the selected station;
          dashed line is the overlay. Invalid readings appear as gaps. Arrow
          keys move the sample inspector.
        </title>
        <defs>
          <linearGradient id={`${id}-area`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor={stroke} stopOpacity="0.22" />
            <stop offset="1" stopColor={stroke} stopOpacity="0" />
          </linearGradient>
        </defs>
        {[0, 1, 2, 3].map((i) => {
          const v = min + ((max - min) * i) / 3;
          return (
            <g key={i}>
              <line
                x1={L}
                x2={W - R}
                y1={y(v)}
                y2={y(v)}
                className="chart-grid"
              />
              <text
                x={L - 12}
                y={y(v) + 4}
                textAnchor="end"
                className="axis-label"
              >
                {value(v, channel.includes("raw") ? 0 : max - min < 1 ? 2 : 1)}
              </text>
            </g>
          );
        })}
        {visibleBands.map((band) => (
          <line
            key={`${band.tone}-${band.value}`}
            x1={L}
            x2={W - R}
            y1={y(band.value)}
            y2={y(band.value)}
            stroke={toneStroke(band.tone)}
            strokeDasharray={band.tone === "ref" ? "1 3" : "5 4"}
            strokeWidth="1.2"
            opacity="0.9"
          />
        ))}
        {ribbon ? (
          <path d={ribbon} fill={stroke} fillOpacity="0.1" stroke="none" />
        ) : null}
        {compare && (
          <path
            d={makePath(
              comp.map((r, i) => ({
                i,
                t: Date.parse(r.sample_time),
                v: r[channel],
              })),
            )}
            fill="none"
            stroke={compareStroke}
            strokeWidth="2.4"
            strokeDasharray="6 5"
            strokeLinecap="round"
          />
        )}
        {runsOf(points).map((run, i) => {
          const line = curveThrough(run);
          const area = `${line}L${run.at(-1)[0]},${H - B}L${run[0][0]},${H - B}Z`;
          return (
            <g key={i}>
              {!ribbon ? <path d={area} fill={`url(#${id}-area)`} /> : null}
              <path
                d={line}
                fill="none"
                stroke={stroke}
                strokeWidth="7"
                opacity="0.18"
                strokeLinejoin="round"
                strokeLinecap="round"
              />
              <path
                d={line}
                fill="none"
                stroke={stroke}
                strokeWidth="2.4"
                strokeLinejoin="round"
                strokeLinecap="round"
              />
            </g>
          );
        })}
        <circle
          cx={x(good.at(-1))}
          cy={y(good.at(-1).v)}
          r="4"
          fill={stroke}
          stroke="#10181c"
          strokeWidth="2"
        />
        {comp.length ? (
          <circle
            cx={x({
              t: Date.parse(comp.at(-1).sample_time),
              i: comp.length - 1,
            })}
            cy={y(comp.at(-1)[channel])}
            r="3.4"
            fill={compareStroke}
            stroke="#10181c"
            strokeWidth="1.6"
          />
        ) : null}
        {[points[0], points[Math.floor(points.length / 2)], points.at(-1)].map(
          (p, i) => (
            <text
              key={i}
              x={x(p)}
              y={H - 7}
              textAnchor={i === 0 ? "start" : i === 2 ? "end" : "middle"}
              className="axis-label"
            >
              {timed
                ? timeLabel(history[p.i].sample_time)
                : `Sample ${p.i + 1}`}
            </text>
          ),
        )}
        {active && (
          <g>
            <line
              x1={x(active)}
              x2={x(active)}
              y1={T}
              y2={H - B}
              stroke="#f7faf8"
              strokeDasharray="3 4"
              opacity=".28"
            />
            <circle cx={x(active)} cy={y(active.v)} r="5" fill={stroke} />
            {peerV != null ? (
              <circle
                cx={x(active)}
                cy={y(peerV)}
                r="4"
                fill="none"
                stroke={compareStroke}
                strokeWidth="2"
              />
            ) : null}
          </g>
        )}
      </svg>
      <div className="inspect-strip" aria-live="polite">
        <span>
          <small>Sample</small>
          <b>
            {active
              ? timeLabel(history[active.i].sample_time)
              : "—"}
          </b>
        </span>
        <span>
          <small>{primaryName || "Station"}</small>
          <b>
            {value(active?.v, meta.precision)}
            <em>{meta.unit}</em>
          </b>
        </span>
        {compare ? (
          <span>
            <small>{compareName || "Overlay"}</small>
            <b>
              {value(peerV, meta.precision)}
              <em>{meta.unit}</em>
            </b>
          </span>
        ) : null}
        {compare ? (
          <span>
            <small>Difference</small>
            <b>
              {deltaV == null
                ? "—"
                : `${deltaV >= 0 ? "+" : ""}${value(deltaV, meta.precision)}`}
              <em>{meta.unit}</em>
            </b>
          </span>
        ) : (
          <span>
            <small>Window</small>
            <b>{good.length} valid</b>
          </span>
        )}
      </div>
      <div className="chart-caption">
        <span>
          <i className="line-key" style={{ borderColor: stroke }} />
          {primaryName ? `${primaryName} · ` : ""}
          {meta.label} · solid
        </span>
        <span>
          {compare ? (
            <>
              <i
                className="line-key compare-key"
                style={{ borderColor: compareStroke }}
              />
              {compareName || "Overlay"} · dashed
            </>
          ) : (
            `${good.length} valid observations`
          )}
        </span>
        {bandLegend.map((item) => (
          <span key={item.tone}>
            <i
              className="line-key"
              style={{
                borderColor: toneStroke(item.tone),
                borderStyle: "dotted",
              }}
            />
            {item.label}
          </span>
        ))}
      </div>
    </div>
  );
}

const COMPARE = [
  { key: "tilt_deg", label: "Tilt", color: "#7ec8c3" },
  { key: "potentiometer_raw", label: "Displacement", color: "#c9b48a" },
  { key: "gas_raw", label: "Gas", color: "#a9b7c9" },
  { key: "temperature_c", label: "Temperature", color: "#8fbfa8" },
];

export function CompareTrends({ history = [], dangers = {} }) {
  const id = useId().replaceAll(":", "");
  const W = 640,
    H = 214,
    L = 48,
    R = 16,
    T = 20,
    B = 34;
  const prepared = COMPARE.map((series) => {
    const samples = (history || [])
      .map((row, i) => ({
        i,
        t: Date.parse(row.sample_time),
        v:
          row.valid !== false && Number.isFinite(row[series.key])
            ? row[series.key]
            : null,
      }))
      .filter((point) => point.v !== null);
    return { ...series, samples, danger: Boolean(dangers[series.key]) };
  }).filter((series) => series.samples.length >= 2);
  if (!prepared.length)
    return (
      <div className="chart-empty">
        This node has fewer than two stored readings on these channels.
      </div>
    );
  const times = prepared.flatMap((series) =>
    series.samples.map((point) => point.t),
  );
  const t0 = Math.min(...times.filter(Number.isFinite));
  const t1 = Math.max(...times.filter(Number.isFinite));
  const timed = Number.isFinite(t0) && t1 > t0;
  const xOf = (point, index, count) =>
    L +
    (timed ? (point.t - t0) / (t1 - t0) : index / Math.max(count - 1, 1)) *
      (W - L - R);
  const drawn = prepared.map((series) => {
    const lo = Math.min(...series.samples.map((point) => point.v));
    const hi = Math.max(...series.samples.map((point) => point.v));
    const span = Math.max(hi - lo, 1e-6);
    const pts = series.samples.map((point, index) => [
      xOf(point, index, series.samples.length),
      T + ((hi - point.v) / span) * (H - T - B),
    ]);
    return { ...series, pts, lo, hi, current: series.samples.at(-1).v };
  });
  return (
    <div className="chart-wrap">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="trend-chart"
        role="img"
        aria-labelledby={id}
      >
        <title id={id}>
          Tilt, displacement, gas, and temperature scaled to their own recorded
          range.
        </title>
        {[0, 1, 2, 3].map((step) => (
          <g key={step}>
            <line
              x1={L}
              x2={W - R}
              y1={T + ((H - T - B) * step) / 3}
              y2={T + ((H - T - B) * step) / 3}
              className="chart-grid"
            />
            <text
              x={L - 10}
              y={T + ((H - T - B) * step) / 3 + 4}
              textAnchor="end"
              className="axis-label"
            >
              {["High", "Mid", "Low", ""][step]}
            </text>
          </g>
        ))}
        {drawn.map((series) => {
          const line = curveThrough(series.pts);
          const color = series.danger ? "#d98980" : series.color;
          return (
            <g key={series.key}>
              <path
                d={line}
                fill="none"
                stroke={color}
                strokeWidth={series.danger ? 6 : 4}
                opacity="0.16"
                strokeLinecap="round"
              />
              <path
                d={line}
                fill="none"
                stroke={color}
                strokeWidth={series.danger ? 2.6 : 1.8}
                strokeLinecap="round"
              />
              <circle
                cx={series.pts.at(-1)[0]}
                cy={series.pts.at(-1)[1]}
                r={series.danger ? 4 : 3}
                fill={color}
              />
            </g>
          );
        })}
      </svg>
      <ul className="compare-legend">
        {drawn.map((series) => (
          <li key={series.key} data-danger={series.danger ? "yes" : "no"}>
            <i style={{ background: series.danger ? "#d98980" : series.color }} />
            <span>{series.label}</span>
            <b>
              {value(series.current, channels[series.key]?.precision ?? 1)}{" "}
              {channels[series.key]?.unit}
            </b>
            {series.danger ? <em>In danger</em> : null}
          </li>
        ))}
      </ul>
      <p className="trend-note">
        Each line uses its own recorded range, so the shapes can be compared.
        The units are not shared.
        {drawn.some((series) => series.danger)
          ? " The marked channel is the one currently tripping a warning rule."
          : " No channel on this node is tripping a warning rule."}
      </p>
    </div>
  );
}
