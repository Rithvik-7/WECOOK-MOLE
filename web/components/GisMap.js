"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Badge } from "./Primitives";
import { channels, labels, timeLabel, value } from "../lib/format";

const FALLBACK = {
  A: { x: 28, y: 42 },
  B: { x: 48, y: 38 },
  C: { x: 62, y: 58 },
  D: { x: 74, y: 34 },
};
const MIN_SCALE = 0.7;
const MAX_SCALE = 6;

function points(nodes) {
  return (nodes || []).map((node) => {
    const spot = FALLBACK[node.id] || { x: 50, y: 50 };
    const x = Number.isFinite(Number(node.x)) ? Number(node.x) : spot.x;
    const y = Number.isFinite(Number(node.y)) ? Number(node.y) : spot.y;
    return { ...node, gx: x, gy: y };
  });
}

function troubled(node) {
  const vibration = Number(node.latest?.vibration);
  return (
    ["movement", "gas", "watch"].includes(node.condition) ||
    (Number.isFinite(vibration) && vibration >= 2.5)
  );
}

const SCARS = {
  A: "M-5 1 L-2 -2 L1 2 L4 -1",
  B: "M-4 2 L0 -3 L2 1 L5 0",
  C: "M-6 0 L-2 2 L1 -2 L5 1 M-1 3 L2 -1",
  D: "M-3 -2 L1 2 L4 -2 M-4 2 L0 0 L3 3",
};

function readings(node) {
  return (node.capabilities || [])
    .map((key) => {
      const meta = channels[key];
      const raw = node.latest?.[key];
      if (!meta || raw == null || !Number.isFinite(Number(raw))) return null;
      return `${meta.label} ${value(raw, meta.precision)} ${meta.unit}`;
    })
    .filter(Boolean);
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function clampView(x, y, scale) {
  const next = clamp(scale, MIN_SCALE, MAX_SCALE);
  const width = 100 / next;
  const height = 100 / next;
  const margin = 18;
  const limitX = 100 + margin - width;
  const limitY = 100 + margin - height;
  return {
    x: width >= 100 + margin * 2 ? (100 - width) / 2 : clamp(x, -margin, Math.max(-margin, limitX)),
    y: height >= 100 + margin * 2 ? (100 - height) / 2 : clamp(y, -margin, Math.max(-margin, limitY)),
    scale: next,
  };
}

export function GisMap({ data, selected, onSelect }) {
  const frameRef = useRef(null);
  const viewRef = useRef({ x: 0, y: 0, scale: 1 });
  const pointers = useRef(new Map());
  const dragRef = useRef(null);
  const pinchRef = useRef(null);
  const skipClick = useRef(false);
  const [view, setView] = useState(viewRef.current);
  const [frameSize, setFrameSize] = useState({ w: 800, h: 560 });
  const [panning, setPanning] = useState(false);
  const [card, setCard] = useState(null);
  const [hoverId, setHoverId] = useState(null);
  const nodes = useMemo(() => points(data?.nodes), [data]);
  const active = card ? nodes.find((node) => node.id === card) || null : null;

  function commit(next) {
    const clamped = clampView(next.x, next.y, next.scale);
    viewRef.current = clamped;
    setView(clamped);
  }

  function zoomAt(clientX, clientY, nextScale) {
    const frame = frameRef.current;
    if (!frame) return;
    const current = viewRef.current;
    const scale = clamp(nextScale, MIN_SCALE, MAX_SCALE);
    const rect = frame.getBoundingClientRect();
    const px = clamp((clientX - rect.left) / rect.width, 0, 1);
    const py = clamp((clientY - rect.top) / rect.height, 0, 1);
    const worldX = current.x + px * (100 / current.scale);
    const worldY = current.y + py * (100 / current.scale);
    commit({
      x: worldX - px * (100 / scale),
      y: worldY - py * (100 / scale),
      scale,
    });
  }

  function zoomCenter(nextScale) {
    const frame = frameRef.current;
    if (!frame) return;
    const rect = frame.getBoundingClientRect();
    zoomAt(rect.left + rect.width / 2, rect.top + rect.height / 2, nextScale);
  }

  useEffect(() => {
    const frame = frameRef.current;
    if (!frame) return undefined;
    const observer = new ResizeObserver(() => {
      setFrameSize({ w: frame.clientWidth, h: frame.clientHeight });
    });
    observer.observe(frame);
    setFrameSize({ w: frame.clientWidth, h: frame.clientHeight });
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const frame = frameRef.current;
    if (!frame) return undefined;
    function onWheel(event) {
      event.preventDefault();
      const factor = event.deltaY < 0 ? 1.18 : 1 / 1.18;
      zoomAt(event.clientX, event.clientY, viewRef.current.scale * factor);
    }
    frame.addEventListener("wheel", onWheel, { passive: false });
    return () => frame.removeEventListener("wheel", onWheel);
  }, []);

  function markerPoint(node) {
    const width = 100 / view.scale;
    const height = 100 / view.scale;
    return {
      left: ((node.gx - view.x) / width) * frameSize.w,
      top: ((node.gy - view.y) / height) * frameSize.h,
    };
  }

  function onPointerDown(event) {
    if (event.target.closest("button, .pog-popup")) return;
    const frame = frameRef.current;
    try {
      frame.setPointerCapture(event.pointerId);
    } catch {
      /* Synthetic events cannot capture the pointer. Drag still tracks the move. */
    }
    pointers.current.set(event.pointerId, { x: event.clientX, y: event.clientY });
    if (pointers.current.size === 1) {
      dragRef.current = {
        x: event.clientX,
        y: event.clientY,
        ox: viewRef.current.x,
        oy: viewRef.current.y,
        moved: false,
        station: event.target.closest("[data-station]")?.dataset.station || "",
      };
      setPanning(true);
    }
  }

  function onPointerMove(event) {
    if (!pointers.current.has(event.pointerId)) return;
    pointers.current.set(event.pointerId, { x: event.clientX, y: event.clientY });
    const frame = frameRef.current;
    if (pointers.current.size >= 2) {
      const [a, b] = [...pointers.current.values()];
      const dist = Math.hypot(a.x - b.x, a.y - b.y);
      const midX = (a.x + b.x) / 2;
      const midY = (a.y + b.y) / 2;
      if (!pinchRef.current) {
        pinchRef.current = { dist, scale: viewRef.current.scale };
      }
      const ratio = dist / Math.max(pinchRef.current.dist, 1);
      zoomAt(midX, midY, pinchRef.current.scale * ratio);
      return;
    }
    const drag = dragRef.current;
    if (!drag || !frame) return;
    const dx = event.clientX - drag.x;
    const dy = event.clientY - drag.y;
    if (Math.hypot(dx, dy) > 8) drag.moved = true;
    const rect = frame.getBoundingClientRect();
    const width = 100 / viewRef.current.scale;
    const height = 100 / viewRef.current.scale;
    commit({
      x: drag.ox - (dx / rect.width) * width,
      y: drag.oy - (dy / rect.height) * height,
      scale: viewRef.current.scale,
    });
  }

  function onPointerUp(event) {
    const drag = dragRef.current;
    pointers.current.delete(event.pointerId);
    if (pointers.current.size < 2) pinchRef.current = null;
    if (pointers.current.size === 0) {
      if (drag?.moved) {
        skipClick.current = true;
        window.setTimeout(() => {
          skipClick.current = false;
        }, 80);
      } else if (drag?.station) {
        onSelect(drag.station);
        setCard(drag.station);
      }
      dragRef.current = null;
      setPanning(false);
    }
  }

  function onKeyDown(event) {
    if (event.target.closest("button, .pog-popup")) return;
    const step = 10 / view.scale;
    if (event.key === "ArrowLeft") commit({ ...view, x: view.x - step });
    else if (event.key === "ArrowRight") commit({ ...view, x: view.x + step });
    else if (event.key === "ArrowUp") commit({ ...view, y: view.y - step });
    else if (event.key === "ArrowDown") commit({ ...view, y: view.y + step });
    else if (event.key === "+" || event.key === "=") zoomCenter(view.scale * 1.25);
    else if (event.key === "-" || event.key === "_") zoomCenter(view.scale / 1.25);
    else if (event.key === "0") commit({ x: 0, y: 0, scale: 1 });
    else return;
    event.preventDefault();
  }

  const chosen = nodes.find((node) => node.id === selected) || null;
  const popup = active ? markerPoint(active) : null;
  const popupBelow = popup ? popup.top < 168 : false;

  return (
    <section className="pog-layout" aria-label="Plan of ground">
      <div className="pog-stage">
        <div
          className={`pog-frame ${panning ? "is-panning" : ""}`}
          ref={frameRef}
          tabIndex={0}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerCancel={onPointerUp}
          onDoubleClick={(event) => {
            if (event.target.closest("button, .pog-popup")) return;
            zoomAt(event.clientX, event.clientY, view.scale * 1.7);
          }}
          onKeyDown={onKeyDown}
          aria-label="Illustrated satellite of the demonstration layout. North is the top of the picture. Drag to move, scroll or pinch to zoom. Hover a station for its issue and readings."
        >
          <svg
            viewBox={`${view.x} ${view.y} ${100 / view.scale} ${100 / view.scale}`}
            preserveAspectRatio="none"
            role="img"
            aria-label="Top-down satellite of the east panel. North is up. Station positions follow the demonstration layout, not a GPS survey."
          >
            <image
              href="/images/mole-satellite.png"
              x="0"
              y="0"
              width="100"
              height="100"
              preserveAspectRatio="none"
            />
            <g className="pog-north" transform="translate(8 10)">
              <path d="M0 7 V0 M-2.2 2.2 L0 0 L2.2 2.2" />
              <text x="3.2" y="3">N</text>
            </g>
            {nodes.filter(troubled).map((node) => (
              <g key={node.id} className={`pog-scar scar-${node.id}`} transform={`translate(${node.gx} ${node.gy})`}>
                <ellipse rx="7" ry="4.2" />
                <path d={SCARS[node.id] || SCARS.A} />
              </g>
            ))}
          </svg>
          {nodes.map((node) => {
            const spot = markerPoint(node);
            const onMap =
              spot.left > -30 && spot.left < frameSize.w + 30 && spot.top > -30 && spot.top < frameSize.h + 30;
            if (!onMap) return null;
            const shaking = troubled(node);
            const tipBelow = spot.top < 150;
            return (
              <div
                key={node.id}
                className={`pog-marker ${node.condition || "unknown"} ${selected === node.id ? "is-selected" : ""} ${shaking ? "is-shaking" : ""}`}
                style={{ left: spot.left, top: spot.top }}
                data-station={node.id}
                role="button"
                tabIndex={0}
                aria-pressed={selected === node.id}
                aria-label={`${node.id}, ${node.place || node.name}, ${labels[node.condition] || node.condition}`}
                onMouseEnter={() => setHoverId(node.id)}
                onMouseLeave={() => setHoverId((current) => (current === node.id ? null : current))}
                onFocus={() => setHoverId(node.id)}
                onBlur={() => setHoverId((current) => (current === node.id ? null : current))}
                onClick={() => {
                  if (skipClick.current) {
                    skipClick.current = false;
                    return;
                  }
                  onSelect(node.id);
                  setCard(node.id);
                }}
                onKeyDown={(event) => {
                  if (event.key !== "Enter" && event.key !== " ") return;
                  event.preventDefault();
                  onSelect(node.id);
                  setCard(node.id);
                }}
              >
                <b>{node.id}</b>
                {hoverId === node.id ? (
                  <div className={`pog-hover ${tipBelow ? "is-below" : ""}`} role="tooltip">
                    <strong>
                      {node.id} {node.place || node.name}
                    </strong>
                    <span>{labels[node.condition] || node.condition}</span>
                    {readings(node).map((line) => (
                      <span key={line}>{line}</span>
                    ))}
                    {shaking ? <em>Ground here is unsettled.</em> : null}
                  </div>
                ) : null}
              </div>
            );
          })}
          {active && popup && (
            <div
              className={`pog-popup ${popupBelow ? "is-below" : ""}`}
              style={{ left: clamp(popup.left, 130, Math.max(130, frameSize.w - 130)), top: popup.top }}
              role="dialog"
              aria-label={`${active.name} on the plan`}
            >
              <div className="pog-popup-head">
                <h3>
                  {active.id} {active.place || active.name}
                </h3>
                <button type="button" aria-label="Close station card" onClick={() => setCard(null)}>
                  ×
                </button>
              </div>
              <Badge condition={active.condition} />
              <p>Last sample {timeLabel(active.latest?.sample_time)}</p>
              {readings(active).length ? (
                <ul>
                  {readings(active).map((line) => (
                    <li key={line}>{line}</li>
                  ))}
                </ul>
              ) : (
                <p>No numeric reading in the latest sample.</p>
              )}
            </div>
          )}
          <div className="pog-compass" aria-hidden="true">
            <span>N</span>
          </div>
          <div className="pog-zoom" role="group" aria-label="Map zoom">
            <button type="button" aria-label="Zoom in" onClick={() => zoomCenter(view.scale * 1.35)}>
              +
            </button>
            <button type="button" aria-label="Zoom out" onClick={() => zoomCenter(view.scale / 1.35)}>
              −
            </button>
            <button type="button" aria-label="Reset view" onClick={() => commit({ x: 0, y: 0, scale: 1 })}>
              ⌂
            </button>
          </div>
        </div>
        <p className="pog-note">
          North is the top of the picture. Hover a station for its issue, tilt, and other readings. Cave mouths, the shaft, and the trees are an illustrated satellite of this demonstration layout, not a GPS survey.
        </p>
      </div>
      <aside className="pog-sheet">
        <h2>Stations</h2>
        <ul>
          {nodes.map((node) => (
            <li key={node.id}>
              <button
                type="button"
                aria-pressed={selected === node.id}
                onClick={() => {
                  onSelect(node.id);
                  setCard(node.id);
                }}
              >
                <b>{node.id}</b>
                <span>{node.place}</span>
                <Badge condition={node.condition} />
              </button>
            </li>
          ))}
        </ul>
        {chosen && (
          <div className="pog-detail">
            <h3>
              {chosen.name} <Badge condition={chosen.condition} />
            </h3>
            <p>{labels[chosen.condition] || chosen.condition}</p>
            <p>Last sample {timeLabel(chosen.latest?.sample_time)}</p>
            {readings(chosen).length ? (
              <ul>
                {readings(chosen).map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
            ) : (
              <p>No numeric reading in the latest sample.</p>
            )}
          </div>
        )}
      </aside>
    </section>
  );
}
