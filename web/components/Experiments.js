"use client";
import { useEffect, useState } from "react";
import { API, request, dateLabel } from "../lib/format";
import { SectionHead, Modal, Empty } from "./Primitives";
import { Icon } from "./icons";

export function Experiments() {
  const [archive, setArchive] = useState(null),
    [error, setError] = useState("");
  const [selected, setSelected] = useState(null),
    [label, setLabel] = useState("unreviewed"),
    [note, setNote] = useState(""),
    [busy, setBusy] = useState(false);
  async function load() {
    try {
      setArchive(await request("/api/experiments"));
      setError("");
    } catch (e) {
      setError(e.message);
    }
  }
  useEffect(() => {
    load();
  }, []);
  return (
    <article className="panel experiment-panel">
      <SectionHead
        eyebrow="EXPERIMENT ARCHIVE"
        title="From observations to a dataset."
      >
        <button className="button light" onClick={load}>
          <Icon name="refresh" size={16} />
          Refresh archive
        </button>
      </SectionHead>
      <p className="muted">
        Keep each recording session separate. Review its context before it
        becomes a training example.
      </p>
      {error && (
        <p className="error-text" role="alert">
          {error}
        </p>
      )}
      {!archive && !error && <p role="status">Loading experiment records…</p>}
      {archive && (
        <>
          <div className="feature-grid">
            <div>
              <span>Recorded sessions</span>
              <strong>{archive.sessions.length}</strong>
            </div>
            <div>
              <span>Physical sessions</span>
              <strong>{archive.readiness.physical_sessions}</strong>
            </div>
            <div>
              <span>Reviewed physical sessions</span>
              <strong>{archive.readiness.reviewed_physical_sessions}</strong>
            </div>
          </div>
          <div className="experiment-list">
            {archive.sessions.map((s) => (
              <div
                className="experiment-row"
                key={`${s.node_id}-${s.session_id}`}
              >
                <div>
                  <strong>
                    Node {s.node_id}{" "}
                    <span className="muted">/ {s.session_id}</span>
                  </strong>
                  <p>
                    {s.sample_count} readings · {s.origin} · {s.sequence_gaps}{" "}
                    sequence gaps
                  </p>
                  <small>
                    {dateLabel(s.started_at)} · {s.label.replaceAll("_", " ")}
                  </small>
                </div>
                <div className="button-row">
                  <a
                    className="button light"
                    href={`${API}/api/experiments/${encodeURIComponent(s.node_id)}/${encodeURIComponent(s.session_id)}/export`}
                    target="_blank"
                    rel="noreferrer"
                  >
                    <Icon name="download" size={15} />
                    JSON
                  </a>
                  <button
                    className="button"
                    onClick={() => {
                      setSelected(s);
                      setLabel(s.label);
                      setNote(s.note);
                      setError("");
                    }}
                  >
                    Review session
                  </button>
                </div>
              </div>
            ))}
          </div>
          {!archive.sessions.length && (
            <Empty title="No recorded sessions yet.">
              Connect the receiver to begin an experiment.
            </Empty>
          )}
          <p className="footnote">{archive.readiness.next_step}</p>
        </>
      )}
      {selected && (
        <Modal
          title={`Review Node ${selected.node_id} / ${selected.session_id}`}
          onClose={() => {
            setSelected(null);
            setError("");
          }}
        >
          <p className="muted">
            This labels an entire recording session. Mixed events should be
            collected as separate experiments. Requires a paired operator.
          </p>
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              setBusy(true);
              setError("");
              try {
                await request(
                  `/api/experiments/${encodeURIComponent(selected.node_id)}/${encodeURIComponent(selected.session_id)}/review`,
                  { label, note },
                );
                setSelected(null);
                await load();
              } catch (e) {
                setError(e.message);
              } finally {
                setBusy(false);
              }
            }}
          >
            {error && (
              <p role="alert" className="error-text">
                {error}
              </p>
            )}
            <label className="form-label">
              Observed class
              <select value={label} onChange={(e) => setLabel(e.target.value)}>
                {[
                  "unreviewed",
                  "baseline",
                  "movement",
                  "disturbance",
                  "sensor_fault",
                ].map((x) => (
                  <option key={x} value={x}>
                    {x.replaceAll("_", " ")}
                  </option>
                ))}
              </select>
            </label>
            <label className="form-label">
              Experiment context
              <textarea
                required
                minLength={3}
                maxLength={2000}
                rows={4}
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Describe the setup, known stimulus and independent observations."
              />
            </label>
            <button
              className="button primary"
              disabled={busy || note.trim().length < 3}
            >
              {busy ? "Saving…" : "Save annotation"}
            </button>
          </form>
        </Modal>
      )}
    </article>
  );
}
