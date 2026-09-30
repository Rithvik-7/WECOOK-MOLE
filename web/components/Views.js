"use client";
import { useState } from "react";
import Link from "next/link";
import { Icon } from "./icons";
import { Badge, Empty, Modal, SectionHead } from "./Primitives";
import { API, dateLabel } from "../lib/format";
import { talkToMole } from "../lib/moleChat";

export { Analytics } from "./AnalysisBoard";
export { Nodes } from "./NodesBoard";
export { Rover } from "./RoverBoard";

export function Incidents({ data, mutate, busy, notify, onInspect }) {
  const [filter, setFilter] = useState("active"),
    [action, setAction] = useState(null),
    [reason, setReason] = useState(""),
    [sheet, setSheet] = useState(
      "node_id,sample_time,channel,value,unit\nA,2019-01-01T00:00:00+00:00,tilt_deg,0.2,deg",
    ),
    [preview, setPreview] = useState(null);
  const all = data.incidents || [],
    items = all.filter((i) =>
      filter === "all" || filter === "closed"
        ? filter === "all" || i.status === "CLOSED"
        : i.status !== "CLOSED",
    ),
    bulletins = data.bulletins || [],
    reports = (data.sos || []).filter((row) => row.status === "QUEUED");
  const verbs = {
    acknowledge: "Acknowledge incident",
    review: "Record review",
    close: "Close & generate report",
  };
  return (
    <div className="response-desk">
      <div className="response-stats">
        <article>
          <p>Open incidents</p>
          <strong>{all.filter((i) => i.status !== "CLOSED").length}</strong>
        </article>
        <article className={bulletins.length ? "is-alert" : ""}>
          <p>Local SOS</p>
          <strong>{bulletins.length}</strong>
        </article>
        <article>
          <p>Waiting on the server</p>
          <strong>{reports.length}</strong>
        </article>
      </div>

      <section className={`response-sos ${bulletins.length ? "is-alert" : ""}`} aria-live="polite">
        <div className="field-card-head">
          <h2>SOS for miners and residents</h2>
          <span>{bulletins.length ? "Monitoring check" : "None active"}</span>
        </div>
        {bulletins.map((item) => (
          <article key={item.id}>
            <p>{item.place}</p>
            <h3>{item.message}</h3>
            <small>{dateLabel(item.created_at)} · Shown on the public page. Not sent by SMS.</small>
          </article>
        ))}
        {!bulletins.length && (
          <p>No movement or gas warning is active, so the check has not raised an SOS.</p>
        )}
      </section>

      <div className="incidents-toolbar">
        <div className="segmented">
          {[
            ["active", "Active"],
            ["closed", "Closed"],
            ["all", "All records"],
          ].map(([key, label]) => (
            <button
              key={key}
              onClick={() => setFilter(key)}
              aria-pressed={filter === key}
            >
              {label}
              <span>
                {
                  all.filter(
                    (i) =>
                      key === "all" ||
                      (key === "closed"
                        ? i.status === "CLOSED"
                        : i.status !== "CLOSED"),
                  ).length
                }
              </span>
            </button>
          ))}
        </div>
        <span className="small muted">
          Acknowledging a warning does not resolve it.
        </span>
      </div>
      <div className="incident-grid">
        {items.map((i) => (
          <article className="panel incident-card" key={i.id}>
            <div className="incident-top">
              <Badge condition={i.severity} />
              <span className="record-id">{i.id}</span>
            </div>
            <h2>{i.title}</h2>
            <p className="incident-copy">{i.explanation}</p>
            <div className="incident-metadata">
              <span>
                <Icon name="clock" size={15} />
                {dateLabel(i.opened_at)}
              </span>
              <span>{i.origin} evidence</span>
            </div>
            <div className="incident-progress">
              {[
                "OPEN",
                "ACKNOWLEDGED",
                "RECOVERED/PENDING REVIEW",
                "CLOSED",
              ].map((s, index) => (
                <span key={s} className={i.status === s ? "current" : ""}>
                  <i>{index + 1}</i>
                  {["Detected", "Acknowledged", "Reviewed", "Closed"][index]}
                </span>
              ))}
            </div>
            <div className="button-row">
              <button
                className="button light"
                onClick={() => onInspect(i.node_id)}
              >
                Inspect Node {i.node_id}
              </button>
              {i.status !== "CLOSED" && (
                <button
                  className="button primary"
                  disabled={busy}
                  onClick={() => {
                    setAction({
                      id: i.id,
                      type:
                        i.status === "OPEN"
                          ? "acknowledge"
                          : i.status === "ACKNOWLEDGED"
                            ? "review"
                            : "close",
                    });
                    setReason("");
                  }}
                >
                  {
                    verbs[
                      i.status === "OPEN"
                        ? "acknowledge"
                        : i.status === "ACKNOWLEDGED"
                          ? "review"
                          : "close"
                    ]
                  }
                  <Icon name="arrow" size={16} />
                </button>
              )}
              {i.report_id && (
                <a
                  className="button primary"
                  href={`${API}/api/reports/${i.report_id}.pdf`}
                  target="_blank"
                  rel="noreferrer"
                >
                  <Icon name="document" size={16} />
                  Incident PDF
                </a>
              )}
            </div>
          </article>
        ))}
      </div>
      {!items.length && (
        <Empty
          icon="document"
          title={
            filter === "closed"
              ? "No closed incidents yet."
              : "No incidents in this view."
          }
        >
          When a station stays in warning, its record appears here. Closed incidents keep their evidence and handoff report.
        </Empty>
      )}
      <details className="response-import">
        <summary>Import a readings sheet</summary>
        <form
          onSubmit={async (event) => {
            event.preventDefault();
            const response = await fetch(`${API}/api/imports/preview`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ filename: "sheet.csv", csv_text: sheet }),
            });
            const body = await response.json();
            if (!response.ok)
              notify(body.detail || "The sheet could not be previewed.", "error");
            else setPreview(body);
          }}
        >
          <label className="form-label">
            CSV
            <textarea
              rows={4}
              value={sheet}
              onChange={(event) => setSheet(event.target.value)}
            />
          </label>
          <button className="button">Preview mapping</button>
          {preview && (
            <p className="footnote">
              {preview.rows} mapped rows.{" "}
              {preview.issues?.length
                ? preview.issues.join(" ")
                : "No issues. The original file is kept."}
            </p>
          )}
          {preview && !preview.issues?.length && (
            <button
              className="button primary"
              type="button"
              disabled={busy}
              onClick={async () => {
                const result = await mutate(
                  `/api/imports/${preview.id}/commit`,
                  {},
                );
                if (result)
                  notify(
                    `${result.stored} imported rows stored. Origin is imported.`,
                  );
              }}
            >
              Commit import
            </button>
          )}
        </form>
      </details>
      {action && (
        <Modal title={verbs[action.type]} onClose={() => setAction(null)}>
          <p className="muted">
            {action.type === "review"
              ? "Record the review outcome. This is an administrative review step; it does not establish physical recovery."
              : action.type === "close"
                ? "Record the closure reason, actions taken and any unresolved follow-up. The evidence snapshot will be preserved."
                : "Record what you have reviewed. The warning and its evidence remain available."}
          </p>
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              const result = await mutate(
                `/api/incidents/${action.id}/${action.type}`,
                { reason },
              );
              if (result) {
                setAction(null);
                notify(
                  result.report_id
                    ? "Incident closed. Your handoff report is ready."
                    : "Incident record updated.",
                  "info",
                  result.report_id
                    ? `${API}/api/reports/${result.report_id}.pdf`
                    : null,
                );
              }
            }}
          >
            <label className="form-label">
              Your note
              <textarea
                required
                minLength={3}
                rows={4}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Describe the review or action you actually performed…"
              />
            </label>
            <button
              className="button primary"
              disabled={busy || reason.trim().length < 3}
            >
              {busy ? "Saving…" : verbs[action.type]}
            </button>
          </form>
        </Modal>
      )}
    </div>
  );
}

export function Assistant({ data }) {
  const [question, setQuestion] = useState(""),
    [answer, setAnswer] = useState(null),
    [loading, setLoading] = useState(false),
    [error, setError] = useState("");
  async function ask(q) {
    setQuestion(q);
    setLoading(true);
    setError("");
    setAnswer({ answer: "", sources: [], provider: "Mole" });
    try {
      const result = await talkToMole({
        question: q,
        history: [],
        onToken: (_token, full) => {
          setAnswer((current) => ({ ...(current || {}), answer: full }));
        },
      });
      setAnswer(result);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }
  return (
    <div className="assistant-layout">
      <article className="panel assistant-main">
        <span className="assistant-emblem">
          <Icon name="assistant" size={30} />
        </span>
        <p className="eyebrow">CONNECTED TO YOUR RECORDS</p>
        <h2>
          A little clarity
          <br />
          goes a long way.
        </h2>
        <p className="muted">
          Mole sits in the corner of every page. This desk is the same
          companion, reading the live records through a language model — not a
          list of prepared replies.
        </p>
        <form
          className="assistant-input"
          onSubmit={(e) => {
            e.preventDefault();
            ask(question);
          }}
        >
          <label htmlFor="question" className="sr-only">
            Ask about site evidence
          </label>
          <textarea
            id="question"
            rows={2}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask Mole about this mine…"
            required
          />
          <button
            className="button primary"
            disabled={loading || !question.trim()}
          >
            {loading ? "Listening…" : "Ask Mole"}
          </button>
        </form>
        {error && (
          <p role="alert" className="error-text">
            {error}
          </p>
        )}
        {loading && (
          <p role="status" className="small muted">
            Reading the stored evidence…
          </p>
        )}
        {answer && (
          <div className="assistant-answer">
            <span className="eyebrow">MOLE</span>
            <p>{answer.answer}</p>
            <div className="source-links">
              {answer.sources?.map((s) => (
                <Link key={s} href={`/incidents?focus=${s}`}>
                  <Icon name="document" size={14} />
                  {s}
                </Link>
              ))}
            </div>
            <small>
              {answer.model
                ? `Mole · ${answer.provider} · ${answer.model}`
                : "Mole is writing…"}
            </small>
          </div>
        )}
      </article>
      <aside className="assistant-sidebar">
        <article className="panel">
          <p className="eyebrow">THIS WORKSPACE</p>
          <h3>Context, always attached.</h3>
          <dl className="definition-list">
            <div>
              <dt>Monitoring points</dt>
              <dd>{data.nodes.length}</dd>
            </div>
            <div>
              <dt>Incident records</dt>
              <dd>{data.incidents.length}</dd>
            </div>
            <div>
              <dt>Weather feed</dt>
              <dd>Not connected</dd>
            </div>
            <div>
              <dt>Response mode</dt>
              <dd>Mole · Groq free API</dd>
            </div>
          </dl>
          <p className="footnote">
            Mole reads the live site brief and a project briefing. It does not
            use a list of prepared answers.
          </p>
        </article>
        <div className="assistant-boundary">
          <Icon name="shield" size={24} />
          <h3>Helpful. Within its role.</h3>
          <p>
            Mole explains what is recorded. It cannot change thresholds, close
            incidents or move the rover.
          </p>
        </div>
      </aside>
    </div>
  );
}
