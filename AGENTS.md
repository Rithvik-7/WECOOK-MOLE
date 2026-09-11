# AGENTS.md — complete A–Z handoff for MOLE

**Read this file first** before changing firmware, pins, ML, dashboard copy, or the pitch.

This document is for future coding agents and teammates. It is the current as-built contract as of **9 September 2026**. If a README, old drawing, or chat summary disagrees with this file plus `.cursor/rules/`, **this file and the cursor rules win**.

---

## 0. Identity (hackathon)

| Field | Value |
|---|---|
| Project name | **MOLE** — Mine Observation & Live-alert Engine |
| Team | **WE COOK** (GitHub repo name: **WECOOK-MOLE**) |
| Event | **Smart India Hackathon 2026** |
| Official PS ID | **SIH26025** |
| That means | SIH 2026 problem **025** |
| Ministry | **Ministry of Coal** |
| Category | **Hardware** |
| Theme | **Disaster Management** |
| Portal / 6-slide template ID | Write **SIH26025** only |
| Never write | `SIH2026025`, “optional rover”, “AI chatbot”, collapse % |

Problem intent (honest product): **AI-enabled, low-cost, real-time mine subsidence monitoring, prediction, and early warning** — demonstrated on a **tabletop model**, not a certified mine.

MOLE is **one** system: **Node A + Node B + laptop ML + Rover + one local dashboard**. The rover is not optional. ML is not optional. Do not pitch sensors-plus-a-rover with a decorative “AI” badge. Do not pitch a gas-car maze robot.

Pitch order: **continuous monitoring and evidence first**, then drive the rover **because a warning appeared**.

---

## 1. What we actually built (one paragraph)

Four ESP32-class boards plus a laptop. Two **fixed** nodes measure tilt, vibration, and (on A only) a crack slider, and send summarized ESP-NOW packets. A **Waveshare ESP32-S3-Zero** receives those packets and prints JSON over USB-C. The laptop Flask site stores packets, runs **tabletop rules**, **Isolation Forest + LOF**, a **joint A–B Isolation Forest**, and a **holdout-selected 30 s sensor-trend forecast**. A **separate rover page** proxies hold-to-move drive commands to a rover Wi-Fi AP and shows ultrasonic distance, an IR digital flag, MQ-7 raw ADC, and rover IMU. Simulation mode works with no hardware. Live mode never silently fakes data.

---

## 2. Non-negotiable honesty rules

Measurements can indicate **disturbance**. They do **not** prove a collapse or name its cause.

| Allowed | Forbidden |
|---|---|
| NORMAL / WATCH / ALERT / UNKNOWN on **this rig** | “Mine is safe / certified / collapse imminent” |
| Isolation Forest score + top feature vs **this tabletop’s normal** | Collapse or subsidence **probability** |
| 30 s forecast of **tilt / vibration / crack mm** + MAE | “Roof will fail in N minutes” as a geotech claim |
| MQ-7 **raw ADC** + local NORMAL/HIGH | CO **ppm** from an uncalibrated MQ-7 |
| IR **digital flag** (LOW = near) | Collision avoidance / lidar / auto-brake |
| Remote FWD/REV/LEFT/RIGHT/STOP | Autonomous navigation |
| Operator-driven inspection | Camera / vision / LLM / login / cloud / LoRa |

- **Green / NORMAL** = fresh valid data and no configured tabletop trigger. It does **not** certify a mine.
- **Rules latch.** Isolation Forest **cannot** clear a rule alert. Ack records awareness; it does not erase history.
- Forecast UI must say it is **not a collapse prediction**.
- Rover vibration is **never** Node B and **never** enters node ML features.
- Live USB path does **not** carry rover commands or video.

---

## 3. Hardware — complete inventory

The team already has the parts. **Do not invent a different board, pin, or radio.** Do not block on budget or the old ₹4,000 node-only figure.

### 3.1 Units

| Unit | MCU | Job | Radio |
|---|---|---|---|
| **Node A** | Classic **ESP32-WROOM-32** DevKit | Tilt + vibration + crack slider | ESP-NOW ch **1** broadcast |
| **Node B** | Same DevKit | Comparison tilt + vibration, **no slider** | ESP-NOW ch **1** broadcast |
| **Receiver** | **Waveshare ESP32-S3-Zero** (ESP32-S3FH4R2) | ESP-NOW → USB-C JSON 115200 | STA, channel 1. **No sensors** |
| **Rover** | Classic **ESP32-WROOM-32** DevKit | Drive + inspect | Wi-Fi AP `Mine-Rover-AP` **only** |

Receiver is **not** a classic ESP32 and **not** ESP32-S2. Arduino: `Waveshare ESP32-S3-Zero` **or** `ESP32S3 Dev Module`, **USB CDC On Boot = Enabled**. Native USB, not CH340.

### 3.2 Node A / Node B pins

Same sketch family: `firmware/node/node.ino` (A) and `firmware/node_b/node.ino` (B).

| Function | Pin / note |
|---|---|
| MPU6050 I²C | SDA **GPIO21**, SCL **GPIO22**, addr **0x68**, **3V3**, AD0 to GND |
| Node A slider | 10 kΩ linear pot SIG → **1 kΩ** → **GPIO34** (ADC1). Never 5 V into ADC |
| Node B slider | **Not fitted.** `sliderRaw = -1`, `HAS_POT 0` |
| `#define` | A: `NODE_ID 1`, `HAS_POT 1`. B: `NODE_ID 2`, `HAS_POT 0` |

Firmware samples MPU ~80 Hz (`SAMPLE_US 12500`), summarizes **~1 packet/s**, broadcasts `FF:FF:FF:FF:FF:FF` on **channel 1**. Sequence increments after each send. Firmware does **not** compute millimetres, alerts, or AI.

`valid` bitmask (USB JSON `valid` field): IMU=1, potentiometer=2, vibration window=4. Healthy A=**7**, healthy B=**5**. Invalid fields are JSON `null`, never `0`.

### 3.3 Receiver

Sketch: `firmware/receiver_s3/receiver_s3.ino`.

- Wi-Fi STA, force channel 1, ESP-NOW RX, size/version/node_id check.
- Prints **one JSON object per line** on USB Serial **115200**.
- May add `gateway_ms`. Does not compute tilt-delta, mm, rules, or AI.
- Upload hint: hold BOOT, tap RESET, release BOOT, then upload.

### 3.4 Rover pins (frozen)

Sketch: `firmware/rover/rover.ino`. AP SSID **`Mine-Rover-AP`**, IP **`192.168.4.1`**. No password in firmware (open AP).

| Function | Pin |
|---|---|
| L298N IN1 (left) | **GPIO13** |
| L298N IN2 (left) | **GPIO12** |
| L298N IN3 (right) | **GPIO14** |
| L298N IN4 (right) | **GPIO27** |
| MPU6050 | SDA **21** / SCL **22** / 0x68 / 3V3 |
| HC-SR04 TRIG | **GPIO5** |
| HC-SR04 ECHO | **GPIO18** **after 1 kΩ / 2 kΩ divider** (ECHO is 5 V — never wire straight in) |
| MQ-7 analog | **GPIO36** raw 12-bit ADC. Threshold `MQ7_HIGH_RAW 2500` → local HIGH. **Not ppm** |
| IR OUT | **GPIO19**, `INPUT_PULLUP`, **LOW = obstacle**. Majority-of-3 debounce. **Does not stop motors** |

**Leave L298N ENA/ENB jumpers ON.** Firmware stops by setting IN1–IN4 LOW, plus a **400 ms** drive watchdog if no repeated command.

Drive map:

| Command | IN1 IN2 IN3 IN4 |
|---|---|
| STOP | 0 0 0 0 |
| FWD | 1 0 1 0 |
| REV | 0 1 0 1 |
| LEFT | 0 1 1 0 |
| RIGHT | 1 0 0 1 |

If a side runs backward, swap **that motor’s two wires**. Do not invent new GPIOs.

HTTP on the rover (GET): `/forward` `/backward` `/left` `/right` `/stop` `/telemetry` `/`.

**GPIO19 is IR, not a motor pin.** Older drawings that put GPIO19 on L298N IN4 are **wrong**. Regenerator: `hardware/draw_rover_circuit.py` → `hardware/rover-circuit.png`.

### 3.5 Split of intelligence

**ESP32 measures and sends. Laptop calibrates, compares A vs B, stores, rules, ML, UI. Rover driving is remote, not autonomous.**

Node path and rover path **must stay separate**. Laptop must join `Mine-Rover-AP` to drive. S3-Zero USB does not carry rover traffic.

### 3.6 Hardware status (as of this handoff)

Firmware **exists in repo but was not necessarily flashed** on the team’s boards. Physical jobs still required:

1. Wire per frozen pin map (especially echo divider and GPIO19 = IR).
2. Flash four sketches (Arduino IDE).
3. Serial Monitor on S3-Zero: JSON for `node_id` 1 and 2 at 115200.
4. `python app.py --mode live --serial auto` (or `COMx`).
5. Baseline A/B + slider two-point cal.
6. Join `Mine-Rover-AP`, raise wheels, polarity test, STOP watchdog, IR/ultrasonic sanity.

---

## 4. Software — complete inventory

Stack: **Python 3 + Flask** (no accounts, no npm, no CDN required). sklearn on the **laptop only**. SQLite. Canvas charts (no Chart.js CDN).

### 4.1 How to run

```powershell
cd software
python -m pip install -r requirements.txt
python app.py --mode simulate
python app.py --mode live --serial auto
python app.py --mode live --serial COM5
python -m pytest -q
```

Pages:

- Monitoring + AI: `http://127.0.0.1:5000/monitoring` (also `/`)
- Rover Inspection: `http://127.0.0.1:5000/rover`

Simulate is **permanently labelled**. It **cannot** persist-train Isolation Forest (`POST /api/train` blocked). **Tabletop prior** `.prior.joblib` files **do** load so IF is READY without waiting 120 samples. Priors are **synthetic quiet-tabletop NORMAL**, not a real mine. Label in UI: “Tabletop prior”.

Live **never** falls back to simulation. USB drop → retry every 2 s; nodes go UNKNOWN after **5 s** without a valid packet.

DBs (gitignored): `software/mole-sim.db`, `software/mole.db`.

### 4.2 Dependencies (`software/requirements.txt`)

Flask≥3, pyserial≥3.5, requests≥2.31, numpy≥1.26, scikit-learn≥1.4, joblib≥1.3, pytest≥8.

Arduino: `Wire`, `WiFi`, `esp_now`, `esp_wifi`, rover also `WebServer`. **No third-party MPU library.**

### 4.3 Python modules (what each file is for)

| File | Responsibility |
|---|---|
| `app.py` | Flask app, USB thread, rover poll thread, all HTTP routes |
| `engine.py` | RLock, ingest, freshness, baselines, snapshot JSON, forecast cache |
| `models.py` | `Telemetry` / `RoverTelemetry`, schema 1 parse |
| `serial_reader.py` | COM port, `readline` JSON, `resolve_port` / `auto` |
| `simulate.py` | Node scenarios + `SimulatedRover` |
| `database.py` | SQLite packets/events, CSV export tagged live/sim |
| `calibration.py` | Two-point ADC→mm; orientation baseline lives on the engine |
| `rules.py` | WATCH/ALERT/UNKNOWN, persist 3, latch, ack ≠ clear |
| `features.py` | Node vectors + joint residual vector |
| `anomaly.py` | Per-node Isolation Forest + LOF; prior/live joblib |
| `forecast.py` | Ridge / Huber / LinearRegression vs persistence; 30-point horizon |
| `explain.py` | Template reasons from numbers (not an LLM) |
| `rover_client.py` | HTTP to `http://192.168.4.1` |
| `rover_sense.py` | Honest IR vs ultrasonic copy (`stops_motors: false`) |
| `train_prior.py` | Generates shipped `*.prior.joblib` |
| `test_app.py` / `test_complete.py` | Contract tests (25 passing at last run) |

UI:

| File | Page |
|---|---|
| `dashboard.html` + `assets/monitoring.js` | Monitoring + AI |
| `rover.html` + `assets/rover.js` | Rover only |
| `assets/common.js` | fetch helpers, badges, toasts |
| `assets/charts.js` | canvas forecast chart |
| `assets/ui.css` | light paper theme |

Artifacts:

| File | Git |
|---|---|
| `artifacts/node1.prior.joblib` | **tracked** |
| `artifacts/node2.prior.joblib` | **tracked** |
| `artifacts/joint.prior.joblib` | **tracked** |
| `artifacts/node1.joblib` / `node2.joblib` | **gitignored** live retrains |

`.gitignore` ignores `*.joblib` then un-ignores `*.prior.joblib`.

### 4.4 HTTP API

| Method | Path | Notes |
|---|---|---|
| GET | `/` `/monitoring` | `dashboard.html` |
| GET | `/rover` | `rover.html` |
| GET | `/assets/<file>` | static |
| GET | `/api/state` | full monitoring snapshot |
| GET | `/api/export.csv` | history |
| POST | `/api/baseline` | `{node_id: 1\|2}` |
| POST | `/api/ack` | awareness only |
| POST | `/api/clear` | needs 3 recovered NORMAL; 409 if not |
| POST | `/api/inspection-done` | operator closed rover inspect; clears recovered latches on A and B; history kept |
| POST | `/api/train` | live only; ≥120 NORMAL; blocked if WATCH/ALERT/UNKNOWN/sim |
| POST | `/api/calibration` | `adc0,adc1,mm0,mm1` distinct ADC |
| POST | `/api/scenario` | simulate only: `normal rising watch alert offline sensor_fault` |
| POST | `/api/rover/<cmd>` | `forward backward left right stop` |
| GET | `/api/rover/state` | rover telemetry + `data.ir` explanation |

### 4.5 Rules (tabletop demo numbers — not mine trigger levels)

Defined in `software/rules.py`:

- WATCH: tilt **≥ 3°** or crack **≥ 2 mm**, **3** consecutive samples
- ALERT: tilt **≥ 6°** or crack **≥ 4 mm**, **3** consecutive samples
- UNKNOWN: stale **> 5 s**, unseen, invalid IMU, Node A uncalibrated slider
- ALERT **latches**
- Ack ≠ clear
- Clear needs **3** fresh NORMAL samples
- Node B never cancels Node A

Node A cannot show NORMAL until the slider is millimetre-calibrated.

Tilt change: `sqrt((roll-roll0)² + (pitch-pitch0)²)` after operator baseline.

### 4.6 ML (core product, laptop only)

**Anomaly (per node):** sklearn `IsolationForest` (contamination 0.05) + `LocalOutlierFactor`, `StandardScaler`. Features: `tilt_change_deg`, `vibration_g`, `d_tilt`, and Node A `relative_mm` once calibrated. States: INACTIVE / READY / UNUSUAL. Show score, LOF vote, top standardized feature, feature names, train count. Optional live retrain writes `nodeN.joblib` and overrides prior until reset.

**Joint:** Isolation Forest on `[abs(A_tilt-B_tilt), abs(A_vib-B_vib)]` for local vs common motion. Patterns such as QUIET / LOCAL_A / LOCAL_B / COMMON. Not a geology model.

**Forecast:** last ~30 s at 1 Hz. Candidates Ridge / HuberRegressor / LinearRegression vs persistence; **holdout MAE** picks the winner. Predicts next **30** samples of tilt, vibration, Node A gap. UI: solid measured, dashed forecast, error band, MAE, quality, surprise z, time-to-WATCH/ALERT **only if fitted slope heads toward the threshold**. Cache predictions until the series changes (`engine.py`). Quiet data can let LinearRegression win with MAE ≈ 0 — that is a **flat signal**, not magic. Huber may fail to converge; it is a candidate, not sacred.

**Priors:** `python software/train_prior.py` (from `software/`). They describe **quiet tabletop**, not the team’s physical MPU. After real baseline, scores may be noisy until optional live retrain.

**Not in ML:** rover IMU, IR, ultrasonic, MQ-7, camera, LLM.

### 4.7 IR interpretation (dashboard)

`rover_sense.explain_ir`:

- Pin 19, active LOW, **not range**, **does not stop motors**
- `agree_near` / `ir_only` / `sonar_only` / `clear`
- Simulate trips IR under ~**12 cm** while ultrasonic “tight” is **25 cm**, so they can disagree
- Live pins are **independent**

Do not add auto-stop on IR (that would be autonomy).

### 4.8 Operator UI behaviour

- Two pages on purpose. Drive controls **must not** appear on monitoring.
- Simulate: top **Rehearsal** bar (`#rehearsalBar`). Rising trend = Node A climbs, Node B quiet (judge-friendly forecast demo).
- Hero metric on node cards: **tilt from baseline**.
- Train A/B buttons **disabled** in simulate.
- Rover: hold-to-move, release/Space STOP, laptop sends STOP twice to beat in-flight races; firmware also stops after 400 ms.

### 4.9 Binary ESP-NOW packet (do not drift)

```cpp
struct __attribute__((packed)) SensorPacket {
    uint8_t version;     // 1
    uint8_t nodeId;      // 1 or 2
    uint32_t sequence;
    uint32_t uptimeMs;
    float roll;
    float pitch;
    float vibration;
    int16_t sliderRaw;   // Node B always -1
    uint8_t flags;       // IMU=1, POT=2, VIB=4
};
```

USB example Node A:

```json
{"type":"telemetry","schema":1,"node_id":1,"seq":17,"uptime_ms":17000,"gateway_ms":18500,"valid":7,"roll_deg":0.12,"pitch_deg":-0.08,"vibration_g":0.004,"adc_raw":2048}
```

More examples: `software/TELEMETRY.md`.

---

## 5. Repo map

```text
WECOOK-MOLE/
├── AGENTS.md                 ← this file (future agents start here)
├── README.md                 ← how to run + flash
├── MOLE-CONTEXT.md           ← product / honesty long form
├── SOFTWARE-PLAN.md          ← software build order
├── AI-PLAN.md                ← ML + UI freeze (priors now override “INACTIVE in sim”)
├── firmware/
│   ├── README.md
│   ├── node/node.ino         ← Node A
│   ├── node_b/node.ino       ← Node B
│   ├── receiver_s3/receiver_s3.ino
│   └── rover/rover.ino
├── software/                 ← Flask app (see §4)
├── hardware/draw_rover_circuit.py
├── pitch/                    ← SIH idea PPT sources
├── ppt/                      ← PPT builders
├── tools/                    ← PPT verification helpers
└── .cursor/rules/            ← always-on project + hardware freeze
```

Cursor rules (always apply): `.cursor/rules/mole-project.mdc`, `mole-hardware.mdc`. Software globs: `mole-software.mdc`.

---

## 6. Judge demo script

1. Simulate or live: both nodes updating; show **SIH26025** story: monitor → warn → inspect.
2. Show model names, train count / prior label, features, forecast MAE. Say it is **not** collapse %.
3. Rehearsal **Rising trend**, or physically tilt Node A. Node B stays quieter → localized evidence.
4. WATCH → ALERT with the **measured reason**. Rules and ML side by side.
5. Open **Rover Inspection because a warning appeared**.
6. Hold FWD (wheels raised first), STOP, show cm + IR flag + MQ-7 raw. IR does not auto-brake.
7. Recover mounts; **Inspection done** (or Ack + Clear after three NORMAL); history still lists the event.

Pitch sentence:

> Isolation Forest + LOF flag unusual combinations versus this rig’s learned normal. A joint forest watches A vs B residual. Holdout-selected sklearn regression forecasts the next 30 seconds of those same signals with MAE. Rules remain the independent early-warning latch. The rover is remote inspection, not autonomy.

---

## 7. What is done vs leftover

**Done in software:** firmware sketches, Flask two-page site, rules, IF+LOF+joint, holdout forecast, priors, simulate scenarios, rover proxy + IR honesty, Inspection done, CSV, tests (~32), paper UI.

**Not done until hardware day:** flashing, COM port, ESP-NOW range, slider mechanics, motor polarity, echo divider on the real board, IR aiming/lighting, AP join on the demo laptop, live baseline/cal, optional live retrain.

SIH26025 is a **Hardware** PS. Extra sklearn does not replace working boards.

---

## 8. Change policy for future agents

1. **Do not change pins, board types, or radio paths** without an explicit human freeze update to this file and `mole-hardware.mdc`.
2. **Do not add** camera, LoRa, LLM, login, cloud, CO ppm, collapse %, autonomous drive, mixing rover IMU into node AI.
3. **Do not** let live mode simulate on USB failure.
4. **Do not** let ML clear a latched rule.
5. Prefer tests in `software/test_app.py` / `test_complete.py` for contract changes.
6. After UI changes, verify `/monitoring` and `/rover` (simulate is enough if boards are unplugged).
7. Official ID on slides/portal: **SIH26025** only.

If you need more narrative, read `MOLE-CONTEXT.md`, `SOFTWARE-PLAN.md`, and `AI-PLAN.md` **after** this file — and treat **shipped priors + two-page UI** as the current product if those plans still say “train in live only / AI INACTIVE in sim”.
