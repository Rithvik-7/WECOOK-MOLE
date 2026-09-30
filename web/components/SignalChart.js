"use client";
import { useId, useState, useRef, useEffect } from "react";
import { channels, value } from "../lib/format";
import { predictChannel } from "../lib/forecast.mjs";

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

export const SENSOR_INFO = {
  tilt_deg: {
    sensor: "MPU · inclination",
    description: "Angular movement of the ground at this point.",
    limit: "Watch: ±0.60° change · alert: ±1.20° sustained for 3 readings.",
    note: "Relative to the window reference; laboratory settings, not a certified safe angle.",
  },
  vibration: {
    sensor: "MPU · accelerometer",
    description: "Relative vibration intensity at the node.",
    limit: "Watch at 2.50 relative units.",
    note: "Not calibrated to mm/s or a seismic magnitude.",
  },
  potentiometer_raw: {
    sensor: "Slider",
    description: "Mechanical movement expressed as ADC counts.",
    limit: "No calibrated displacement limit.",
    note: "Conversion to millimetres requires mechanical calibration.",
  },
  linear_raw: {
    sensor: "Linear sensor",
    description: "Second displacement input on Node C, in ADC counts.",
    limit: "No calibrated stroke.",
    note: "The module and stroke are not confirmed. Counts are not millimetres.",
  },
  temperature_signal_raw: {
    sensor: "Temperature signal",
    description: "Single-wire temperature input on Node B.",
    limit: "No temperature limit.",
    note: "The module name is not confirmed. This is an ADC count, not degrees.",
  },
  gas_raw: {
    sensor: "MQ-2 · gas response",
    description: "Heated gas-sensor response, in raw ADC counts.",
    limit: "Prototype alert at 1,800 counts after warm-up.",
    note: "Not a gas concentration or a certified gas alarm.",
  },
  ir: {
    sensor: "IR · detection input",
    description: "Infrared detection state from Node C.",
    limit: "No configured risk limit.",
    note: "Module, active polarity and physical purpose still need confirmation.",
  },
  temperature_c: {
    sensor: "BME280 · temperature",
    description: "Local ambient temperature from the BME280.",
    limit: "No site-approved temperature limit.",
    note: "Node B is a DS18B20. Node D's fitted chip is a BMP280, so this page's humidity channel stays empty. Neither is soil moisture.",
  },
  humidity_pct: {
    sensor: "BME280 · humidity",
    description: "Relative humidity near the ventilation area.",
    limit: "No site-approved humidity limit.",
    note: "Humidity alone does not establish subsidence risk.",
  },
  pressure_hpa: {
    sensor: "BME280 · pressure",
    description: "Local atmospheric pressure.",
    limit: "No site-approved pressure limit.",
    note: "Not groundwater level or underground support pressure.",
  },
};
export function SignalChart({
  node,
  channel,
  model,
  forecastEnabled = true,
  compact = false,
}) {
  const chartRef = useRef(null);
  const [plotWidth, setPlotWidth] = useState(620);
  useEffect(() => {
    const observer = new ResizeObserver((entries) =>
      setPlotWidth(Math.max(240, entries[0].contentRect.width)),
    );
    if (chartRef.current) observer.observe(chartRef.current);
    return () => observer.disconnect();
  }, []);
  const uid = useId(),
    [cursor, setCursor] = useState(null),
    meta = channels[channel] || {
      label: "IR detection",
      unit: "state",
      precision: 0,
    };
  const history = node.history || [],
    good = history.filter(
      (r) =>
        r.valid !== false &&
        Number.isFinite(r[channel]) &&
        Number.isFinite(Date.parse(r.sample_time)),
    );
  const prediction = forecastEnabled
    ? predictChannel(history, channel, model)
    : { available: false, reason: "Forecast hidden.", points: [] };
  const info = SENSOR_INFO[channel],
    latest = node.latest?.valid !== false ? node.latest?.[channel] : null;
  const vals = good.map((r) => r[channel]),
    avg = vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : null;
  const f = prediction.points,
    W = plotWidth,
    H = compact ? 176 : 225,
    L = 52,
    R = 22,
    T = 28,
    B = 36;
  const all = [...vals, ...f.flatMap((p) => [p.lower, p.upper])];
  const extent = all.length ? Math.max(...all) - Math.min(...all) : 1,
    pad = Math.max(
      extent * 0.18,
      channel.includes("raw") ? 1.5 : channel === "ir" ? 0.2 : 0.02,
    );
  const lo = (all.length ? Math.min(...all) : 0) - pad,
    hi = (all.length ? Math.max(...all) : 1) + pad;
  const first = good.length ? Date.parse(good[0].sample_time) : 0,
    last = good.length ? Date.parse(good.at(-1).sample_time) : 1,
    end = f.at(-1)?.time || last;
  const x = (t) => L + ((t - first) / Math.max(end - first, 1)) * (W - L - R),
    y = (v) => T + ((hi - v) / (hi - lo)) * (H - T - B);
  const high =
    channel === "tilt_deg"
      ? ["movement", "watch"].includes(
          node.analysis?.movement_state || node.condition,
        )
      : channel === "gas_raw"
        ? node.analysis?.gas_state === "gas"
        : channel === "vibration"
          ? latest >= 2.5
          : false;
  const line = high ? "#e07a6a" : "#7ec8c3";
  const pts = [];
  history.forEach((r) => {
    if (
      r.valid === false ||
      !Number.isFinite(r[channel]) ||
      !Number.isFinite(Date.parse(r.sample_time))
    ) {
      return;
    }
    pts.push([x(Date.parse(r.sample_time)), y(r[channel])]);
  });
  const d = curveThrough(pts);
  const lastPt = pts.at(-1);
  const area =
    pts.length > 1
      ? `${d} L${lastPt[0].toFixed(1)},${H - B} L${pts[0][0].toFixed(1)},${H - B} Z`
      : "";
  const latestGood = good.at(-1),
    anchor = latestGood ? `${x(last)},${y(latestGood[channel])}` : "";
  const gid = uid.replaceAll(":", "");
  const forecastPath = f.length
    ? `M${anchor} ` + f.map((p) => `L${x(p.time)},${y(p.value)}`).join(" ")
    : "";
  const band = f.length
    ? `M${anchor} ` +
      f.map((p) => `L${x(p.time)},${y(p.upper)}`).join(" ") +
      [...f]
        .reverse()
        .map((p) => `L${x(p.time)},${y(p.lower)}`)
        .join(" ") +
      " Z"
    : "";
  const active =
    cursor === null
      ? null
      : good.reduce(
          (a, b) =>
            Math.abs(x(Date.parse(a.sample_time)) - cursor) <
            Math.abs(x(Date.parse(b.sample_time)) - cursor)
              ? a
              : b,
          good[0],
        );
  const seconds = (t) =>
    new Date(t).toLocaleTimeString("en-IN", {
      hour12: false,
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  return (
    <article
      ref={chartRef}
      className={`signal-card ${compact ? "is-compact" : ""} ${high ? "signal-warning" : ""}`}
    >
      <header>
        <div>
          <p className="sensor-label">{info?.sensor}</p>
          <h3>{meta.label}</h3>
        </div>
        <div className="signal-current">
          {value(latest, meta.precision)}
          <small>{meta.unit}</small>
        </div>
      </header>
      <p className="signal-description">{compact ? null : info?.description}</p>
      {good.length < 2 ? (
        <div className="signal-empty">
          {channel === "ir"
            ? "Waiting for an IR reading."
            : "Waiting for two valid observations."}
        </div>
      ) : (
        <>
          <svg
            className="signal-svg"
            viewBox={`0 0 ${W} ${H}`}
            role="img"
            aria-labelledby={uid}
            onPointerMove={(e) => {
              const r = e.currentTarget.getBoundingClientRect();
              setCursor(((e.clientX - r.left) / r.width) * W);
            }}
            onPointerLeave={() => setCursor(null)}
          >
            <title id={uid}>
              {node.name} {meta.label}. {good.length} valid observations.{" "}
              {prediction.available
                ? "Dashed line shows the experimental 20-second forecast."
                : prediction.reason}
            </title>
            <defs>
              <linearGradient id={`${gid}-fill`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0" stopColor={line} stopOpacity="0.32" />
                <stop offset="1" stopColor={line} stopOpacity="0" />
              </linearGradient>
            </defs>
            {[0, 1, 2, 3].map((i) => {
              const v = lo + ((hi - lo) * i) / 3;
              return (
                <g key={i}>
                  <line
                    x1={L}
                    x2={W - R}
                    y1={y(v)}
                    y2={y(v)}
                    stroke="rgba(214,226,220,0.16)"
                  />
                  <text x={L - 10} y={y(v) + 4} textAnchor="end" fill="#c5d0ca">
                    {value(
                      v,
                      channel.includes("raw") ? 0 : hi - lo < 1 ? 2 : 1,
                    )}
                  </text>
                </g>
              );
            })}
            {band && <path d={band} fill="#c4a574" opacity=".18" />}
            {area && <path d={area} fill={`url(#${gid}-fill)`} />}
            <path
              d={d}
              fill="none"
              stroke={line}
              strokeWidth="4.5"
              strokeLinejoin="round"
              strokeLinecap="round"
              opacity="0.22"
            />
            <path
              d={d}
              fill="none"
              stroke={line}
              strokeWidth="2.6"
              strokeLinejoin="round"
              strokeLinecap="round"
            />
            {lastPt && (
              <circle
                className="signal-now"
                cx={lastPt[0]}
                cy={lastPt[1]}
                r="4.5"
                fill={line}
                stroke="#07090c"
                strokeWidth="1.5"
              />
            )}
            {f.length > 0 && (
              <>
                <line
                  x1={x(last)}
                  x2={x(last)}
                  y1={T}
                  y2={H - B}
                  stroke="#9aa8a1"
                  strokeDasharray="4 4"
                />
                <path
                  d={forecastPath}
                  fill="none"
                  stroke="#e0b15a"
                  strokeWidth="2.4"
                  strokeDasharray="6 5"
                  strokeLinecap="round"
                />
                <text x={x(last) - 5} y={16} textAnchor="end" fill="#e7eee9">
                  Latest
                </text>
                <text x={W - R} y={16} textAnchor="end" fill="#e0b15a">
                  +20s
                </text>
              </>
            )}
            {[first, first + (last - first) / 2, last].map((t, i) => (
              <text
                key={i}
                x={x(t)}
                y={H - 10}
                textAnchor={i === 0 ? "start" : i === 2 ? "end" : "middle"}
                fill="#c5d0ca"
              >
                {seconds(t)}
              </text>
            ))}
            {active && (
              <>
                <line
                  x1={x(Date.parse(active.sample_time))}
                  x2={x(Date.parse(active.sample_time))}
                  y1={T}
                  y2={H - B}
                  stroke="#c5d0ca"
                />
                <circle
                  cx={x(Date.parse(active.sample_time))}
                  cy={y(active[channel])}
                  r="5"
                  fill={line}
                />
              </>
            )}
          </svg>
          <div className="chart-readout">
            {active ? (
              `${seconds(Date.parse(active.sample_time))} · ${value(active[channel], meta.precision)} ${meta.unit}`
            ) : (
              <>
                <span>
                  <i />
                  Observed
                </span>
                {prediction.available && (
                  <>
                    <span>
                      <i className="forecast-key" />
                      20s forecast
                    </span>
                    <span className="band-key">Residual band</span>
                  </>
                )}
              </>
            )}
          </div>
        </>
      )}
      <div className="signal-statistics">
        <span>
          Minimum
          <b>{value(vals.length ? Math.min(...vals) : null, meta.precision)}</b>
        </span>
        <span>
          Average<b>{value(avg, meta.precision)}</b>
        </span>
        <span>
          Maximum
          <b>{value(vals.length ? Math.max(...vals) : null, meta.precision)}</b>
        </span>
        <span>
          At +20s<b>{value(f.at(-1)?.value, meta.precision)}</b>
        </span>
      </div>
      <p className="forecast-state">
        {prediction.available
          ? "Experimental forecast · synthetic-trained model"
          : prediction.reason}
      </p>
      <div className="signal-limit">
        <strong>{info?.limit}</strong>
        <span>{info?.note}</span>
      </div>
      <details className="chart-details">
        <summary>Data &amp; forecast details</summary>
        <p>{prediction.reason}</p>
        <p>
          {good.length} valid samples · {node.latest?.origin || "unknown"}{" "}
          source · {model?.version || "no model loaded"}. Bands are calibrated
          on synthetic sessions, not mine data.
        </p>
        <div className="sample-table">
          <table>
            <thead>
              <tr>
                <th>Time</th>
                <th>
                  {meta.label} ({meta.unit})
                </th>
              </tr>
            </thead>
            <tbody>
              {good.slice(-60).map((r, i) => (
                <tr key={i}>
                  <td>{seconds(Date.parse(r.sample_time))}</td>
                  <td>{value(r[channel], meta.precision)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </article>
  );
}
