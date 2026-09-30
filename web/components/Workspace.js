"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import Link from "next/link";
import { Brand } from "./Brand";

import { saveSnapshot, readSnapshot } from "../lib/offline.mjs";

import { usePathname } from "next/navigation";

import { Icon } from "./icons";

import { MineOverview as Overview, PLACEMENTS } from "./MineOverview";

import { Modal, NodeDetail } from "./Primitives";

import { Analytics, Incidents, Rover, Assistant, Nodes } from "./Views";
import { GisMap } from "./GisMap";
import { CalibrationBoard } from "./CalibrationBoard";

import { API, request, dateLabel } from "../lib/format";
import { latestStamp } from "../lib/intel";

function HeaderClock() {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);
  const label = now.toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
  return (
    <time className="header-clock" dateTime={now.toISOString()}>
      {label}
    </time>
  );
}

const NAV = [
  ["/", "overview", "Overview"],

  ["/nodes", "nodes", "Sensor network"],

  ["/analytics", "analytics", "Intelligence"],

  ["/incidents", "incidents", "Incident log"],

  ["/rover", "rover", "Rover station"],
];

const TITLES = {
  overview: [
    "SURFACE INTELLIGENCE",

    "A deeper perspective.",

    "Every movement. Every observation. One connected field.",
  ],

  nodes: [
    "SENSOR NETWORK",

    "Four stations. Every channel.",

    "Readings, laboratory watch limits, graphs and downloads for each installed instrument. Limits are prototype settings, not certified safe values.",
  ],

  gis: [
    "PLAN OF GROUND",

    "Where each station sits.",

    "A schematic GIS plan. Positions are the demonstration layout, not a GPS survey, and the colours follow the live station state.",
  ],

  analytics: [
    "SIGNAL OVERLAY",

    "Two stations. One clock.",

    "The same channel, ranked across the four stations, with the laboratory tilt bands drawn on the overlay. Coverage is not a probability of safety.",
  ],

  incidents: [
    "RESPONSE DESK",

    "Alerts, SOS, and the record.",

    "A monitoring warning raises a local SOS. Miners and residents can send one too. Each incident keeps its evidence and handoff.",
  ],

  rover: [
    "ROVER R1",

    "Command the inspection unit.",

    "Drive pad, camera bay and payload on this console. Motion and live video wait for a confirmed controller. This page does not show a picture of the rover.",
  ],

  assistant: [
    "MOLE FIELD NOTES",

    "Ask your evidence.",

    "Clear answers from recorded observations and incident history.",
  ],
  calibration: [
    "SENSOR ZEROING",
    "Set zero. Detect movement.",
    "Choose a sensor, keep it still and set its current position as zero. Movement away from zero is shown as danger.",
  ],
};

export function Workspace({ view }) {
  const pathname = usePathname();

  const [data, setData] = useState(null),
    [error, setError] = useState(""),
    [connection, setConnection] = useState("connecting");

  const [selected, setSelected] = useState("B"),
    [detail, setDetail] = useState(null),
    [pair, setPair] = useState(false),
    [paired, setPaired] = useState(false),
    [token, setToken] = useState(""),
    [pairError, setPairError] = useState("");

  const [notice, setNotice] = useState(null),
    [paused, setPaused] = useState(false),
    [busy, setBusy] = useState(false);

  const pauseRef = useRef(false),
    pending = useRef(null);

  const notify = useCallback(
    (message, type = "info", href = null) => setNotice({ message, type, href }),

    [],
  );

  const load = useCallback(async () => {
    try {
      const snapshot = await request("/api/state");

      setData(snapshot);

      try {
        saveSnapshot(localStorage, snapshot);
      } catch {}

      setError("");

      setConnection("connected");
    } catch (e) {
      setError(e.message);

      setConnection("offline");

      const cached = readSnapshot(localStorage);

      if (cached) setData({ ...cached.data, cachedAt: cached.savedAt });
    }
  }, []);

  useEffect(() => {
    setPaired(Boolean(sessionStorage.getItem("mole-capability")));

    load();

    const source = new EventSource(`${API}/api/events`);

    source.onmessage = (e) => {
      try {
        const next = JSON.parse(e.data);

        try {
          saveSnapshot(localStorage, next);
        } catch {}

        if (pauseRef.current) pending.current = next;
        else setData(next);

        setError("");

        setConnection("connected");
      } catch {
        setConnection("reconnecting");
      }
    };

    source.onerror = () => setConnection("reconnecting");

    const timer = setInterval(() => {
      if (!pauseRef.current) load();
    }, 1000);

    return () => {
      clearInterval(timer);
      source.close();
    };
  }, [load]);

  useEffect(() => {
    if (!notice || notice.type === "error" || notice.href) return;

    const timer = setTimeout(() => setNotice(null), 6500);

    return () => clearTimeout(timer);
  }, [notice]);

  function togglePause() {
    pauseRef.current = !pauseRef.current;

    setPaused(pauseRef.current);

    if (!pauseRef.current && pending.current) {
      setData(pending.current);

      pending.current = null;
    }
  }

  async function mutate(path, body) {
    setBusy(true);

    try {
      const result = await request(path, body);

      await load();

      return result;
    } catch (e) {
      notify(e.message, "error");

      window.dispatchEvent(
        new CustomEvent("mole-action-error", { detail: e.message }),
      );

      return null;
    } finally {
      setBusy(false);
    }
  }

  const nodes = data?.nodes || [],
    active = (data?.incidents || []).filter((i) => i.status !== "CLOSED"),
    node = nodes.find((n) => n.id === selected) || nodes[0],
    latestSample = nodes
      .map((n) => n.latest?.sample_time)
      .filter(Boolean)
      .sort()
      .at(-1);

  const title = TITLES[view];

  const origins = new Set(nodes.map((n) => n.latest?.origin).filter(Boolean));

  const originLabel =
    origins.size > 1
      ? "MIXED SOURCES"
      : origins.has("physical")
        ? "PHYSICAL DATA"
        : origins.has("imported")
          ? "IMPORTED DATA"
          : "DEMO DATA";

  const alertItem = active[0];
  const activityCopy = alertItem
    ? {
        kicker: active.length === 1 ? "1 open" : `${active.length} open`,
        detail: alertItem.title || "Incident open",
      }
    : { kicker: "Clear", detail: "All stations steady" };
  const linkLabel =
    connection === "connected"
      ? "Live"
      : connection === "offline"
        ? "Offline"
        : connection === "reconnecting"
          ? "Reconnecting"
          : "Connecting";

  return (
    <div className={`app-shell ${view === "overview" ? "overview-shell" : ""}`}>
      <a className="skip-link" href="#workspace">
        Skip to workspace
      </a>

      <div className="workspace-shell">
        <header className="mole-header">
          <div className="header-brand">
            <Brand />
            <p className="header-site">{data?.site?.name || "Field panel"}</p>
          </div>
          <nav className="primary-nav" aria-label="Primary navigation">
            {[
              ["/", "Monitor"],
              ["/nodes", "Nodes"],
              ["/map", "Map"],
              ["/analytics", "Analysis"],
              ["/rover", "Rover"],
            ].map(([href, label]) => (
              <Link
                key={href}
                href={href}
                aria-current={pathname === href ? "page" : undefined}
              >
                {label}
              </Link>
            ))}
          </nav>
          <div className="header-tools">
            <div className={`header-status ${alertItem ? "is-alert" : "is-clear"}`}>
              <p className="link-led" data-state={connection} aria-live="polite">
                <i />
                <span>{linkLabel}</span>
              </p>
              <Link
                href="/incidents"
                className={`activity-brief ${alertItem ? "is-alert" : "is-clear"}`}
                aria-label={`${activityCopy.kicker}. ${activityCopy.detail}`}
              >
                <span className="activity-kicker">{activityCopy.kicker}</span>
                <strong>{activityCopy.detail}</strong>
              </Link>
            </div>
            <HeaderClock />
            <details className="header-menu">
              <summary aria-label="Console menu">
                <Icon name="settings" size={18} />
              </summary>
              <div>
                <p className="header-panel-kicker">Console</p>
                <p className="header-panel-status">
                  Link {linkLabel.toLowerCase()}
                  {data?.site?.name ? ` · ${data.site.name}` : ""}
                </p>
                {active.length > 0 && (
                  <ul className="header-notes">
                    {active.slice(0, 3).map((item) => (
                      <li key={item.id}>
                        <Link href="/incidents">{item.title}</Link>
                      </li>
                    ))}
                  </ul>
                )}
                <Link href="/assistant">Evidence assistant</Link>
                <Link href="/calibration">Sensor calibration</Link>
                <button onClick={() => setPair(true)}>
                  {paired ? "Operator paired" : "Pair operator"}
                </button>
              </div>
            </details>
          </div>
        </header>

        <main id="workspace" className="workspace">
          {view !== "overview" && (
            <div className="page-heading">
              <div>
                <p className="eyebrow">{title[0]}</p>

                <h1>{title[1]}</h1>

                <p>{title[2]}</p>
              </div>

              <div className="heading-actions">
                {latestSample && (
                  <span className="sample-time">
                    <Icon name="clock" size={15} />
                    <span>
                      Last sample <strong>{dateLabel(latestSample)}</strong>
                    </span>
                  </span>
                )}

                <span className="demo-tag">{originLabel}</span>

                <a
                  className="button light"
                  href={`${API}/api/exports/telemetry.xlsx`}
                >
                  <Icon name="download" size={17} />
                  Export Excel
                </a>

                <a
                  className="button light"
                  href={`${API}/api/exports/telemetry.csv`}
                >
                  Export CSV
                </a>
              </div>
            </div>
          )}
          {data && view !== "overview" && (
            <div className="context-line">
              <span>
                <Icon name="location" size={14} />
                {data.site.name} <b>·</b> Illustrative geometry{" "}
                <em className="origin-label">{originLabel.toLowerCase()}</em>
              </span>
            </div>
          )}

          {!data && (
            <div className="connection-empty">
              <Icon name={error ? "signal" : "layers"} size={34} />

              <h2>
                {error
                  ? "The monitoring service is unreachable."
                  : "Opening your field workspace…"}
              </h2>

              <p>
                {error
                  ? "Start the local API, then reconnect. No readings are substituted."
                  : "Loading the site, measurements and incident records."}
              </p>

              {error && (
                <button className="button primary" onClick={load}>
                  <Icon name="refresh" />
                  Reconnect
                </button>
              )}
            </div>
          )}

          {data && (
            <>
              {connection !== "connected" && (
                <div className="inline-warning">
                  <Icon name="signal" />
                  Connection interrupted. Historical snapshot only.{" "}
                  {data.cachedAt
                    ? `Saved ${dateLabel(data.cachedAt)}.`
                    : "Live status is unavailable."}
                  <button className="text-button" onClick={load}>
                    Retry
                  </button>
                </div>
              )}

              {paused && (
                <div className="inline-warning">
                  <Icon name="pause" />
                  Display paused. Background sensing and alerts continue.
                  <button className="text-button" onClick={togglePause}>
                    Resume display
                  </button>
                </div>
              )}

              {view === "overview" && (
                <Overview
                  data={data}
                  selected={node?.id}
                  onSelect={setSelected}
                  onInspect={setDetail}
                  paused={paused}
                  onPause={togglePause}
                  connection={connection}
                />
              )}

              {view === "nodes" && <Nodes data={data} onInspect={setDetail} />}

              {view === "gis" && (
                <GisMap data={data} selected={selected} onSelect={setSelected} />
              )}

              {view === "analytics" && <Analytics data={data} />}

              {view === "incidents" && (
                <Incidents
                  data={data}
                  mutate={mutate}
                  busy={busy}
                  notify={notify}
                  onInspect={setDetail}
                />
              )}

              {view === "rover" && (
                <Rover
                  data={data}
                  mutate={mutate}
                  busy={busy}
                  notify={notify}
                  paired={paired}
                />
              )}

              {view === "assistant" && <Assistant data={data} />}

              {view === "calibration" && (
                <CalibrationBoard
                  data={data}
                  paired={paired}
                  onPair={() => setPair(true)}
                  notify={notify}
                  onStateRefresh={load}
                />
              )}
            </>
          )}

          <footer className="workspace-footer">
            <span>
              MOLE <b>/</b> Closer to the ground.
            </span>

            <span>
              MOLE / Field intelligence
              {data?.persistence?.jobs_failed
                ? ` · ${data.persistence.jobs_failed} failed jobs`
                : ""}
            </span>
          </footer>
        </main>
      </div>

      <nav className="mobile-nav" aria-label="Mobile navigation">
        {NAV.map(([href, key, label]) => (
          <Link
            key={key}
            href={href}
            aria-current={pathname === href ? "page" : undefined}
          >
            <Icon name={key} size={20} />

            <span>
              {key === "analytics"
                ? "Insights"
                : key === "incidents"
                  ? "Incidents"
                  : key === "nodes"
                    ? "Nodes"
                    : key === "rover"
                      ? "Rover"
                      : "Overview"}
            </span>
          </Link>
        ))}
      </nav>

      {detail && nodes.find((n) => n.id === detail) && (
        <NodeDetail
          node={{
            ...nodes.find((n) => n.id === detail),
            place: PLACEMENTS[detail],
          }}
          onClose={() => setDetail(null)}
        />
      )}

      {pair && (
        <Modal title="Operator device" onClose={() => setPair(false)}>
          <p className="muted">
            Monitoring is open to everyone. Pair this browser session to
            acknowledge incidents and plan inspections.
          </p>

          <form
            onSubmit={async (e) => {
              e.preventDefault();

              setBusy(true);

              try {
                const response = await fetch(`${API}/api/operator/check`, {
                  headers: { "X-Mole-Capability": token.trim() },
                });

                if (!response.ok)
                  throw new Error(
                    "This credential was not accepted by the service.",
                  );

                sessionStorage.setItem("mole-capability", token.trim());

                setToken("");

                setPaired(true);

                setPair(false);

                notify("Operator session paired.");
              } catch (e) {
                setPairError(e.message);
              } finally {
                setBusy(false);
              }
            }}
          >
            {pairError && (
              <p className="error-text" role="alert">
                {pairError}
              </p>
            )}

            <label className="form-label">
              Operator credential
              <input
                type="password"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                autoComplete="off"
                required
                placeholder="Enter the configured device credential"
              />
            </label>

            <div className="button-row">
              <button
                className="button primary"
                disabled={busy || !token.trim()}
              >
                Pair this session
                <Icon name="arrow" size={16} />
              </button>

              {paired && (
                <button
                  type="button"
                  className="button"
                  onClick={() => {
                    sessionStorage.removeItem("mole-capability");

                    setPaired(false);

                    setPair(false);

                    notify("Operator session removed.");
                  }}
                >
                  Unpair
                </button>
              )}
            </div>
          </form>
        </Modal>
      )}

      {notice && (
        <div
          className={`toast ${notice.type}`}
          role={notice.type === "error" ? "alert" : "status"}
        >
          <Icon name={notice.type === "error" ? "info" : "check"} />

          <div>
            {notice.message}

            {notice.href && (
              <a href={notice.href} target="_blank" rel="noreferrer">
                Open incident PDF <Icon name="northeast" size={14} />
              </a>
            )}
          </div>

          <button
            className="icon-btn"
            aria-label="Dismiss notification"
            onClick={() => setNotice(null)}
          >
            <Icon name="close" size={17} />
          </button>
        </div>
      )}
    </div>
  );
}
