"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Icon } from "./icons";
import { channels, dateLabel, request, value } from "../lib/format";

const FALLBACK = { label: "Sensor channel", unit: "raw", precision: 2 };
const ZERO_ALLOWANCE = {
  tilt_deg: 0.08,
  vibration: 0.15,
  potentiometer_raw: 8,
  gas_raw: 40,
  temperature_c: 0.5,
  humidity_pct: 3,
  pressure_hpa: 2,
};

function validValues(node, channel) {
  return (node?.history || [])
    .filter((sample) => sample.valid !== false && Number.isFinite(Number(sample[channel])))
    .slice(-8)
    .map((sample) => Number(sample[channel]));
}

function median(values) {
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2
    ? sorted[middle]
    : (sorted[middle - 1] + sorted[middle]) / 2;
}

function display(number, precision) {
  return Number.isFinite(number) ? Number(number).toFixed(precision) : "—";
}

export function CalibrationBoard({ data, paired, onPair, notify, onStateRefresh }) {
  const [nodeId, setNodeId] = useState(data.nodes?.[0]?.id || "A");
  const [channel, setChannel] = useState("tilt_deg");
  const [records, setRecords] = useState([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const errorRef = useRef(null);

  const node = data.nodes.find((item) => item.id === nodeId) || data.nodes[0];
  const installed = node?.capabilities || [];
  const info = channels[channel] || FALLBACK;
  const samples = useMemo(() => validValues(node, channel), [node, channel]);
  const current = samples.at(-1);
  const active = node?.calibrations?.[channel];
  const hasZero = active?.baseline_value !== null && active?.baseline_value !== undefined;
  const baseline = Number(active?.baseline_value);
  const allowance = Number(active?.tolerance ?? ZERO_ALLOWANCE[channel] ?? 0);
  const movement = Number.isFinite(current) && Number.isFinite(baseline)
    ? current - baseline
    : null;
  const isDanger = movement !== null && Math.abs(movement) > allowance;

  useEffect(() => {
    if (!installed.includes(channel)) setChannel(installed[0] || "tilt_deg");
  }, [channel, installed]);

  useEffect(() => setError(""), [nodeId, channel]);

  async function loadRecords() {
    try {
      const result = await request("/api/calibrations");
      setRecords(result.records || []);
    } catch {}
  }

  useEffect(() => {
    loadRecords();
  }, []);

  async function setZero() {
    if (!paired) {
      onPair();
      return;
    }
    if (samples.length < 3) {
      setError("This sensor needs at least three valid readings. Check its connection and try again.");
      errorRef.current?.focus();
      return;
    }

    setSaving(true);
    setError("");
    const zeroAt = median(samples);
    const tolerance = ZERO_ALLOWANCE[channel] ?? Math.max(Math.abs(zeroAt) * 0.01, 0.01);

    try {
      await request("/api/calibrations", {
        node_id: node.id,
        channel,
        mode: "baseline",
        baseline_value: zeroAt,
        reference_value: 0,
        tolerance,
        sample_count: samples.length,
        status: "active",
        unit: info.unit,
        note: `Current ${info.label.toLowerCase()} position set as zero from ${samples.length} stable readings.`,
      });
      await Promise.all([loadRecords(), onStateRefresh?.()]);
      notify(`${node.name} ${info.label.toLowerCase()} is now zeroed.`);
    } catch (requestError) {
      setError(requestError.message);
      errorRef.current?.focus();
    } finally {
      setSaving(false);
    }
  }

  const selectedRecords = records.filter(
    (record) => record.node_id === node?.id && record.channel === channel,
  );

  return (
    <div className="zero-page">
      <section className="zero-card" aria-labelledby="zero-title">
        <div className="zero-intro">
          <span className="zero-icon"><Icon name="calibrate" size={28} /></span>
          <div>
            <p className="eyebrow">QUICK CALIBRATION</p>
            <h2 id="zero-title">Set the current position as zero</h2>
            <p>Place the sensor in its normal position and keep it still. After zeroing, movement beyond the small noise allowance is shown as danger.</p>
          </div>
        </div>

        {error && (
          <div className="zero-error" role="alert" tabIndex="-1" ref={errorRef}>
            <Icon name="info" /><span>{error}</span>
          </div>
        )}

        <div className="zero-selectors">
          <label className="form-label">
            1. Select station
            <select value={nodeId} onChange={(event) => setNodeId(event.target.value)}>
              {data.nodes.map((item) => (
                <option key={item.id} value={item.id}>{item.name} · {item.place}</option>
              ))}
            </select>
          </label>
          <label className="form-label">
            2. Select sensor
            <select value={channel} onChange={(event) => setChannel(event.target.value)}>
              {installed.map((key) => (
                <option key={key} value={key}>{(channels[key] || FALLBACK).label}</option>
              ))}
            </select>
          </label>
        </div>

        <div className={`zero-reading ${hasZero ? (isDanger ? "is-danger" : "is-safe") : "is-ready"}`} aria-live="polite">
          <div>
            <small>{hasZero ? "Movement from zero" : "Current sensor reading"}</small>
            <strong>
              {hasZero ? display(movement, info.precision) : value(current, info.precision)}
              <em>{info.unit}</em>
            </strong>
            <p>
              {hasZero
                ? `Zero was set at ${display(baseline, info.precision)} ${info.unit}. Noise allowance: ±${display(allowance, info.precision)} ${info.unit}.`
                : `${samples.length} valid recent reading${samples.length === 1 ? "" : "s"} available.`}
            </p>
          </div>
          <span className="zero-state">
            <Icon name={hasZero && isDanger ? "incidents" : hasZero ? "check" : "signal"} size={22} />
            {hasZero ? (isDanger ? "DANGER" : "SAFE") : "READY"}
          </span>
        </div>

        <div className="zero-instruction">
          <span>1</span><p><strong>Put the sensor in its normal position.</strong><br />Do not touch or move it while zeroing.</p>
          <span>2</span><p><strong>Press the button once.</strong><br />The current position becomes 0.</p>
          <span>3</span><p><strong>Watch the status.</strong><br />Movement away from 0 changes SAFE to DANGER.</p>
        </div>

        <button className="zero-button" type="button" onClick={setZero} disabled={saving || samples.length < 3}>
          <Icon name="calibrate" size={23} />
          {saving ? "Setting zero…" : paired ? "Set current position as zero" : "Pair operator and set zero"}
        </button>
        <p className="zero-footnote">Zeroing uses the median of the latest valid readings so one noisy sample cannot shift the baseline. Source readings are preserved.</p>
      </section>

      <aside className="zero-side">
        <section className={`zero-status-card ${hasZero ? (isDanger ? "is-danger" : "is-safe") : ""}`}>
          <p className="eyebrow">SELECTED SENSOR</p>
          <h2>{node?.name} · {info.label}</h2>
          <dl>
            <div><dt>Location</dt><dd>{node?.place}</dd></div>
            <div><dt>Current</dt><dd>{value(current, info.precision)} {info.unit}</dd></div>
            <div><dt>Zero set</dt><dd>{hasZero ? `${display(baseline, info.precision)} ${info.unit}` : "Not set"}</dd></div>
            <div><dt>Status</dt><dd>{hasZero ? (isDanger ? "DANGER" : "SAFE") : "Not calibrated"}</dd></div>
          </dl>
        </section>

        <section className="zero-history">
          <p className="eyebrow">ZERO HISTORY</p>
          <h2>Previous settings</h2>
          {selectedRecords.length === 0 ? (
            <p className="muted">No zero position has been saved for this sensor.</p>
          ) : (
            <ol>
              {selectedRecords.slice(0, 4).map((record) => (
                <li key={record.id}>
                  <div><strong>{record.status === "active" ? "Current zero" : "Previous zero"}</strong><time>{dateLabel(record.created_at)}</time></div>
                  <span>{display(Number(record.baseline_value), info.precision)} {record.unit || info.unit}</span>
                </li>
              ))}
            </ol>
          )}
        </section>
      </aside>
    </div>
  );
}
