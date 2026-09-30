"use client";

import { useEffect, useId, useRef, useState } from "react";
import Link from "next/link";
import {
  loadMoleThread,
  moleStatus,
  saveMoleThread,
  talkToMole,
} from "../lib/moleChat";

function MoleFace({ mood = "idle" }) {
  return (
    <svg
      className={`mole-face is-${mood}`}
      viewBox="0 0 80 80"
      aria-hidden="true"
      focusable="false"
    >
      <ellipse className="mole-soil" cx="40" cy="70" rx="30" ry="9" />
      <ellipse className="mole-soil-inner" cx="40" cy="70" rx="18" ry="5" />
      <g className="mole-rise">
        <ellipse className="mole-ear left" cx="22" cy="30" rx="7" ry="10" />
        <ellipse className="mole-ear right" cx="58" cy="30" rx="7" ry="10" />
        <ellipse className="mole-body" cx="40" cy="44" rx="22" ry="24" />
        <ellipse className="mole-belly" cx="40" cy="50" rx="12" ry="10" />
        <g className="mole-eyes">
          <ellipse cx="31" cy="38" rx="5" ry="6" />
          <ellipse cx="49" cy="38" rx="5" ry="6" />
          <circle className="mole-glint" cx="32.5" cy="36.5" r="1.7" />
          <circle className="mole-glint" cx="50.5" cy="36.5" r="1.7" />
        </g>
        <ellipse className="mole-snout" cx="40" cy="50" rx="11" ry="8" />
        <circle className="mole-nose" cx="40" cy="51" r="3.2" />
        <path className="mole-smile" d="M34 55c2.2 3 9.8 3 12 0" />
        <g className="mole-paws">
          <ellipse cx="24" cy="62" rx="7" ry="4.5" />
          <ellipse cx="56" cy="62" rx="7" ry="4.5" />
        </g>
      </g>
    </svg>
  );
}

function historyForModel(messages) {
  return messages
    .filter((row) => !row.local && row.content?.trim())
    .map((row) => ({ role: row.role, content: row.content }));
}

export function MoleDock() {
  const panelId = useId();
  const inputId = useId();
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState(null);
  const [hello, setHello] = useState(true);
  const [messages, setMessages] = useState([]);
  const scroller = useRef(null);
  const field = useRef(null);
  const abort = useRef(null);

  useEffect(() => {
    setMessages(loadMoleThread());
    const seen = sessionStorage.getItem("mole-hello");
    if (seen) setHello(false);
    moleStatus()
      .then(setStatus)
      .catch(() => setStatus({ ready: false }));
  }, []);

  useEffect(() => {
    saveMoleThread(messages);
    const node = scroller.current;
    if (node) node.scrollTop = node.scrollHeight;
  }, [messages, open]);

  useEffect(() => {
    if (!open) return undefined;
    field.current?.focus();
    function onKey(event) {
      if (event.key === "Escape") setOpen(false);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  function toggle() {
    setOpen((value) => {
      const next = !value;
      if (next) {
        setHello(false);
        sessionStorage.setItem("mole-hello", "1");
      }
      return next;
    });
  }

  async function ask(event) {
    event?.preventDefault();
    const question = draft.trim();
    if (!question || busy) return;
    const prior = historyForModel(messages);
    const user = {
      id: `u-${Date.now()}`,
      role: "user",
      content: question,
    };
    const pending = {
      id: `a-${Date.now()}`,
      role: "assistant",
      content: "",
      pending: true,
    };
    setDraft("");
    setBusy(true);
    setMessages((rows) => [...rows, user, pending]);
    abort.current?.abort();
    abort.current = new AbortController();
    try {
      const result = await talkToMole({
        question,
        history: prior,
        signal: abort.current.signal,
        onToken: (_token, full) => {
          setMessages((rows) =>
            rows.map((row) =>
              row.id === pending.id ? { ...row, content: full } : row,
            ),
          );
        },
      });
      setMessages((rows) =>
        rows.map((row) =>
          row.id === pending.id
            ? {
                ...row,
                content: result.answer,
                pending: false,
                sources: result.sources,
                model: result.model,
              }
            : row,
        ),
      );
    } catch (error) {
      if (error.name === "AbortError") return;
      setMessages((rows) =>
        rows.map((row) =>
          row.id === pending.id
            ? {
                ...row,
                pending: false,
                error: true,
                content: error.message || "Mole could not answer just then.",
              }
            : row,
        ),
      );
    } finally {
      setBusy(false);
    }
  }

  const mood = busy ? "think" : open ? "listen" : hello ? "hello" : "idle";
  const readyLabel = status?.ready
    ? `Listening · ${status.provider} · ${status.model}`
    : "Needs a Groq key";

  return (
    <div className={`mole-dock ${open ? "is-open" : ""}`}>
      {open && (
        <section
          className="mole-panel"
          id={panelId}
          role="dialog"
          aria-modal="true"
          aria-labelledby="mole-title"
        >
          <header className="mole-panel-head">
            <span className="mole-avatar" aria-hidden="true">
              <MoleFace mood={mood} />
            </span>
            <div>
              <p className="station-kicker">Companion</p>
              <h2 id="mole-title">Mole</h2>
              <p className="mole-status">{readyLabel}</p>
            </div>
            <button
              type="button"
              className="button light"
              onClick={() => setOpen(false)}
            >
              Close
            </button>
          </header>
          <div className="mole-thread" ref={scroller} aria-live="polite">
            {!messages.length && (
              <p className="mole-empty">
                {status?.ready
                  ? "I'm Mole. I stay with this console. Ask about a station, an incident, the rover, or how this mine is put together. I read the live records — I do not invent sensors."
                  : "I'm Mole. I talk through Groq's free API. Add GROQ_API_KEY from console.groq.com to the project .env file, then ask again."}
              </p>
            )}
            {messages.map((row) => (
              <article
                key={row.id}
                className={`mole-bubble is-${row.role} ${row.error ? "is-error" : ""} ${row.pending && !row.content ? "is-waiting" : ""}`}
              >
                <span>{row.role === "user" ? "You" : "Mole"}</span>
                <p>
                  {row.content ||
                    (row.pending ? "Mole is thinking…" : "")}
                </p>
                {row.sources?.length > 0 && (
                  <div className="mole-sources">
                    {row.sources.map((id) => (
                      <Link key={id} href={`/incidents?focus=${id}`}>
                        {id}
                      </Link>
                    ))}
                  </div>
                )}
              </article>
            ))}
          </div>
          <form className="mole-compose" onSubmit={ask}>
            <label htmlFor={inputId} className="sr-only">
              Ask Mole
            </label>
            <textarea
              id={inputId}
              ref={field}
              rows={2}
              value={draft}
              disabled={busy}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  ask(event);
                }
              }}
              placeholder="Ask Mole about this mine…"
            />
            <div className="mole-compose-row">
              <button
                type="button"
                className="button light"
                disabled={busy || !messages.length}
                onClick={() => setMessages([])}
              >
                Clear
              </button>
              <button
                className="button primary"
                disabled={busy || !draft.trim()}
              >
                {busy ? "Listening…" : "Ask Mole"}
              </button>
            </div>
          </form>
        </section>
      )}
      {hello && !open && <p className="mole-hi">Mole</p>}
      <button
        type="button"
        className={`mole-launcher ${open ? "is-open" : ""}`}
        aria-expanded={open}
        aria-controls={open ? panelId : undefined}
        onClick={toggle}
      >
        <span className="mole-launcher-art" aria-hidden="true">
          <MoleFace mood={mood} />
        </span>
        <span className="mole-launcher-name">Mole</span>
      </button>
    </div>
  );
}
