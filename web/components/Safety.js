"use client";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { request, dateLabel } from "../lib/format";
import {
  readSnapshot,
  saveSnapshot,
  readOutbox,
  queueSOS,
  flushSOS,
  updateReceipts,
} from "../lib/offline.mjs";
import { Badge, SectionHead, Empty } from "./Primitives";
import { Brand } from "./Brand";

export function Safety() {
  const [snapshot, setSnapshot] = useState(null),
    [connected, setConnected] = useState(false),
    [items, setItems] = useState([]),
    [error, setError] = useState(""),
    [message, setMessage] = useState(""),
    [landmark, setLandmark] = useState(""),
    [location, setLocation] = useState(null),
    [locating, setLocating] = useState(false),
    [busy, setBusy] = useState(false),
    [permission, setPermission] = useState("default"),
    [privateRows, setPrivateRows] = useState(null),
    [notes, setNotes] = useState({});
  const syncing = useRef(false),
    seen = useRef(null),
    mounted = useRef(true);
  async function sync() {
    if (syncing.current) return;
    syncing.current = true;
    try {
      const result = await flushSOS(localStorage, (p) =>
        request("/api/sos", p),
      );
      if (mounted.current) {
        setItems(result.items);
        if (result.error)
          setError(
            `Not confirmed by server: ${result.error} Your pending request stays on this device.`,
          );
        else
          setError((previous) =>
            previous.startsWith("Not confirmed by server:") ? "" : previous,
          );
      }
    } catch (e) {
      if (mounted.current) setError(`Device storage unavailable: ${e.message}`);
    } finally {
      syncing.current = false;
    }
  }
  async function refresh() {
    try {
      const data = await request("/api/state");
      if (!mounted.current) return;
      const savedAt = new Date().toISOString();
      setSnapshot({ data, savedAt });
      setConnected(true);
      try {
        saveSnapshot(localStorage, data);
      } catch {
        setError("Offline snapshot could not be saved on this device.");
      }
      const signatures = new Set(
        data.incidents
          .filter((i) => i.status !== "CLOSED")
          .map((i) => `${i.id}:${i.severity}`),
      );
      if (
        seen.current &&
        "Notification" in window &&
        Notification.permission === "granted"
      ) {
        for (const i of data.incidents.filter((i) => i.status !== "CLOSED"))
          if (!seen.current.has(`${i.id}:${i.severity}`)) {
            try {
              new Notification(`MOLE: ${i.title}`, {
                body: `${i.origin} observation. Open MOLE to review the evidence.`,
                tag: i.id,
              });
            } catch {}
          }
      }
      seen.current = signatures;
      await sync();
      try {setItems(updateReceipts(localStorage,data.sos || []));} catch {}
    } catch {
      if (mounted.current) setConnected(false);
    }
  }
  useEffect(() => {
    mounted.current = true;
    setSnapshot(readSnapshot(localStorage));
    setItems(readOutbox(localStorage));
    setPermission(
      "Notification" in window ? Notification.permission : "unsupported",
    );
    refresh();
    const timer = setInterval(refresh, 10000);
    const online = () => refresh();
    window.addEventListener("online", online);
    return () => {
      mounted.current = false;
      clearInterval(timer);
      window.removeEventListener("online", online);
    };
  }, []);
  async function send(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      if (!crypto.randomUUID)
        throw new Error(
          "A secure HTTPS connection is required to create a request ID.",
        );
      const packet = {
        request_id: crypto.randomUUID(),
        message: message.trim(),
        landmark: landmark.trim(),
        ...(location || {}),
      };
      setItems(queueSOS(localStorage, packet));
      setMessage("");
      setLandmark("");
      setLocation(null);
      await sync();
    } catch (e) {
      setError(`Request was not saved: ${e.message}`);
    } finally {
      setBusy(false);
    }
  }
  function locate() {
    if (!navigator.geolocation) {
      setError("Location is unavailable. Enter a landmark instead.");
      return;
    }
    setLocating(true);
    setError("");
    navigator.geolocation.getCurrentPosition(
      (p) => {
        setLocation({
          lat: p.coords.latitude,
          lon: p.coords.longitude,
          accuracy_m: p.coords.accuracy,
          located_at: new Date(p.timestamp).toISOString(),
        });
        setLocating(false);
      },
      () => {
        setError("Could not obtain location. You can still send a landmark.");
        setLocating(false);
      },
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 0 },
    );
  }
  const active =
    snapshot?.data.incidents.filter((i) => i.status !== "CLOSED") || [];
  return (
    <main className="safety-shell">
      <header className="safety-header">
        <Brand tagline="FIELD COMPANION" label="MOLE field companion" />
        <Link className="button light" href="/">
          Open workspace
        </Link>
      </header>
      <div className="page-heading">
        <div>
          <p className="eyebrow">PEOPLE & RESPONSE</p>
          <h1>Stay informed. Be heard.</h1>
          <p>
            Recorded alerts, a local SOS outbox, and a clear receipt for every
            request.
          </p>
        </div>
        <span className={`badge ${connected ? "normal" : "stale"}`}>
          {connected ? "Service connected" : "Offline / reconnecting"}
        </span>
      </div>
      <div className="inline-warning">
        {snapshot
          ? `${connected ? "Last synchronized" : "Historical snapshot saved"} ${dateLabel(snapshot.savedAt)}. Sensor observation times may be older.`
          : "No saved readings yet. Connect once to load site records."}
      </div>
      {error && (
        <p className="safety-error" role="alert">
          {error}
        </p>
      )}
      <div className="safety-grid">
        <article className="panel safety-card">
          <SectionHead eyebrow="ASK FOR HELP" title="Send an SOS" />
          <p className="muted">
            Requests reach this project's server when connected. External
            emergency dispatch, SMS and push delivery are not configured. Use
            your site's established emergency channel for urgent help.
          </p>
          <form onSubmit={send}>
            <label className="form-label">
              Landmark or gallery
              <input
                value={landmark}
                onChange={(e) => setLandmark(e.target.value)}
                maxLength={500}
                placeholder="For example: Panel 1, north access"
              />
            </label>
            <label className="form-label">
              What happened?
              <textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                required
                minLength={3}
                maxLength={1500}
                rows={3}
                placeholder="Briefly describe the help needed."
              />
            </label>
            <div className="button-row">
              <button
                type="button"
                className="button light"
                disabled={locating}
                onClick={locate}
              >
                {locating ? "Locating…" : "Attach my location"}
              </button>
              {location && (
                <button
                  type="button"
                  className="button light"
                  onClick={() => setLocation(null)}
                >
                  Remove location
                </button>
              )}
            </div>
            {location && (
              <p className="footnote">
                Location attached, accuracy approximately{" "}
                {Math.round(location.accuracy_m)} m. Captured{" "}
                {dateLabel(location.located_at)}. Underground positioning may be
                unavailable.
              </p>
            )}
            <button
              className="button primary full"
              disabled={busy || message.trim().length < 3}
            >
              {busy ? "Saving request…" : "Save & send SOS"}
            </button>
            <p className="footnote">
              Saved on this device first. Pending requests retry while this page
              is open. Clearing browser data removes unsent requests. Location
              and message are visible only to paired operators after receipt.
            </p>
          </form>
        </article>
        <article className="panel safety-card">
          <SectionHead eyebrow="DEVICE OUTBOX" title="Know where it stands">
            <button className="button light" onClick={sync}>
              Retry pending
            </button>
          </SectionHead>
          {!items.length && (
            <Empty title="No requests from this device.">
              Your SOS receipts will appear here.
            </Empty>
          )}
          <div aria-live="polite">
            {items.map((item) => {
              const server = snapshot?.data.sos?.find(
                (s) => s.id === item.receiptId,
              );
              const status = server?.status || item.status;
              return (
                <div
                  className="sos-receipt"
                  key={item.requestId || item.packet.request_id}
                >
                  <strong>
                    {status === "LOCAL_PENDING"
                      ? "On this device — not received"
                      : status === "ACKNOWLEDGED"
                        ? "Acknowledged by an operator"
                        : "Received by server — awaiting operator"}
                  </strong>
                  <p>{dateLabel(item.createdAt)}</p>
                  <small>
                    {item.receiptId || "Waiting for a server receipt"}
                  </small>
                  <p className="footnote">
                    {status === "ACKNOWLEDGED"
                      ? "Acknowledgement does not confirm rescue or dispatch."
                      : status === "LOCAL_PENDING"
                        ? "Keep this page open when connectivity returns."
                        : "No external dispatch confirmation is available."}
                  </p>
                </div>
              );
            })}
          </div>
        </article>
      </div>
      <article className="panel safety-card">
        <SectionHead eyebrow="SITE BULLETIN" title="Recorded alerts">
          <button className="button light" onClick={refresh}>
            Refresh
          </button>
        </SectionHead>
        <p className="footnote">
          {connected
            ? "Showing server records."
            : "Offline: historical conditions only."}{" "}
          Observation source is shown on each alert.
        </p>
        <div className="safety-alerts">
          {active.map((i) => (
            <div className="sos-receipt" key={i.id}>
              <Badge condition={i.severity} />
              <h3>{i.title}</h3>
              <p>{i.explanation}</p>
              <small>
                {i.origin} · {dateLabel(i.updated_at)}
              </small>
              <Link className="text-button" href="/incidents">
                Open incident records
              </Link>
            </div>
          ))}
        </div>
        {snapshot && !active.length && (
          <p>
            No open incidents in this snapshot. This does not establish current
            safety.
          </p>
        )}
        <div className="notification-settings">
          <button
            className="button"
            disabled={
              permission === "granted" ||
              permission === "unsupported" ||
              permission === "denied"
            }
            onClick={async () => {
              try {
                setPermission(await Notification.requestPermission());
              } catch {
                setPermission("unsupported");
              }
            }}
          >
            {permission === "granted"
              ? "Browser alerts enabled"
              : permission === "denied"
                ? "Notifications blocked in browser settings"
                : permission === "unsupported"
                  ? "Browser notifications unavailable"
                  : "Enable browser alerts"}
          </button>
          <p className="footnote">
            New or changed incident alerts while this page is open. Background
            push and SMS are not connected.
          </p>
        </div>
      </article>
      <article className="panel safety-card">
        <SectionHead eyebrow="PAIRED OPERATOR" title="SOS response desk">
          <button
            className="button light"
            onClick={async () => {
              try {
                setPrivateRows((await request("/api/sos/operator")).requests);
                setError("");
              } catch (e) {
                setError(e.message);
              }
            }}
          >
            Load operator inbox
          </button>
        </SectionHead>
        <p className="muted">
          Pair your browser in the workspace first. Private request details are
          not stored in the offline snapshot.
        </p>
        {privateRows?.map((row) => (
          <div key={row.id} className="sos-receipt">
            <strong>{row.id}</strong>
            <p>
              {row.landmark || "No landmark"} · {row.message || "No message"}
            </p>
            {row.lat !== null && (
              <p>
                Reported location: {row.lat}, {row.lon} · accuracy{" "}
                {row.accuracy_m ?? "unknown"} m
              </p>
            )}
            <small>
              {row.status} · {dateLabel(row.created_at)}
            </small>
            {row.status === "QUEUED" && (
              <form
                onSubmit={async (e) => {
                  e.preventDefault();
                  try {
                    await request(`/api/sos/${row.id}/acknowledge`, {
                      reason: notes[row.id],
                    });
                    setPrivateRows(
                      (await request("/api/sos/operator")).requests,
                    );
                    refresh();
                  } catch (e) {
                    setError(e.message);
                  }
                }}
              >
                <label className="form-label">
                  Operator response note
                  <input
                    required
                    minLength={3}
                    maxLength={2000}
                    value={notes[row.id] || ""}
                    onChange={(e) =>
                      setNotes({ ...notes, [row.id]: e.target.value })
                    }
                  />
                </label>
                <button
                  className="button"
                  disabled={(notes[row.id] || "").trim().length < 3}
                >
                  Record acknowledgement
                </button>
              </form>
            )}
          </div>
        ))}
        {privateRows?.length === 0 && <p>No SOS requests recorded.</p>}
      </article>
    </main>
  );
}
