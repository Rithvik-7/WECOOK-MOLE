"use client";
import { useMemo, useState } from "react";
import Link from "next/link";
import { Badge, Empty, Modal, SectionHead } from "./Primitives";
import { Icon } from "./icons";
import { dateLabel, timeLabel } from "../lib/format";
import { NAMES } from "./MineOverview";

const KIT = [
  {
    id: "camera",
    name: "Camera",
    role: "Close visual of the inspection face.",
    status: "Not equipped",
    live: false,
  },
  {
    id: "drive",
    name: "Drive",
    role: "Operator motion under this pad.",
    status: "Not enabled",
    live: false,
  },
  {
    id: "fix",
    name: "Localization",
    role: "Last known position of the unit.",
    status: "Unavailable",
    live: false,
  },
  {
    id: "radio",
    name: "Command radio",
    role: "Uplink from this console to R1.",
    status: "No controller confirmed",
    live: false,
  },
  {
    id: "lights",
    name: "Work lights",
    role: "Illumination at the inspection face.",
    status: "Not equipped",
    live: false,
  },
  {
    id: "log",
    name: "Mission log",
    role: "Notes linked to an incident. Distinct from Node C.",
    status: "Available on this console",
    live: true,
  },
];

const DRIVE = [
  { kind: "forward", label: "Forward", row: "fwd" },
  { kind: "left", label: "Left", row: "left" },
  { kind: "halt", label: "Halt", row: "halt" },
  { kind: "right", label: "Right", row: "right" },
  { kind: "back", label: "Back", row: "back" },
];

function parseEvidence(raw) {
  try {
    const items = JSON.parse(raw || "[]");
    return Array.isArray(items) ? items : [];
  } catch {
    return [];
  }
}

function commandExpiry() {
  return new Date(Date.now() + 5 * 60 * 1000).toISOString();
}

export function Rover({ data, mutate, busy, notify, paired }) {
  const openIncidents = (data.incidents || []).filter(
    (i) => i.status !== "CLOSED",
  );
  const missions = data.missions || [];
  const [incident, setIncident] = useState(openIncidents[0]?.id || "");
  const [note, setNote] = useState("");
  const [missionId, setMissionId] = useState(missions[0]?.id || "");
  const [evidence, setEvidence] = useState(null);
  const [finding, setFinding] = useState("");
  const [log, setLog] = useState([]);
  const mission =
    missions.find((m) => m.id === missionId) || missions[0] || null;
  const armed = Boolean(paired && mission);
  const reason = !paired
    ? "Pair an operator session to arm the pad."
    : !mission
      ? "Plan a mission first. Commands need a linked incident."
      : "Drive is armed. The controller will refuse motion until R1 is confirmed.";

  const kit = useMemo(
    () =>
      KIT.map((item) =>
        item.id === "log"
          ? {
              ...item,
              status: missions.length
                ? `${missions.length} mission${missions.length === 1 ? "" : "s"} on this console`
                : "Available on this console",
            }
          : item,
      ),
    [missions.length],
  );

  function pushLog(kind, detail) {
    setLog((rows) =>
      [
        {
          t: new Date().toISOString(),
          kind,
          detail,
        },
        ...rows,
      ].slice(0, 8),
    );
  }

  async function sendCommand(kind) {
    if (!armed) {
      notify(reason, "error");
      pushLog(kind, reason);
      return;
    }
    const result = await mutate("/api/commands", {
      mission_id: mission.id,
      kind,
      expires_at: commandExpiry(),
    });
    pushLog(
      kind,
      result
        ? result.note || "Command stored. No motion was issued."
        : "Not executed.",
    );
  }

  async function recordLostLink() {
    if (!armed) {
      notify(reason, "error");
      return;
    }
    const result = await mutate(`/api/missions/${mission.id}/link-lost`);
    if (result) {
      notify(result.note || "Lost link recorded. No vehicle stop was sent.");
      pushLog("link-lost", result.note);
    }
  }

  async function recordPositionUnknown() {
    if (!armed) {
      notify(reason, "error");
      return;
    }
    const result = await mutate(`/api/missions/${mission.id}/position`, {
      known: false,
      note: "Last contact unavailable",
    });
    if (result) {
      notify("Position recorded as unknown. Localization is not confirmed.");
      pushLog("position", "Last contact unavailable.");
    }
  }

  return (
    <div className="rover-desk">
      <section className="rover-status" aria-label="R1 link status">
        <div>
          <p className="station-kicker">Unit</p>
          <strong>R1</strong>
          <small>Inspection unit · distinct from Node C</small>
        </div>
        <div>
          <p className="station-kicker">Radio</p>
          <strong>{paired ? "Operator paired" : "Not paired"}</strong>
          <small>
            {paired
              ? "Console may send a command. The vehicle link is still unconfirmed."
              : "Pair from the header before a command."}
          </small>
        </div>
        <div>
          <p className="station-kicker">Camera</p>
          <strong>Not equipped</strong>
          <small>No live feed on this console.</small>
        </div>
        <div>
          <p className="station-kicker">Drive</p>
          <strong>Not enabled</strong>
          <small>Simulation cannot issue motion.</small>
        </div>
        <div>
          <p className="station-kicker">Position</p>
          <strong>
            {mission?.position?.known ? "Known" : "Unavailable"}
          </strong>
          <small>
            {mission?.position?.note || "Last contact unavailable."}
          </small>
        </div>
      </section>

      <div className="rover-stage">
        <article className="camera-bay">
          <header className="camera-chrome">
            <span>R1 · camera bay</span>
            <Badge condition="unavailable">No live feed</Badge>
          </header>
          <div
            className="camera-stage"
            role="img"
            aria-label="Camera bay. No live feed. The camera is not equipped. This is not a picture of the rover."
          >
            <p className="camera-kicker">Signal</p>
            <h2>No live feed.</h2>
            <p>
              The camera is not equipped. This panel is the empty bay, not a
              drawing of the unit and not a simulated video.
            </p>
            <dl>
              <div>
                <dt>Frame</dt>
                <dd>—</dd>
              </div>
              <div>
                <dt>Latency</dt>
                <dd>—</dd>
              </div>
              <div>
                <dt>Last contact</dt>
                <dd>—</dd>
              </div>
            </dl>
          </div>
        </article>

        <aside className="rover-controls">
          <p className="station-kicker">Drive pad</p>
          <h3>Command R1.</h3>
          <p className="brief-lead">{reason}</p>
          <label className="form-label">
            Active mission
            <select
              value={mission?.id || ""}
              onChange={(e) => setMissionId(e.target.value)}
            >
              {!missions.length && <option value="">No mission yet</option>}
              {missions.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.id} · {m.state}
                </option>
              ))}
            </select>
          </label>
          <div
            className="drive-pad"
            role="group"
            aria-label="Drive pad. Arrow keys work when this pad is focused."
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.target !== e.currentTarget) return;
              const map = {
                ArrowUp: "forward",
                ArrowDown: "back",
                ArrowLeft: "left",
                ArrowRight: "right",
                w: "forward",
                W: "forward",
                s: "back",
                S: "back",
                a: "left",
                A: "left",
                d: "right",
                D: "right",
                " ": "halt",
                Escape: "halt",
              };
              const kind = map[e.key];
              if (!kind) return;
              e.preventDefault();
              sendCommand(kind);
            }}
          >
            {DRIVE.map((item) => (
              <button
                key={item.kind}
                type="button"
                className={`pad-btn is-${item.row} ${item.kind === "halt" ? "is-halt" : ""}`}
                disabled={busy}
                onClick={() => sendCommand(item.kind)}
              >
                {item.label}
              </button>
            ))}
          </div>
          <p className="footnote">
            Focus the pad, then use arrow keys or W A S D. Space or Escape is
            Halt. A refused command is recorded. The vehicle does not move.
          </p>
          <div className="payload-actions">
            <button
              type="button"
              className="button light"
              disabled={busy}
              onClick={() => sendCommand("lights")}
            >
              Lights
            </button>
            <button
              type="button"
              className="button light"
              disabled={busy}
              onClick={() => sendCommand("camera-tilt")}
            >
              Camera tilt
            </button>
            <button
              type="button"
              className="button light"
              disabled={busy}
              onClick={recordLostLink}
            >
              Record lost link
            </button>
            <button
              type="button"
              className="button light"
              disabled={busy}
              onClick={recordPositionUnknown}
            >
              Position unknown
            </button>
          </div>
          <ol className="command-log" aria-live="polite">
            {!log.length && (
              <li>
                <span>—</span>
                <p>No command attempted this session.</p>
              </li>
            )}
            {log.map((row, i) => (
              <li key={`${row.t}-${i}`}>
                <span>{timeLabel(row.t)}</span>
                <p>
                  <b>{row.kind}</b> · {row.detail}
                </p>
              </li>
            ))}
          </ol>
        </aside>
      </div>

      <section className="rover-kit" aria-label="What is on R1">
        <header>
          <p className="station-kicker">Payload</p>
          <h2>What is on this unit.</h2>
          <p>
            R1 is a separate inspection unit. It is not Node C. Only the mission
            log is live on this console. Camera, drive, lights and position wait
            for confirmed hardware.
          </p>
        </header>
        <ul>
          {kit.map((item) => (
            <li key={item.id} className={item.live ? "is-on" : ""}>
              <i />
              <div>
                <strong>{item.name}</strong>
                <p>{item.role}</p>
              </div>
              <em>{item.status}</em>
            </li>
          ))}
        </ul>
      </section>

      <div className="rover-plan">
        <article className="mission-form">
          <p className="station-kicker">Mission</p>
          <h2>Plan an inspection.</h2>
          <p className="muted">
            Link a planned visit to the incident you want to inspect. Planning
            does not move the unit.
          </p>
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              const result = await mutate("/api/missions", {
                incident_id: incident,
                note,
              });
              if (result) {
                setNote("");
                setMissionId(result.id);
                notify(
                  `Mission ${result.id} recorded. No movement command was issued.`,
                );
              }
            }}
          >
            <label className="form-label">
              Related incident
              <select
                required
                value={incident}
                onChange={(e) => setIncident(e.target.value)}
              >
                <option value="">Choose an incident</option>
                {(data.incidents || []).map((i) => (
                  <option key={i.id} value={i.id}>
                    {NAMES[i.node_id] || `Node ${i.node_id}`} · {i.id}
                    {i.status === "CLOSED" ? " · closed" : ""}
                  </option>
                ))}
              </select>
            </label>
            <label className="form-label">
              Inspection objective
              <textarea
                required
                minLength={3}
                rows={3}
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="What should this inspection establish?"
              />
            </label>
            <button
              className="button primary full"
              disabled={busy || !incident || note.trim().length < 3}
            >
              Create planned mission
              <Icon name="arrow" size={16} />
            </button>
          </form>
          <p className="footnote">
            {!paired
              ? "Pair an operator session in the header before creating a mission."
              : "Mission planning is available. Motion and a camera still await confirmed rover hardware."}
          </p>
        </article>

        <article className="mission-list">
          <SectionHead eyebrow="MISSION ARCHIVE" title="Linked to an incident.">
            <Link className="button light" href="/incidents">
              Open incident log
              <Icon name="arrow" size={16} />
            </Link>
          </SectionHead>
          {!missions.length && (
            <Empty icon="rover" title="No inspection is planned yet.">
              Create a mission. Notes stay with the originating incident.
            </Empty>
          )}
          {missions.map((m) => (
            <article
              className={`mission-row ${m.id === mission?.id ? "is-active" : ""}`}
              key={m.id}
            >
              <span className="mission-symbol">
                <Icon name="rover" size={24} />
              </span>
              <div>
                <h3>{m.id}</h3>
                <p>{m.note}</p>
                <span className="small muted">
                  {m.unit || "R1"} · distinct from Node C · {m.incident_id} ·{" "}
                  {dateLabel(m.created_at)} · {m.state}
                </span>
                <p className="small muted">
                  {m.simulation === false
                    ? ""
                    : "Simulation. No physical command is sent. "}
                  {m.position?.note || "Last contact unavailable."}{" "}
                  {m.inspection_complete
                    ? "Checklist complete."
                    : "Inspection incomplete."}
                </p>
                {parseEvidence(m.evidence).map((e, i) => (
                  <p className="evidence-note" key={i}>
                    {e.note} <span>· {e.origin}</span>
                  </p>
                ))}
              </div>
              <div className="mission-actions">
                <button
                  type="button"
                  className="button light"
                  onClick={() => setMissionId(m.id)}
                >
                  Arm pad
                </button>
                <button
                  type="button"
                  className="button light"
                  onClick={() => {
                    setEvidence(m.id);
                    setFinding("");
                  }}
                >
                  Add review note
                  <Icon name="plus" size={16} />
                </button>
              </div>
            </article>
          ))}
        </article>
      </div>

      {evidence && (
        <Modal
          title="Add a mission review note"
          onClose={() => setEvidence(null)}
        >
          <p className="muted">
            This stores a text note. It does not claim a camera capture or a
            physical inspection.
          </p>
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              const result = await mutate(`/api/missions/${evidence}/evidence`, {
                note: finding,
                finding:
                  "Operator-entered prototype review note; no physical inspection verified.",
              });
              if (result) {
                setEvidence(null);
                notify("Review note attached to the mission.");
              }
            }}
          >
            <label className="form-label">
              Observation
              <textarea
                required
                rows={4}
                minLength={3}
                value={finding}
                onChange={(e) => setFinding(e.target.value)}
              />
            </label>
            <button
              className="button primary"
              disabled={busy || finding.trim().length < 3}
            >
              Save review note
            </button>
          </form>
        </Modal>
      )}
    </div>
  );
}
