"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { dateLabel, request } from "../lib/format";
import {
  flushSOS,
  queueSOS,
  readOutbox,
  readSnapshot,
  saveSnapshot,
  updateReceipts,
} from "../lib/offline.mjs";

const COPY = {
  en: {
    lang: "हिन्दी",
    kicker: "Miners and residents",
    title: "Alerts and reports",
    lead: "See what is recorded at East Panel, and send a report from where you are. This page does not call a rescue team.",
    alerts: "Recorded alerts",
    refresh: "Refresh",
    none: "No open alert in this copy. That does not mean the ground is safe.",
    report: "Raise an issue",
    who: "Who is reporting",
    miner: "Miner",
    resident: "Resident",
    kind: "What is wrong",
    where: "Where",
    whereHint: "Road, house, gallery, or landmark",
    what: "What should the operator know",
    contact: "Phone number, if you want a call back",
    send: "Send report",
    sending: "Sending…",
    mine: "Reports from this phone",
    empty: "No report from this browser yet.",
    pending: "Saved here. The server has not received it.",
    queued: "The server stored this report. That does not mean a person has seen it.",
    noted: "An operator wrote a note. That is not a rescue.",
    offline: "Showing the last saved copy.",
    live: "Showing the latest server copy.",
    emergency: "For immediate danger, use the mine’s existing emergency channel. SMS and phone push are not connected.",
    monitor: "Operator monitor",
    sosTitle: "SOS",
    sosLead: "Send this to the server for miners and residents on this page. It does not text anyone and it does not call a rescue team.",
    prepare: "Prepare SOS",
    sendSos: "Send SOS now",
    sosBanner: "SOS for local people",
    sosReach: "Shown on this page to miners and residents. Not sent by SMS.",
    listen: "Turn on emergency alerts on this phone",
    listening: "This phone will be told to leave when a warning appears, while this page is open",
    leave: "Leave this area",
    leaveBody: "Move away from the warning now. Do not stay to watch the screen.",
    sosPop: "New SOS",
    popClose: "Close",
    noPlace: "Location not sent",
  },
  hi: {
    lang: "English",
    kicker: "खनिक और निवासी",
    title: "चेतावनी और शिकायत",
    lead: "ईस्ट पैनल पर दर्ज चेतावनियाँ देखें, और जहाँ आप हैं वहाँ से रिपोर्ट भेजें। यह पेज बचाव दल नहीं बुलाता।",
    alerts: "दर्ज चेतावनियाँ",
    refresh: "फिर देखें",
    none: "इस प्रति में कोई खुली चेतावनी नहीं है। इसका अर्थ यह नहीं कि ज़मीन सुरक्षित है।",
    report: "समस्या बताएँ",
    who: "कौन बता रहा है",
    miner: "खनिक",
    resident: "निवासी",
    kind: "क्या गड़बड़ है",
    where: "कहाँ",
    whereHint: "सड़क, घर, गैलरी या निशान",
    what: "ऑपरेटर को क्या जानना चाहिए",
    contact: "फ़ोन नंबर, अगर वापस कॉल चाहिए",
    send: "रिपोर्ट भेजें",
    sending: "भेज रहे हैं…",
    mine: "इस फ़ोन से भेजी रिपोर्ट",
    empty: "इस ब्राउज़र से अभी कोई रिपोर्ट नहीं।",
    pending: "यहाँ सहेजी गई है। सर्वर को अभी नहीं मिली।",
    queued: "सर्वर ने रिपोर्ट रख ली है। इसका अर्थ यह नहीं कि किसी ने इसे देख लिया है।",
    noted: "एक ऑपरेटर ने टिप्पणी लिखी। यह बचाव नहीं है।",
    offline: "आखिरी सहेजी प्रति दिख रही है।",
    live: "सर्वर की ताज़ा प्रति दिख रही है।",
    emergency: "तुरंत खतरे के लिए खदान का मौजूदा आपातकालीन तरीका इस्तेमाल करें। एसएमएस और फ़ोन पुश जुड़े नहीं हैं।",
    monitor: "ऑपरेटर मॉनिटर",
    sosTitle: "एसओएस",
    sosLead: "इसे इस पेज पर खनिकों और निवासियों के लिए सर्वर पर भेजें। यह किसी को एसएमएस नहीं करता और बचाव दल नहीं बुलाता।",
    prepare: "एसओएस तैयार करें",
    sendSos: "अभी एसओएस भेजें",
    sosBanner: "स्थानीय लोगों के लिए एसओएस",
    sosReach: "यह पेज खनिकों और निवासियों को दिखाता है। एसएमएस से नहीं भेजा गया।",
    listen: "इस फ़ोन पर आपातकालीन चेतावनी चालू करें",
    listening: "पेज खुला रहने पर खतरे के समय यह फ़ोन कहेगा कि यहाँ से हट जाएँ",
    leave: "यहाँ से हट जाएँ",
    leaveBody: "चेतावनी वाली जगह से अभी दूर जाएँ। स्क्रीन देखने के लिए रुके नहीं।",
    sosPop: "नया एसओएस",
    popClose: "बंद करें",
    noPlace: "जगह नहीं मिली",
  },
};

const KINDS = {
  en: [
    ["help", "Someone needs help"],
    ["movement", "Ground or wall movement"],
    ["gas", "Gas smell"],
    ["damage", "Crack, road, or building damage"],
    ["water", "Water where it should not be"],
    ["other", "Something else"],
  ],
  hi: [
    ["help", "किसी को मदद चाहिए"],
    ["movement", "ज़मीन या दीवार हिली"],
    ["gas", "गैस की गंध"],
    ["damage", "दरार, सड़क या इमारत"],
    ["water", "पानी जहाँ नहीं होना चाहिए"],
    ["other", "कुछ और"],
  ],
};

const SEVERITY = {
  en: {
    movement: "Movement",
    gas: "Gas",
    watch: "Watch",
    sensor_fault: "Sensor fault",
    stale: "Old reading",
    normal: "Steady",
    unavailable: "Unavailable",
  },
  hi: {
    movement: "हलचल",
    gas: "गैस",
    watch: "निगरानी",
    sensor_fault: "सेंसर दोष",
    stale: "पुराना आँकड़ा",
    normal: "स्थिर",
    unavailable: "अनुपलब्ध",
  },
};

function requestId() {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = [...bytes].map((value) => value.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

function tinyMessage(message) {
  const clean = String(message || "").replace(/\s+/g, " ").trim();
  const sentence = clean.split(/(?<=[.!?])\s/)[0] || clean;
  return sentence.length > 140 ? `${sentence.slice(0, 137)}…` : sentence;
}

function placeLine(item, fallback) {
  const name = item.place || item.landmark || "";
  const lat = Number(item.lat);
  const lon = Number(item.lon);
  const coords = Number.isFinite(lat) && Number.isFinite(lon) ? `${lat.toFixed(5)}, ${lon.toFixed(5)}` : "";
  if (name && coords) return `${name} · ${coords}`;
  return name || coords || fallback;
}
function receiptText(status, text) {
  if (status === "ACKNOWLEDGED") return text.noted;
  if (status === "LOCAL_PENDING") return text.pending;
  return text.queued;
}

export function FieldDesk() {
  const [lang, setLang] = useState("en");
  const [role, setRole] = useState("miner");
  const [kind, setKind] = useState("help");
  const [place, setPlace] = useState("");
  const [detail, setDetail] = useState("");
  const [contact, setContact] = useState("");
  const [snapshot, setSnapshot] = useState(null);
  const [live, setLive] = useState(false);
  const [items, setItems] = useState([]);
  const [bulletins, setBulletins] = useState([]);
  const [armed, setArmed] = useState(false);
  const [listening, setListening] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [popup, setPopup] = useState(null);
  const seen = useRef(new Set());
  const popSeen = useRef(new Set());
  const popQueue = useRef([]);
  const primed = useRef(false);
  const closeRef = useRef(null);
  const text = COPY[lang];
  const kinds = KINDS[lang];
  const data = snapshot?.data;
  const alerts = (data?.incidents || []).filter((item) => item.status !== "CLOSED");
  const stations = (data?.nodes || []).filter((node) =>
    ["movement", "gas", "watch", "sensor_fault", "stale"].includes(node.condition),
  );

  async function refresh() {
    try {
      const next = await request("/api/state");
      const saved = saveSnapshot(localStorage, next);
      setSnapshot(saved);
      setBulletins(next.bulletins || []);
      setLive(true);
      setItems(updateReceipts(localStorage, next.sos || []));
      const arrivals = [
        ...(next.bulletins || []).map((item) => ({
          id: item.id,
          place: placeLine(item, text.noPlace),
          message: tinyMessage(item.message) || text.leaveBody,
        })),
        ...(next.sos || [])
          .filter((item) => item.origin === "physical" && /SOS|एसओएस/i.test(item.message || ""))
          .map((item) => ({
            id: item.id,
            place: placeLine(item, text.noPlace),
            message: tinyMessage(item.message) || text.sosTitle,
          })),
      ];
      if (!primed.current) {
        arrivals.forEach((item) => popSeen.current.add(item.id));
        primed.current = true;
      } else {
        const fresh = arrivals.filter((item) => item.id && !popSeen.current.has(item.id));
        fresh.forEach((item) => popSeen.current.add(item.id));
        if (fresh.length) {
          popQueue.current.push(...fresh.slice(1));
          setPopup((current) => current || fresh[0]);
        }
      }
      const flushed = await flushSOS(localStorage, (packet) => request("/api/sos", packet));
      setItems(flushed.items);
      if (flushed.error) setError(flushed.error);
    } catch {
      setLive(false);
      setSnapshot(readSnapshot(localStorage));
      setItems(readOutbox(localStorage));
    }
  }

  useEffect(() => {
    setItems(readOutbox(localStorage));
    setSnapshot(readSnapshot(localStorage));
    setListening(typeof Notification !== "undefined" && Notification.permission === "granted");
    refresh();
    const timer = setInterval(refresh, 2000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!popup) return undefined;
    closeRef.current?.focus();
    function onKey(event) {
      if (event.key === "Escape") setPopup(popQueue.current.shift() || null);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [popup]);

  useEffect(() => {
    if (!listening || typeof Notification === "undefined" || Notification.permission !== "granted") return;
    for (const item of bulletins) {
      if (seen.current.has(item.id)) continue;
      seen.current.add(item.id);
      try {
        new Notification(text.leave, { body: `${text.leaveBody} ${item.place || ""}`.trim(), tag: item.id });
      } catch {}
    }
  }, [bulletins, listening, text.leave, text.leaveBody]);

  async function enableListen() {
    if (typeof Notification === "undefined") return;
    const permission = await Notification.requestPermission();
    setListening(permission === "granted");
  }

  async function sendSos() {
    setBusy(true);
    setError("");
    try {
      const who = role === "miner" ? "Miner" : "Resident";
      const packet = {
        request_id: requestId(),
        landmark: place.trim() || null,
        contact: contact.trim() || null,
        message: `${who} · SOS. Need help now.${detail.trim() ? ` ${detail.trim()}` : ""}`,
        delivered: false,
      };
      setItems(queueSOS(localStorage, packet));
      setArmed(false);
      const flushed = await flushSOS(localStorage, (body) => request("/api/sos", body));
      setItems(flushed.items);
      if (flushed.error) setError(flushed.error);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const who = role === "miner" ? "Miner" : "Resident";
      const topic = KINDS.en.find((item) => item[0] === kind)?.[1] || "Report";
      const packet = {
        request_id: requestId(),
        landmark: place.trim() || null,
        contact: contact.trim() || null,
        message: `${who} · ${topic}. ${detail.trim()}`,
        delivered: false,
      };
      setItems(queueSOS(localStorage, packet));
      setDetail("");
      setPlace("");
      setContact("");
      const flushed = await flushSOS(localStorage, (body) => request("/api/sos", body));
      setItems(flushed.items);
      if (flushed.error) setError(flushed.error);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="field-desk">
      <header className="field-bar">
        <Link href="/" className="field-brand">MOLE</Link>
        <button type="button" className="field-lang" onClick={() => setLang(lang === "en" ? "hi" : "en")}>
          {text.lang}
        </button>
      </header>
      <p className="field-kicker">{text.kicker}</p>
      <h1>{text.title}</h1>
      <p className="field-lead">{text.lead}</p>
      <p className="field-note">{live ? text.live : text.offline}</p>
      {error ? <p className="field-error" role="alert">{error}</p> : null}
      {popup ? (
        <div className="sos-pop-backdrop" role="presentation">
          <div className="sos-pop" role="alertdialog" aria-modal="true" aria-labelledby="sos-pop-title">
            <p className="field-kicker">{text.sosPop}</p>
            <h2 id="sos-pop-title">{popup.place}</h2>
            <p>{popup.message}</p>
            <button
              ref={closeRef}
              type="button"
              className="field-ghost"
              onClick={() => setPopup(popQueue.current.shift() || null)}
            >
              {text.popClose}
            </button>
          </div>
        </div>
      ) : null}

      {bulletins.length ? (
        <section className="field-sos" role="alert">
          <p className="field-leave">{text.leave}</p>
          <p className="field-lead">{text.leaveBody}</p>
          {bulletins.map((item) => (
            <article key={item.id}>
              <h2>{item.place}</h2>
              <p>{item.message}</p>
              <p className="field-meta">{dateLabel(item.created_at)} · {text.sosReach}</p>
            </article>
          ))}
        </section>
      ) : (
        <p className="field-note">{text.calm}</p>
      )}
      <button type="button" className="field-ghost" onClick={enableListen} disabled={listening}>
        {listening ? text.listening : text.listen}
      </button>

      <section className="field-card">
        <h2>{text.sosTitle}</h2>
        <p className="field-note">{text.sosLead}</p>
        {!armed ? (
          <button type="button" className="field-sos-button" onClick={() => setArmed(true)}>{text.prepare}</button>
        ) : (
          <button type="button" className="field-sos-button" disabled={busy} onClick={sendSos}>
            {busy ? text.sending : text.sendSos}
          </button>
        )}
      </section>

      <section className="field-card" aria-live="polite">
        <div className="field-card-head">
          <h2>{text.alerts}</h2>
          <button type="button" className="field-ghost" onClick={refresh}>{text.refresh}</button>
        </div>
        {alerts.map((item) => (
          <article key={item.id} className="field-alert">
            <p className="field-severity">{SEVERITY[lang][item.severity] || item.severity}</p>
            <h3>{item.title}</h3>
            <p>{item.explanation}</p>
            <p className="field-meta">{dateLabel(item.updated_at)}</p>
          </article>
        ))}
        {stations.map((node) => (
          <article key={node.id} className="field-alert">
            <p className="field-severity">{SEVERITY[lang][node.condition] || node.condition}</p>
            <h3>{node.name || node.id}</h3>
            <p>{node.place}</p>
            {node.analysis?.summary ? <p>{node.analysis.summary}</p> : null}
          </article>
        ))}
        {!alerts.length && !stations.length ? <p>{text.none}</p> : null}
      </section>

      <section className="field-card">
        <h2>{text.report}</h2>
        <form onSubmit={submit}>
          <fieldset className="field-choice">
            <legend>{text.who}</legend>
            {["miner", "resident"].map((value) => (
              <label key={value} className={role === value ? "is-on" : ""}>
                <input
                  type="radio"
                  name="role"
                  value={value}
                  checked={role === value}
                  onChange={() => setRole(value)}
                />
                {text[value]}
              </label>
            ))}
          </fieldset>
          <label className="form-label">
            {text.kind}
            <select value={kind} onChange={(event) => setKind(event.target.value)}>
              {kinds.map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </label>
          <label className="form-label">
            {text.where}
            <input value={place} onChange={(event) => setPlace(event.target.value)} maxLength={500} placeholder={text.whereHint} />
          </label>
          <label className="form-label">
            {text.what}
            <textarea value={detail} onChange={(event) => setDetail(event.target.value)} required minLength={3} maxLength={1500} rows={4} />
          </label>
          <label className="form-label">
            {text.contact}
            <input value={contact} onChange={(event) => setContact(event.target.value)} maxLength={40} inputMode="tel" />
          </label>
          <button className="field-send" disabled={busy || detail.trim().length < 3}>
            {busy ? text.sending : text.send}
          </button>
        </form>
        <p className="field-note">{text.emergency}</p>
      </section>

      <section className="field-card" aria-live="polite">
        <h2>{text.mine}</h2>
        {!items.length ? <p>{text.empty}</p> : null}
        {items.map((item) => {
          const server = data?.sos?.find((row) => row.id === item.receiptId);
          const status = server?.status || item.status;
          return (
            <article key={item.requestId || item.packet?.request_id} className="field-alert">
              <h3>{item.packet?.landmark || text.report}</h3>
              <p>{receiptText(status, text)}</p>
              <p className="field-meta">
                {item.receiptId ? `${item.receiptId} · ` : ""}
                {dateLabel(item.createdAt)}
              </p>
            </article>
          );
        })}
      </section>
      <p className="field-foot">
        <Link href="/">{text.monitor}</Link>
      </p>
    </main>
  );
}
