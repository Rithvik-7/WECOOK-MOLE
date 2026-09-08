# MOLE — AI + monitoring app plan

**Last updated:** 9 September 2026  
**Read this with** `SOFTWARE-PLAN.md` (firmware, USB, rover radio) **and** `MOLE-CONTEXT.md` (honesty rules). This file freezes **what the AI actually does** and **what the operator app shows**.

No camera. No login. No cloud. No ChatGPT overlay. Firmware, the Flask backend,
the Monitoring + AI page, and the separate Rover Inspection page are implemented.
Physical flashing and live-hardware validation remain.

---

## 1. What we are answering (analysis)

**Problem statement SIH26025** (SIH 2026 · Ministry of Coal · Hardware · Disaster Management). Official catalogue ID is **SIH26025**, not SIH2026025.

> AI-enabled low-cost **real-time** mine subsidence **monitoring**, **prediction**, and **early warning**.

**ML is a core product, not a side panel.** Isolation Forest + Ridge must ship, train on live NORMAL data, and be visible (features, score, MAE). Hardware-only or rover-only is not this PS.

| PS word | What we can honestly ship on a tabletop | What would be slop / a lie |
|---|---|---|
| Monitoring | Live Node A + Node B on one focused page, source-tagged, timed | Fake live feed, or rover IMU treated as Node B |
| Early warning | Rules: WATCH / ALERT after persistence; stale → UNKNOWN | Green badge that means “mine is safe” |
| AI-enabled | Isolation Forest on **this rig’s** normal samples | “AI powered” label with no model, or an LLM inventing geology |
| Prediction | **Next 30 s of the measured signals** + “if this rate holds, time-to-WATCH/ALERT” | Collapse probability, subsidence forecast, “roof will fail in 12 min” |
| Inspection | Rover drive + ultrasonic / IR / MQ-7 raw / rover tilt | Camera / vision (not in the build) |

Two different prediction claims (already in the project definition):

1. **Sensor-trend prediction** — we **build this**. Ridge regression on the last ~30 s of tilt / vibration / crack. Judges can see a dashed line and a checked error (MAE on a recent window).
2. **Mine-subsidence / collapse prediction** — we **do not claim**. That needs surveyed mounts, labelled events, and geotechnical validation. Pitch it as the **field path**, not as a demo output.

Isolation Forest alone is real AI, but the PS title says *prediction*. A short-horizon forecast of **the same numbers already on the chart** is the missing piece that still stays honest.

**Website vs phone app:** use a **local website on the laptop** (`http://127.0.0.1:5000`). The S3-Zero arrives over **USB**. A phone app cannot see that serial port. Flask + one HTML page, no npm build, no accounts. Browser on the same laptop is the app.

**Rover without camera:** inspection is distance, IR obstacle, MQ-7 **raw**, rover MPU. Operator still drives FWD/REV/LEFT/RIGHT/STOP. Driving is **not** an AI function.

---

## 2. What “not AI slop” means here

Build these, and show them on the panel:

- Named models (`IsolationForest`, `Ridge`) with **feature names on screen**
- Train count, train time, contamination / horizon
- **INACTIVE** until enough **live NORMAL** samples (or a joblib file trained on this same tabletop)
- Anomaly **score** + which feature was most unusual
- Forecast overlay + MAE
- Written reason built from **numbers**, not from a language model
- Rules column and AI column **side by side**; AI **cannot** clear a rule alert
- Simulate mode: banner **SIMULATED DATA**; **cannot** train; AI stays INACTIVE

Do **not** build: login, chatbot, purple “AI” watermarks, collapse %, CO ppm, vision, autonomous driving, TensorFlow, OpenAI, venue cloud.

Stack: Python 3, Flask, pyserial, sqlite3, numpy, scikit-learn, joblib, one `dashboard.html` + Chart.js from a local vendor file (or a simple canvas chart if you want zero CDN). Prefer **offline**.

---

## 3. Data the AI is allowed to see

Laptop first: drop junk, require schema 1, known `node_id`, non-decreasing seq (duplicates do not refresh), IMU/slider flags, calibration, freshness (5 s → UNKNOWN). **Then** features.

**Node A vector (per 1 Hz sample, after baseline):**

| Feature | Meaning |
|---|---|
| `tilt_change_deg` | `sqrt((roll-roll0)² + (pitch-pitch0)²)` |
| `vibration_g` | 1 s RMS residual from firmware |
| `relative_mm` | two-point ADC→mm; omit from IF until calibrated |
| `d_tilt` | 1 s difference of tilt_change (rate) |

**Node B vector:** `tilt_change_deg`, `vibration_g`, `d_tilt` (no mm).

**Joint (system) vector:** `abs(A_tilt - B_tilt)`, `abs(A_vib - B_vib)`. Used for “local vs whole-model motion”, not for mixing rover IMU.

Rover telemetry is **never** in Isolation Forest or the node forecast. It is inspection evidence only.

---

## 4. Three AI pieces (all on the laptop)

```text
USB JSON  →  validate  →  features
                 │
     ┌───────────┼────────────┐
     ▼           ▼            ▼
 Isolation    Ridge 30s     Template
 Forest       forecast      explanation
 (unusual     (prediction   (from numbers)
  vs normal)   of signals)
     │           │            │
     └───────────┴────────────┘
              dashboard
         (rules stay independent)
```

### A. Anomaly — Isolation Forest (scikit-learn)

- `StandardScaler` + `IsolationForest(n_estimators=100, contamination=0.05, random_state=0)`
- One model per node; optional third on joint residuals
- Train only **`--mode live`**, only samples that rules already called **NORMAL**, **≥120 per node** (~2 min at 1 Hz)
- Block train if WATCH/ALERT latched or node stale
- Persist `software/artifacts/node1.joblib` (scaler + forest + feature list + trained_at + n_samples)
- Output: `ai_state` INACTIVE | READY | UNUSUAL, `score` (decision_function or inverted so higher = more unusual), `top_feature`
- If the model file exists from a previous session on **this rig**, load it and show trained_at. Venue: collect 2 min of quiet tabletop **before** judges walk up.

### B. Prediction — Ridge, next 30 seconds of **signals**

For each of tilt_change (A), vibration (A), tilt_change (B), vibration (B), crack mm (A if calibrated):

- Fit `Ridge` on the last 30 accepted points (time index → value)
- Emit 30 future points for the chart (dashed)
- Rolling MAE vs the last 10 s after they arrive (“forecast error”)
- If slope > small epsilon: `seconds_to_watch` / `seconds_to_alert` = distance-to-threshold / slope, capped (e.g. 5 min) or `null` if slope is flat/away
- UI label **exactly**: `Sensor forecast (30 s). Not a collapse prediction.`

This is the SIH “prediction” **demonstrated** at the hackathon. Keep the field-scale subsidence model as spoken **next work**, not a number on the screen.

### C. Explanation — templates, not an LLM

Examples the code may emit only if the values exist:

- `Node A tilt change 4.2° for 8 s (WATCH). Node B 0.3°. Residual suggests local disturbance, not whole-table motion.`
- `Isolation Forest UNUSUAL on Node A (score 0.62). Largest deviation: vibration_g.`
- `30 s tilt forecast still rising; estimated 11 s to ALERT if this rate holds.`

Forbidden: “roof fall”, “blasting”, “subsidence of 10 cm”, “87% collapse risk”.

---

## 5. Early warning (rules — not ML)

Keep rule engine independent. AI may **add** UNUSUAL; it may not cancel WATCH/ALERT.

| Status | Tabletop meaning (not DGMS levels) |
|---|---|
| NORMAL | Fresh, valid, calibrated, below WATCH |
| WATCH | 3 consecutive samples ≥ 3° tilt or 2 mm crack |
| ALERT | 3 consecutive ≥ 6° or 4 mm; **latched** |
| UNKNOWN | Stale > 5 s, bad schema, uncalibrated A slider, unseen node |

Ack = operator saw it. Clear = three fresh NORMAL only. Node B never clears Node A.

**A vs B (Python):** A moved, B quiet → local. Both moved similarly → common (table/model). Show that sentence in the evidence panel.

---

## 6. The app (one local website)

```text
python software/app.py --mode live --serial COM5
python software/app.py --mode simulate
```

Open `http://127.0.0.1:5000`. No passwords. Poll `GET /api/state` ~2 Hz.

### Screen (single page)

1. **Top bar** — MOLE · LIVE or **SIMULATED DATA** · USB connected/missing · rover AP last-seen · time
2. **Three unit cards** — Node A, Node B, Rover (status colour, last packet age, main numbers)
3. **Charts** — tilt A vs B, vibration A vs B, crack mm; **dashed forecast**; WATCH/ALERT markers
4. **Evidence** — left: rule reason; right: AI state / score / top feature / forecast + MAE
5. **Rover pad** — hold FWD/REV/LEFT/RIGHT, large STOP, auto-STOP on mouseup/keyup; distance, IR, MQ-7 raw + NORMAL/HIGH, rover roll/pitch (labelled inspection-only)
6. **History** — events, ack, rover deploy, CSV export
7. **Operator actions** — capture baseline, slider two-point mm, train AI, ack, clear recovered

No camera panel. No user accounts.

### Networking at the venue

- Nodes: USB to laptop (works with Wi-Fi off)
- Rover: laptop joins `Mine-Rover-AP`; Flask proxies `/api/rover/*` → `http://192.168.4.1/...`
- Judges look at the **laptop browser**, not at 192.168.4.1 directly (so nodes and rover stay one UI)

Drive is momentary. If the page dies, firmware should stop after a short timeout (rover sketch: stop if no command for ~400 ms).

---

## 7. Files to add (AI-specific on top of SOFTWARE-PLAN)

```text
software/
  features.py       # tilt_change, rates, A-vs-B residual
  anomaly.py        # Isolation Forest + joblib
  forecast.py       # Ridge 30 s + MAE + time-to-threshold
  explain.py        # template sentences from structured fields
  app.py
  dashboard.html
  artifacts/        # *.joblib gitignored except a README
```

API extras:

- `POST /api/train` `{ "node_id": 1 }` — live + enough NORMAL only
- `GET /api/state` includes `ai`, `forecast`, `explanation`, `rover`
- `POST /api/rover/{forward,backward,left,right,stop}`
- `GET /api/rover/telemetry`

Tests to add beyond the original 11-test intent:

- Simulate cannot train
- Untrained → INACTIVE, never green-because-AI
- AI UNUSUAL does not clear a latched ALERT
- Forecast labelled; time-to-alert is null when slope ≤ 0
- Rover packet cannot update Node B features

---

## 8. Demo script (judges)

1. Quiet table. Both nodes NORMAL. If IF is READY, score near normal.
2. Capture baseline if not set. Optional: show 120/120 train.
3. Tilt Node A (or open slider). Charts move. WATCH then ALERT + **reason**.
4. Point at AI: UNUSUAL and/or rising 30 s dashed forecast. Say the on-screen sentence: not a collapse %.
5. Node B still quiet → local disturbance.
6. Drive rover in the tunnel **because of that warning**. Show distance / IR / MQ-7 raw. No camera.
7. Ack; restore the model; three NORMAL; history still has the event.

If radio fails: `--mode simulate` still shows the UI, with the banner, and AI **off**.

---

## 9. Build order (software now)

Hardware Hello-World can continue in parallel. App work does not wait.

0. Contracts + empty `software/` `firmware/`
1. `node.ino` / `receiver_s3.ino` (real JSON on USB)
2. Flask ingest + simulate + SQLite
3. Rules + calibration + tests
4. Dashboard: live numbers + charts (no AI yet, panel shows INACTIVE)
5. Isolation Forest + persist + evidence column
6. Ridge forecast overlay + MAE + time-to-threshold
7. `rover.ino` + proxy pad (no camera)
8. Full judge loop on real packets

---

## 10. Pitch lines (use these)

- “AI learned what *this* tabletop looks like when quiet. Isolation Forest flags unusual combinations.”
- “Prediction here is the **next 30 seconds of tilt and vibration**, checked with MAE. It is not a certified subsidence forecast.”
- “Early warning is the rule latch. AI cannot hide a rule alert.”
- “The rover inspects after the officer decides. It does not replace Node A or B.”
