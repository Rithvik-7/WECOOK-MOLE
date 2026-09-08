# MOLE — software plan (zero → working demo)

**Last updated:** 9 September 2026  
**This file is the software build order.** AI behaviour and the operator website are frozen in `AI-PLAN.md`. Hardware pins and radios are frozen in `MOLE-CONTEXT.md` and `.cursor/rules/`. If an older README says the rover is optional, ignore that: the rover is in the demo, but **its radio stays off the node ESP-NOW/USB path**.

This repo currently has **firmware sketches and a local Python website**. Pitch/PPT and a rover wiring drawing do not replace flashing the four boards and running `--mode live`.

---

## What we are building

**PS:** SIH 2026 official ID **SIH26025** (Ministry of Coal, Hardware). ML on the laptop is a **required** slice, not polish after the rover.

One laptop program plus three Arduino sketches that together let a judge see:

1. Node A and Node B live on one dashboard.
2. A controlled tilt/vibration makes status go NORMAL → WATCH → ALERT, with a reason.
3. **Isolation Forest** flags “unusual vs trained normal” (separate from rules) — named model, score, top feature.
4. **Ridge** draws a **30 s sensor forecast** on the same charts (labelled: not a collapse prediction) + MAE. This is the PS *prediction* we actually ship.
5. The operator then drives the rover inside the model tunnel and sees inspection readings on the **same** local website (no camera).

Pitch order: **monitoring and evidence first**, then rover **because a warning appeared**.

```text
Node A / Node B  --ESP-NOW ch1-->  Waveshare ESP32-S3-Zero
                                         USB-C 115200 JSON
                                              |
                                              v
                                    Laptop Python
                              SQLite + rules + Isolation Forest
                                      Dashboard
                                              |
                              Wi-Fi AP Mine-Rover-AP (separate)
                                              |
                                              v
                                    Rover ESP32 + sensors
```

**ESP32 = measurement.**  
**Laptop = intelligence + storage + UI.**  
**Rover = inspection after an operator decision.**

---

## Repo layout to create

```text
MOLE/
├── firmware/
│   ├── node/node.ino              # one sketch; NODE_ID + HAS_POT
│   ├── receiver_s3/receiver_s3.ino
│   └── rover/rover.ino
└── software/
    ├── app.py                     # HTTP dashboard + APIs
    ├── serial_reader.py           # USB ingest from S3-Zero
    ├── rover_client.py            # laptop → rover AP proxy
    ├── models.py                  # packet / node / rover records
    ├── artifacts/                 # Isolation Forest joblib (gitignored)
    ├── database.py                # SQLite
    ├── calibration.py             # baseline + slider mm
    ├── rules.py                   # NORMAL / WATCH / ALERT / UNKNOWN
    ├── anomaly.py                 # Isolation Forest + joblib
    ├── forecast.py                # Ridge 30 s signal prediction
    ├── explain.py                 # template reasons from numbers
    ├── features.py                # tilt_change, rates, A-vs-B
    ├── simulate.py                # labelled fake packets for UI work
    ├── dashboard.html             # local website, no login
    ├── test_app.py
    ├── TELEMETRY.md
    └── requirements.txt
```

Arduino boards:

| Sketch | Board setting |
|---|---|
| `node.ino` A | ESP32 Dev Module, `NODE_ID 1`, `HAS_POT 1` |
| `node.ino` B | ESP32 Dev Module, `NODE_ID 2`, `HAS_POT 0` |
| `receiver_s3.ino` | **Waveshare ESP32-S3-Zero** (fallback ESP32S3 Dev Module), USB CDC On Boot **Enabled** |
| `rover.ino` | ESP32 Dev Module |

Libraries: Arduino `Wire`, `WiFi`, `esp_now`, `esp_wifi`, rover also `WebServer`. No third-party MPU library.

---

## Data contract (do not drift)

### Binary on air (Node A/B → receiver)

```cpp
struct SensorPacket {
    uint8_t version;     // 1
    uint8_t nodeId;      // 1 or 2
    uint32_t sequence;
    uint32_t uptimeMs;
    float roll;
    float pitch;
    float vibration;
    int16_t sliderRaw;   // Node B always -1
    uint8_t flags;       // bit0 IMU, bit1 slider, bit2 vibration window
};
```

Nodes sample the MPU faster (50–100 Hz), summarize ~1 s, then send **one** packet. `sequence++` after each send so the laptop can see gaps (100,101,102,105 → 103–104 lost).

### JSON on USB (receiver → laptop)

One object, then `\n`. 115200 baud. Python: `ser.readline()`.

Node A:

```json
{"type":"telemetry","schema":1,"node_id":1,"seq":225,"uptime_ms":17000,"valid":7,"roll_deg":2.14,"pitch_deg":1.32,"vibration_g":0.07,"adc_raw":1764}
```

Node B:

```json
{"type":"telemetry","schema":1,"node_id":2,"seq":194,"uptime_ms":19400,"valid":5,"roll_deg":0.12,"pitch_deg":0.07,"vibration_g":0.01,"adc_raw":null}
```

`valid`: IMU=1, potentiometer=2, vibration window=4. Healthy A=7, healthy B=5. Invalid fields are `null`, not `0`. Receiver may add `gateway_ms`. Receiver **does not** compute tilt-delta, millimetres, alerts, or AI.

### Laptop adds (never on the ESP32)

`received_at`, `delta_roll`, `delta_pitch`, `tilt_change`, `relative_mm`, fresh/stale, status, rule reason, anomaly score.

### Rover HTTP (laptop ↔ rover AP)

SSID `Mine-Rover-AP`, ESP32 AP IP `192.168.4.1`.

| Path | Job |
|---|---|
| `/forward` `/backward` `/left` `/right` `/stop` | Drive (L298N map frozen) |
| `/telemetry` | JSON: distance_cm, mq7_raw, ir_obstacle, roll/pitch/vibration, seq |

Rover `device_id` is `"rover"`, never `node_id` 1 or 2. Rover vibration is **never** treated as Node B. MQ-7 is **raw ADC + NORMAL/HIGH**, not ppm.

**Demo networking:** USB serial from the S3-Zero does not need Wi-Fi. For rover control, the laptop joins `Mine-Rover-AP` (or the dashboard proxies once the laptop is on that AP). Do not require venue Wi-Fi or cloud.

---

## Module jobs

| File | Does | Does not |
|---|---|---|
| `node.ino` | Wake MPU, roll/pitch, 1 s vibration RMS, optional ADC34, ESP-NOW send | Alerts, mm, AI |
| `receiver_s3.ino` | STA + channel 1, ESP-NOW RX, size/version check, JSON line to USB | Sensors, rules |
| `rover.ino` | AP + WebServer, L298N, HC-SR04, IR, MQ-7 raw, MPU | ESP-NOW, Isolation Forest |
| `serial_reader.py` | Open COM port, parse lines, drop junk | Guess missing nodes as healthy |
| `simulate.py` | Fake A/B packets for UI without hardware | Silent fallback in `--mode live` |
| `models.py` | Typed records, schema 1 only for nodes | Accept rover as node 1/2 |
| `calibration.py` | Capture baseline; two-point ADC→mm | Convert mm on the ESP32 |
| `rules.py` | Persistence, latch, ack, clear, stale→UNKNOWN | Let AI clear a rule alert |
| `anomaly.py` | Isolation Forest after enough live NORMAL samples | Train in simulate; claim collapse % |
| `database.py` | SQLite history + CSV export tagged live/sim | Cloud |
| `rover_client.py` | HTTP to 192.168.4.1, timeouts, last-seen | Mix into node freshness |
| `app.py` | One UI, `/api/state`, baseline/ack/clear/train, rover proxy | |

Starter rule numbers (tabletop, **not** mine trigger levels): WATCH 3° or 2 mm; ALERT 6° or 4 mm; 3 consecutive samples; stale after 5 s → UNKNOWN; ALERT latched; ack does not clear; clear needs 3 fresh NORMAL; Node B never cancels Node A.

Green = healthy data and no configured trigger. **Green is not a certified-safe mine.**

---

## Build order (this is the work)

Hardware can flash Hello World in parallel. Software does **not** wait for every sensor to be soldered: simulate mode unblocks the dashboard.

### Slice 0 — contracts and empty tree

Create the folders and `TELEMETRY.md`. Freeze JSON + `SensorPacket`. No features yet.

### Slice 1 — node firmware (serial first, radio second)

`node.ino` with `#define NODE_ID` / `HAS_POT`.

Bench via USB Serial before ESP-NOW:

1. MPU: ax ay az, roll, pitch.
2. Node A slider ADC moving.
3. Node B same MPU test, `sliderRaw = -1`.
4. Then ESP-NOW broadcast on channel 1, 1 Hz summary.

### Slice 2 — S3-Zero receiver

`WiFi.STA` → force channel 1 → `esp_now_init` → RX callback → JSON line.

Prove: Node A only, then A+B, then USB into a terminal at 115200. If upload fails: hold BOOT, reset, release BOOT. Native USB, not CH340.

### Slice 3 — laptop ingest + simulate (dashboard can start here)

`serial_reader.py` + `simulate.py` + SQLite store of raw packets.

```text
python app.py --mode simulate
python app.py --mode live --serial COMx
```

Live must **error** if the port is missing. Never quietly simulate.

### Slice 4 — validation, calibration, rules

Usable? recent? schema? duplicate seq? IMU valid?  
Then baseline. Then WATCH/ALERT/UNKNOWN. Tests before pretty UI.

Minimum tests (reuse the old 11-test intent):

- Latch / ack / clear
- Stale → UNKNOWN
- Duplicates do not refresh freshness
- Unseen node never green
- Missing crack scale blocks Node A NORMAL
- Bad schema / invalid sensor
- Simulate cannot train Isolation Forest

### Slice 5 — dashboard (nodes only)

One local HTTP page (`localhost`):

- Node A / Node B cards: readings, last update, connection
- Graphs: tilt, vibration, slider mm
- Status colour + **reason text**
- Buttons: set baseline, ack, clear recovered alert, export CSV
- Permanent **SIMULATED DATA** banner in simulate mode

Compare A vs B on the laptop: A moved and B quiet → local disturbance; both moved together → table/model/common motion. That comparison is **Python**, not firmware.

### Slice 6 — Isolation Forest + 30 s forecast

See `AI-PLAN.md`. Train only in **live** after ≥120 genuine NORMAL samples per node. Persist joblib. Block train during an active/latched warning. Show INACTIVE until ready. Ridge overlay next 30 s of tilt/vibration; MAE on a recent window; time-to-WATCH/ALERT only if slope is toward the threshold. UI sentence: not a collapse prediction. AI never clears a rule.

### Slice 7 — rover firmware + dashboard panel

Only after A/B live on the dashboard (hardware test order 1–9, then rover). **No camera.**

Drive map: STOP all 0; FWD 1,0,1,0; BACK 0,1,0,1; LEFT 0,1,1,0; RIGHT 1,0,0,1. If wheels invert, swap two motor wires or the map once — do not rewrite the project.

Rover Inspection is a **separate page**: hold-to-move FWD/REV/LEFT/RIGHT, large STOP, last telemetry, connection stale if `/telemetry` dies. HC-SR04 via divider; IR `LOW` = obstacle. Rover IMU is inspection-only.

### Slice 8 — working demo (acceptance path)

1. Both nodes green / NORMAL, graphs moving.
2. Tilt or open the Node A gap; show numbers change.
3. WATCH then ALERT + reason (and AI flag if trained).
4. Say: inspect with the rover **because** of that warning.
5. Drive in the tunnel; show distance / IR / MQ-7 raw / rover tilt.
6. Ack, then recover to NORMAL; history still has the event.

---

## What “done” looks like for the hackathon

| Must show | Not this week unless extra time |
|---|---|
| A+B JSON through S3-Zero USB | LoRa, mesh, cloud, login |
| Rules + explanations | Collapse / subsidence % |
| Isolation Forest + 30 s Ridge forecast (MAE) | Camera, vision, LLM chatbot |
| Rover on the same local website, separate radio | Autonomous navigation |
| SQLite + CSV | SMS, DGMS certification, CO ppm |

---

## Team split (software)

- **Firmware:** `node.ino`, `receiver_s3.ino` (S3 CDC is the sharp edge), then `rover.ino`
- **Backend:** serial, validate, calibrate, rules, SQLite, rover HTTP proxy
- **Frontend + AI check:** dashboard, demo scenarios, Isolation Forest verify, SIMULATED labelling

Hardware owners still do MPU/slider/motor wiring; software should not block on BOM.
