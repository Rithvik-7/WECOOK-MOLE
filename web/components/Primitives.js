"use client";
import { useEffect, useRef, useState } from "react";
import { Icon } from "./icons";
import { channels, labels, value, dateLabel } from "../lib/format";
import { Trend } from "./Trend";
import { SignalChart } from "./SignalChart";

export function Badge({ condition, children }) {
  return (
    <span className={`badge ${condition || "neutral"}`}>
      <i />
      {children || labels[condition] || condition}
    </span>
  );
}
export function SectionHead({ eyebrow, title, children }) {
  return (
    <div className="section-head">
      <div>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h2>{title}</h2>
      </div>
      {children}
    </div>
  );
}
export function Empty({ icon = "info", title, children }) {
  return (
    <div className="empty-state">
      <span className="empty-icon">
        <Icon name={icon} size={28} />
      </span>
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  );
}
export function Modal({ title, onClose, children, wide = false }) {
  const ref = useRef(null);
  const [actionError, setActionError] = useState("");
  useEffect(() => {
    const handler = (e) => setActionError(e.detail);
    window.addEventListener("mole-action-error", handler);
    return () => window.removeEventListener("mole-action-error", handler);
  }, []);
  useEffect(() => {
    const el = ref.current;
    const previous = document.activeElement;
    el.showModal();
    const old = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = old;
      previous?.focus?.();
    };
  }, []);
  return (
    <dialog
      ref={ref}
      className={`modal ${wide ? "wide" : ""}`}
      aria-label={title}
      onCancel={onClose}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="modal-inner">
        <div className="modal-head">
          <h2>{title}</h2>
          <button
            className="icon-btn"
            aria-label="Close dialog"
            onClick={onClose}
          >
            <Icon name="close" />
          </button>
        </div>
        {actionError && (
          <p role="alert" className="error-text">
            {actionError}
          </p>
        )}
        {children}
      </div>
    </dialog>
  );
}
export function NodeDetail({ node, onClose }) {
  const [forecastModel, setForecastModel] = useState(null);
  useEffect(() => {
    fetch("/models/short-horizon.json")
      .then((r) => (r.ok ? r.json() : null))
      .then(setForecastModel)
      .catch(() => {});
  }, []);
  const a = node.analysis;
  return (
    <Modal title={`${node.name} / field record`} onClose={onClose} wide>
      <div className="detail-intro">
        <Badge condition={node.condition} />
        <span className="muted">{node.place}</span>
      </div>
      <p className="small muted">
        {node.latest?.origin || "Unavailable"} observation ·{" "}
        {dateLabel(node.latest?.sample_time)}
      </p>
      <div className="detail-measures">
        {node.capabilities.map((key) => {
          const c = channels[key] || { label: "IR sensor", unit: "" };
          return (
            <div key={key}>
              <span>{c.label}</span>
              <strong>
                {value(node.latest?.[key], c.precision ?? 1)}{" "}
                <small>{node.latest?.[key] != null ? c.unit : ""}</small>
              </strong>
              {key === "ir" && <small>Module and purpose unconfirmed</small>}
              {key === "potentiometer_raw" && (
                <small>Millimetres need calibration</small>
              )}
            </div>
          );
        })}
      </div>
      <div className="signals-grid detail-signals">
        {node.capabilities.map((channel) => (
          <SignalChart
            key={channel}
            node={node}
            channel={channel}
            model={forecastModel}
          />
        ))}
      </div>
      <h3>Why this reading</h3>
      <p className="small">
        {node.condition === "normal"
          ? "No configured warning is active. The notes below are the rule evidence for this window."
          : "Evidence-based prototype explanation. Not a certified safety decision."}
      </p>
      <ul className="evidence-list">
        {(a?.evidence || ["No analysis available."]).map((e, i) => (
          <li key={i}>{e}</li>
        ))}
      </ul>
      <details className="technical">
        <summary>Device, provenance & raw reading</summary>
        <pre>
          {JSON.stringify(
            {
              capabilities: node.capabilities,
              quality: a?.quality,
              latest: node.latest,
            },
            null,
            2,
          )}
        </pre>
      </details>
    </Modal>
  );
}
