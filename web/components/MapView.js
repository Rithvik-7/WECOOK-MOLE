"use client";
import { useEffect, useId, useRef, useState } from "react";
import { labels, value } from "../lib/format";
import { groundHeight, nodePoint, projectPoint, layoutLabels } from "../lib/map-geometry.mjs";
const colors = {
  normal: "#7dcea0",
  watch: "#e0b15a",
  movement: "#e15b55",
  gas: "#e07a3d",
  sensor_fault: "#7eb6d6",
  stale: "#8e9b9b",
  unavailable: "#8e9b9b",
};
const panelsGeometry = [
  [
    [266, 227],
    [488, 202],
    [524, 341],
    [294, 365],
  ],
  [
    [540, 188],
    [747, 176],
    [791, 302],
    [570, 329],
  ],
];
const trees = Array.from({ length: 36 }, (_, i) => [
  135 + (i % 9) * 84 + Math.sin(i * 9) * 22,
  i < 18 ? 135 + Math.floor(i / 9) * 28 : 433 + Math.floor((i - 18) / 9) * 32,
]);
export function MapView({
  nodes = [],
  selected,
  onSelect,
  mode = "2d",
  yaw = 0,
  zoom = 1,
  panels = true,
  network = true,
  coverage = true,
  resetKey = 0,
}) {
  const cut = mode === "3d",
    uid = useId().replaceAll(":", ""),
    drag = useRef(null),
    [pan, setPan] = useState({ x: 0, y: 0 }),
    [orbit, setOrbit] = useState(0),
    [dragging, setDragging] = useState(false);
  useEffect(() => {
    setPan({ x: 0, y: 0 });
    setOrbit(0);
  }, [resetKey]);
  const heading = (((cut ? yaw : 0) + orbit) % 360 + 360) % 360;
  const project = (x, y, z = 0) =>
    projectPoint(x, y, z, { cut, yaw: heading, zoom, pan });
  const ground = (x, y) => project(x, y, cut ? groundHeight(x, y) : 0);
  const path = (pts, close = false) =>
    pts
      .map((p, i) => `${i ? "L" : "M"}${p[0].toFixed(1)},${p[1].toFixed(1)}`)
      .join(" ") + (close ? "Z" : "");
  const labelPositions=layoutLabels(nodes.map(n=>{const [x,y]=ground(...nodePoint(n));return {id:n.id,x,y};}));
  const warned = new Set(
    nodes
      .filter((n) => ["movement", "gas", "watch"].includes(n.condition))
      .flatMap((n) => (n.id === "D" ? [1] : n.id === "C" ? [] : [0])),
  );
  const zone = (x, y, radius) =>
    Array.from({ length: 28 }, (_, i) => {
      const angle = (i / 28) * Math.PI * 2;
      return project(
        x + Math.cos(angle) * radius,
        y + Math.sin(angle) * radius * 0.72,
        0,
      );
    });
  const boundary = [
    [100, 110],
    [900, 110],
    [900, 510],
    [100, 510],
  ];
  const terrain = [];
  for (let y = 0; y < 14; y++)
    for (let x = 0; x < 24; x++) {
      const a = [100 + (x * 800) / 24, 110 + (y * 400) / 14],
        b = [a[0] + 800 / 24, a[1]],
        c = [b[0], a[1] + 400 / 14],
        d = [a[0], c[1]];
      for (const points of [
        [a, b, c],
        [a, c, d],
      ]) {
        const h = groundHeight(points[0][0], points[0][1]);
        terrain.push({
          points: points.map((p) => ground(...p)),
          fill: `hsl(${152 + h * 0.18} 19% ${12 + h * 0.075}%)`,
        });
      }
    }
  function down(e) {
    if (e.target.closest("[data-node]")) return;
    e.currentTarget.setPointerCapture(e.pointerId);
    drag.current = {
      x: e.clientX,
      y: e.clientY,
      pan,
      width: e.currentTarget.getBoundingClientRect().width,
      moved: false,
    };
    setDragging(true);
  }
  function move(e) {
    if (!drag.current) return;
    const d = drag.current;
    const dx = e.clientX - d.x,
      dy = e.clientY - d.y;
    if (Math.hypot(dx, dy) > 6) d.moved = true;
    if (!d.moved) return;
    setPan({
      x: Math.max(
        -230,
        Math.min(230, d.pan.x + ((e.clientX - d.x) * 1000) / d.width),
      ),
      y: Math.max(
        -150,
        Math.min(150, d.pan.y + ((e.clientY - d.y) * 1000) / d.width),
      ),
    });
  }
  function end() {
    const d = drag.current;
    drag.current = null;
    setDragging(false);
    if (d && !d.moved) setOrbit((angle) => (angle + 45) % 360);
  }
  return (
    <svg
      className={`mine-svg ${cut ? "is-cutaway" : ""} ${dragging ? "is-dragging" : ""}`}
      viewBox="0 0 1000 620"
      role="group"
      aria-label={
        cut
          ? "Schematic mine cutaway. Click empty terrain to rotate 45 degrees. Drag to pan."
          : "Terrain schematic. Click empty terrain to rotate 45 degrees. Drag to pan."
      }
      onPointerDown={down}
      onPointerMove={move}
      onPointerUp={end}
      onPointerCancel={end}
    >
      <defs>
        <pattern
          id={`${uid}-grid`}
          width="40"
          height="40"
          patternUnits="userSpaceOnUse"
        >
          <path
            d="M40 0H0V40"
            fill="none"
            stroke="#668078"
            strokeOpacity=".11"
          />
        </pattern>
        <clipPath id={`${uid}-clip`}>
          <rect x="0" y="0" width="1000" height="620" />
        </clipPath>
      </defs>
      <rect width="1000" height="620" fill="#0c1416" />
      <rect width="1000" height="620" fill={`url(#${uid}-grid)`} />
      <g clipPath={`url(#${uid}-clip)`}>
        {cut && (
          <g>
            <path
              d={path(
                boundary.map((p) => project(...p, -125)),
                true,
              )}
              fill="#090e11"
              stroke="#354348"
            />
            {[1, 2].map((side) => {
              const a = boundary[side],
                b = boundary[(side + 1) % 4];
              return (
                <g key={side}>
                  <path
                    d={path(
                      [
                        ground(...a),
                        ground(...b),
                        project(...b, -125),
                        project(...a, -125),
                      ],
                      true,
                    )}
                    fill={side === 1 ? "#3a332c" : "#243038"}
                    stroke="#53605a"
                    strokeOpacity=".45"
                  />
                  {[25, 50, 80, 110].map((depth) => (
                    <path
                      key={depth}
                      d={path([project(...a, -depth), project(...b, -depth)])}
                      stroke={depth === 80 ? "#e0b15a" : depth === 25 ? "#6d8f86" : "#4e5c62"}
                      strokeOpacity=".4"
                      strokeWidth={depth === 80 ? 4 : 1}
                    />
                  ))}
                </g>
              );
            })}
            <path
              d={path(
                [
                  [270, 350],
                  [500, 350],
                  [500, 265],
                  [760, 265],
                ].map((p) => project(...p, -70)),
              )}
              stroke="#9bd5c3"
              strokeWidth="5"
              fill="none"
              strokeLinecap="round"
            />
            <text
              x="155"
              y="519"
              fill="#8caaa0"
              fontSize="12"
              letterSpacing="2"
            >
              ILLUSTRATIVE STRATA / NOT SURVEYED DEPTH
            </text>
            {[
              ["SURFACE", 8],
              ["ROCK / OVERBURDEN", -28],
              ["GEOLOGICAL STRATA", -55],
              ["COAL SEAM", -80],
              ["PANEL / TUNNEL", -100],
            ].map(([label, depth]) => {
              const [x, y] = project(130, 180, depth);
              return (
                <text key={label} x={x} y={y} fill="#c5d4c8" fontSize="11" letterSpacing="1.4">
                  {label}
                </text>
              );
            })}
            {nodes
              .filter((n) => ["movement", "gas"].includes(n.condition))
              .map((n) => {
                const [sx, sy] = nodePoint(n);
                const top = ground(sx, sy);
                const seam = project(sx, sy, -80);
                return (
                  <g key={`link-${n.id}`}>
                    <path
                      d={path([top, seam])}
                      stroke={colors[n.condition]}
                      strokeWidth="1.4"
                      strokeDasharray="3 4"
                      fill="none"
                    />
                    <circle cx={seam[0]} cy={seam[1]} r="7" fill={colors[n.condition]} fillOpacity=".35" />
                    <text x={seam[0] + 12} y={seam[1]} fill="#f0d3c4" fontSize="11">
                      {n.condition === "movement"
                        ? "Potential affected zone based on detected movement"
                        : "Sensor evidence at this node — not a collapse location"}
                    </text>
                  </g>
                );
              })}
          </g>
        )}
        <g>
          {terrain.map((t, i) => (
            <path
              key={i}
              d={path(t.points, true)}
              fill={t.fill}
              stroke={t.fill}
              strokeWidth=".6"
            />
          ))}
        </g>
        {Array.from({ length: 23 }, (_, i) => (
          <path
            key={i}
            d={path(
              Array.from({ length: 65 }, (_, j) => {
                const x = 90 + j * 13;
                const y =
                  112 +
                  i * 18 +
                  Math.sin(x / 97 + i * 0.12) * 10 +
                  Math.sin(x / 193) * 18;
                return ground(x, y);
              }),
            )}
            fill="none"
            stroke="#8bad95"
            strokeOpacity={i % 4 === 0 ? ".26" : ".1"}
            strokeWidth={i % 4 === 0 ? 1.2 : 0.7}
          />
        ))}
        <path
          d={path(
            boundary.map((p) => ground(...p)),
            true,
          )}
          fill="none"
          stroke="#a5c1a6"
          strokeOpacity=".3"
        />
        <path
          d={path(
            [
              [100, 357],
              [242, 352],
              [386, 402],
              [548, 420],
              [689, 360],
              [900, 341],
            ].map((p) => ground(...p)),
          )}
          fill="none"
          stroke="#080f11"
          strokeWidth="13"
          strokeLinejoin="round"
        />
        <path
          d={path(
            [
              [100, 357],
              [242, 352],
              [386, 402],
              [548, 420],
              [689, 360],
              [900, 341],
            ].map((p) => ground(...p)),
          )}
          fill="none"
          stroke="#6b8478"
          strokeWidth="1.5"
          strokeDasharray="5 8"
        />
        {cut&&<g><path d={path([[220,510],[800,510]].map(p=>project(...p,-72)))} fill="none" stroke="#091517" strokeWidth="14" strokeLinecap="round"/><path d={path([[220,510],[800,510]].map(p=>project(...p,-72)))} fill="none" stroke="#87aea3" strokeWidth="1.4" strokeDasharray="6 6"/>{[340,580,730].map(x=><path key={x} d={path([project(x,510,-72),project(x,510,-105)])} stroke="#0b1517" strokeWidth="9" fill="none"/>)}</g>}
        <g opacity=".7">
          {trees.map(([x, y], i) => {
            const p = ground(x, y);
            return (
              <g key={i} transform={`translate(${p[0]} ${p[1]})`}>
                <ellipse rx="9" ry={cut ? 4 : 8} cy="3" fill="#091711" />
                <path
                  d={cut ? "M0-15-6 0H6ZM0-9-8 6H8Z" : "M0-8-7 4H7Z"}
                  fill="#446052"
                  stroke="#809c7b"
                  strokeOpacity=".24"
                  strokeWidth=".7"
                />
              </g>
            );
          })}
        </g>
        {panels &&
          panelsGeometry.map((poly, i) => (
            <g key={i}>
              <path
                d={path(
                  poly.map((p) => ground(...p)),
                  true,
                )}
                fill="#9cb38b"
                fillOpacity={warned.has(i) ? 0.16 : 0.045}
                stroke={warned.has(i) ? "#efc37e" : "#b9c9a3"}
                strokeOpacity={warned.has(i) ? 0.9 : 0.45}
                strokeDasharray="5 5"
              />
              <text
                x={ground(poly[3][0] + 15, poly[3][1] - 12)[0]}
                y={ground(poly[3][0] + 15, poly[3][1] - 12)[1]}
                fill="#a5b49c"
                fontSize="11"
                letterSpacing="2"
              >
                PANEL 0{i + 1}
              </text>
            </g>
          ))}
        {coverage &&
          nodes.map((n) => {
            const [x, y] = nodePoint(n);
            const alert = ["movement", "gas", "watch"].includes(n.condition);
            return (
              <path
                key={`zone-${n.id}`}
                d={path(zone(x, y, 78), true)}
                fill={colors[n.condition] || colors.unavailable}
                fillOpacity={alert ? 0.16 : 0.07}
                stroke={colors[n.condition] || colors.unavailable}
                strokeOpacity={alert ? 0.7 : 0.28}
                className={`coverage-field${alert ? " is-alert" : ""}`}
              />
            );
          })}
        {network && (
          <g>
            {nodes.map((n) => (
              <path
                key={n.id}
                d={path([ground(...nodePoint(n)), ground(530, 437)])}
                fill="none"
                stroke="#aac7bb"
                strokeOpacity=".36"
                strokeDasharray="4 7"
                className="radio-link"
              />
            ))}
            <g transform={`translate(${ground(530, 437).join(" ")})`}>
              <rect
                x="-8"
                y="-8"
                width="16"
                height="16"
                rx="4"
                fill="#162d2e"
                stroke="#a9cfc1"
              />
              <text x="18" y="5" fill="#9fb7ad" fontSize="11">
                R0 / RECEIVER
              </text>
            </g>
          </g>
        )}
        {!cut && (
          <g fill="#8ba095" fontSize="11" letterSpacing="2">
            <text x="140" y="93">
              NORTH WOODLAND
            </text>
            <text x="717" y="552">
              ACCESS ROAD
            </text>
          </g>
        )}
        {nodes.map((n) => {
          const [x, y] = ground(...nodePoint(n)),
            col = colors[n.condition] || colors.unavailable,
            active = n.id === selected,
            watch = n.condition === "watch",
            alert = ["movement", "gas"].includes(n.condition),
            lx = labelPositions[n.id].x, ly=labelPositions[n.id].y;
          return (
            <g
              key={n.id}
              data-node={n.id}
              className={`map-marker ${active ? "is-selected" : ""}`}
              role="button"
              tabIndex="0"
              aria-label={`${n.name}, ${labels[n.condition] || n.condition}, ${value(n.latest?.tilt_deg, 2)} degrees tilt`}
              aria-pressed={active}
              onClick={() => onSelect(n.id)}
              onKeyDown={(e) => {
                if (["Enter", " "].includes(e.key)) {
                  e.preventDefault();
                  onSelect(n.id);
                }
              }}
              style={{ "--node-color": col }}
            >
              <circle cx={x} cy={y} r="28" fill="transparent" />
              {(alert || watch) && (
                <circle
                  className={`signal-ring${watch ? " is-watch" : ""}`}
                  cx={x}
                  cy={y}
                  r="29"
                  fill="none"
                  stroke={col}
                  strokeOpacity=".45"
                />
              )}
              <path
                d={`M${x - 13} ${y}h5M${x + 8} ${y}h5M${x} ${y - 13}v5M${x} ${y + 8}v5`}
                stroke={col}
                strokeWidth="1.1"
                fill="none"
              />
              {active && (
                <circle
                  cx={x}
                  cy={y}
                  r="25"
                  fill={col}
                  fillOpacity=".07"
                  stroke={col}
                  strokeOpacity=".6"
                  strokeDasharray="3 4"
                />
              )}
              <circle
                cx={x}
                cy={y}
                r="15"
                fill="#142022"
                stroke={col}
                strokeWidth="1.8"
              />
              <circle cx={x} cy={y} r="5" fill={col} />
              <path d={`M${x} ${y}L${lx+(lx<x?133:0)} ${ly+28}`} stroke={col} strokeWidth=".7" strokeOpacity=".4"/>
              <g
                className="sensor-label"
                transform={`translate(${lx} ${ly})`}
              >
                <rect
                  width="133"
                  height="57"
                  rx="11"
                  fill="#142025"
                  fillOpacity=".95"
                  stroke={active ? col : "#43554f"}
                  strokeOpacity={active ? ".8" : ".8"}
                />
                <text
                  x="11"
                  y="18"
                  fill="#dce8e0"
                  fontSize="11"
                  fontWeight="600"
                >
                  NODE {n.id}
                  <tspan x="120" textAnchor="end" fill={col}>
                    {value(n.latest?.tilt_deg, 2)}°
                  </tspan>
                </text>
                <text x="11" y="39" fill={col} fontSize="11">
                  {labels[n.condition] || "Unavailable"}
                </text>
              </g>
            </g>
          );
        })}
      </g>
      {coverage && (
      <g fill="#9eb4aa" fontSize="11" letterSpacing="1.5">
        <text x="24" y="28">360° MONITORING COVERAGE</text>
        <text x="24" y="44" fill="#7f948c" fontSize="10" letterSpacing="0.4">
          Schematic zone around each node. Not a physical 360° measurement.
        </text>
      </g>
      )}
      <g
        transform={`translate(928 86) rotate(${heading})`}
        fill="#a9bcb1"
        aria-label="Compass"
      >
        <circle r="16" fill="#10181c" fillOpacity=".72" stroke="#6b8982" strokeWidth="1" />
        <path d="M0-22-4.5 0 0-3 4.5 0Z" fill="#e0b15a" />
        <path d="M22 0 0-4.5 3 0 0 4.5Z" fill="#8fd0d6" />
        <path d="M0 22 4.5 0 0 3-4.5 0Z" fill="#8e9b9b" />
        <path d="M-22 0 0 4.5-3 0 0-4.5Z" fill="#8e9b9b" />
        <path d="M12-12 8-8M12 12 8 8M-12 12-8 8M-12-12-8-8" stroke="#6b8982" strokeWidth="1.2" fill="none" />
        <text x="0" y="-28" textAnchor="middle" fontSize="11" fill="#e0b15a">N</text>
        <text x="30" y="4" textAnchor="middle" fontSize="10">E</text>
        <text x="0" y="36" textAnchor="middle" fontSize="10">S</text>
        <text x="-30" y="4" textAnchor="middle" fontSize="10">W</text>
      </g>
      <g fill="#6b8982" fontSize="10" letterSpacing="1.2">
        <text x="24" y="560">SCHEMATIC SCALE — NOT SURVEYED</text>
        <path d="M24 568H94" stroke="#6b8982" strokeWidth="1.2" />
        <text x="24" y="585">
          {cut ? "STRATA VIEW" : "SURFACE VIEW"} / SCHEMATIC
        </text>
        <text x="970" y="585" textAnchor="end">
          {Math.round(heading)}° · CLICK TERRAIN TO TURN
        </text>
      </g>
    </svg>
  );
}
