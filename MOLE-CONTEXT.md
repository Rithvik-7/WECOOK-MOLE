# MOLE — Portable Project Context

**How to use this file:** Paste or attach the entire document before asking any AI, teammate, or tool to work on MOLE. Do not summarise it first. This is the current project definition. If an older PDF, blueprint, starter README, or chat says something different, **this file wins.**

**Last updated:** 9 September 2026  
**Hackathon:** Smart India Hackathon 2026  
**Official PS ID:** **SIH26025** (Ministry of Coal · Hardware · Disaster Management)  
**PS title:** Development of an AI-enabled Low Cost Real Time Mine Subsidence Monitoring, Prediction and Early Warning System for Underground Coal Mines in India  
**Team size:** 6 (team name: WE COOK) · **CMRIT** (CMR Institute of Technology), not CMIT  
**Roster:** Rithvik (leader); Komala TG (shared AI/ML, backend, research, PPT); Venkatesh, Devika (ordered and managed all electronics, also backend); Pragati Karvi (frontend, backend, PPT, demo); Pallavi Samantha (research, website, basic electronics). All 2nd year **ISE**, **CMRIT**. See `docs/TEAM.md`.  
**Build type:** Hackathon hardware + **laptop ML** + software demonstration on a tabletop model mine  
**Parts status:** The team already has the components for Node A, Node B, the rover, and supporting gear (borrowed / jugaad). Do **not** block on budget, shopping lists, or the old ₹4,000 node-only figure.

**PS ID note:** SIH 2026 problem 025 is catalogued as **SIH26025**. Do not put `SIH2026025` on the official idea PPT or SIH portal. That string is year+025 concatenated; judges and the template match **SIH26025**.

**Hardware freeze (9 Sep):** Receiver is a **Waveshare ESP32-S3-Zero**, not the classic ESP32 used on Node A/B and not an ESP32-S2. Node A keeps the 10 kΩ linear slider. Rover payload and GPIOs are frozen. Rover radio stays **Wi-Fi AP**, separate from node ESP-NOW. Software build order lives in `SOFTWARE-PLAN.md`. AI + operator website: `AI-PLAN.md`. Firmware and the local two-page website are implemented; physical flashing and live hardware validation remain.

---

## 1. One-line definition

MOLE is an **ML-backed** tabletop mine-monitoring and inspection system: two fixed nodes stream live tilt/vibration/crack, the laptop runs **Isolation Forest + Ridge forecast** plus rule-based early warning, one dashboard shows the evidence, and a rover inspects after the officer decides.

**MOLE is one integrated project: Node A + Node B + ML (Isolation Forest + Ridge) + Rover + Dashboard.**  
Hardware without trained/visible ML does **not** answer SIH26025. ML without live nodes is a demo of charts, not the PS. The rover is **not** optional and **not** the product by itself.

**ML is a core product pillar, not garnish.** Judges must see named models, features, a score / MAE, and a written reason from numbers. A chatbot, purple “AI” watermark, or collapse-% slider is not that.

---

## 2. What problem we are solving

Underground mining can affect the ground above it. Changes may appear as ground tilting, cracks opening, or unusual vibration.

MOLE aims to help a **mine safety officer notice concerning changes, understand the available evidence, and inspect the affected area remotely.**

It combines two kinds of information:

- **Continuous monitoring:** Node A and Node B remain in fixed positions and collect readings.
- **Targeted inspection:** The rover moves through the model mine to investigate an area requiring attention.

The dashboard brings this together. AI helps identify unusual patterns.

**Critical distinction:** these measurements can indicate a disturbance. They do **not** automatically prove that a collapse will happen, and they do **not** tell us exactly what caused it.

---

## 3. The complete system

```text
 NODE A                         NODE B
 Classic ESP32                  Classic ESP32
 MPU6050 + 10k slider           MPU6050 (no slider)
    │                              │
    └──────── ESP-NOW CH 1 ────────┘
                    │
                    ▼
        WAVESHARE ESP32-S3-ZERO
              RECEIVER (no sensors)
                    │
               USB-C / 115200 JSON
                    │
                    ▼
                  LAPTOP  (this is where ML lives)
          Python + SQLite + rules
          Isolation Forest (anomaly) + Ridge 30 s (prediction)
                Dashboard
                    │
                    ▼
            OPERATOR DECISION
                    │
                    ▼
                 ROVER  (separate radio)
          Classic ESP32 + L298N + MPU + HC-SR04 + MQ-7 + IR
                Wi-Fi AP Mine-Rover-AP → 192.168.4.1
                    │
                    └──── inspection telemetry back to dashboard
```

**The nodes detect changes. ML + rules analyse the readings (this is the SIH “AI-enabled / prediction / early warning” layer). The dashboard explains them. The rover investigates.**

Pitch order for judges: lead with **continuous monitoring and evidence**, then drive the rover **because a warning appeared**. Do not pitch MOLE as a gas-car maze robot.

---

## 4. Hardware units

### Distinguish these carefully

- **Three main hardware units:** Node A, Node B, Rover.
- **Controller-board count** may be higher. A separate **Waveshare ESP32-S3-Zero** USB receiver is **supporting communication infrastructure**, not another monitoring node.
- Four boards: Node A (classic ESP32), Node B (classic ESP32), S3-Zero receiver, rover (classic ESP32).

### Node A — tilt and movement monitoring (fixed)

**Job:** Monitor whether its mounting surface changes orientation. If a flat board slowly tilts, Node A detects the change.

**Where:** On the surface of the miniature, above the model underground mine panel. For the demonstration, this portion of the surface can move slightly so the team can create a controlled disturbance.

**Information it can provide (depending on final sensor configuration):**

- Tilt in one direction
- Tilt in the other direction
- Change from its calibrated starting position
- Whether that change persists or returns to normal
- Sensor and communication status

**What the measurements mean:**

Useful: “Node A has tilted further than its normal starting position, and the change has continued across several readings.”

Not allowed: “The ground has sunk by 10 centimetres.”

Tilt measures **orientation**. Measuring actual vertical settlement needs a different arrangement.

**Crack measurement (frozen for this build):** Node A uses a 10 kΩ **linear** slide potentiometer, SIG through 1 kΩ to **GPIO34**, VCC 3V3, GND common. Optional 100 nF from GPIO34 to GND.

- One side attaches to the fixed part of the model.
- The other follows the moving part.
- Firmware sends raw ADC only. The laptop converts to approximate model-gap millimetres after two-point ruler calibration.
- It must be a guided physical linkage, not a free-turning knob.

**Existing starter firmware behaviour for Node A:** MPU6050 gravity-based roll/pitch, vibration RMS proxy, and raw ADC from the slider. Tilt change is computed as:

`sqrt((roll - roll0)^2 + (pitch - pitch0)^2)`

This is suitable only for small movements with fixed mounting. It is **not** vertical ground displacement.

### Node B — vibration monitoring (fixed)

**Job:** Monitor shaking and changes in vibration.

Complements Node A:

- Node A primarily answers: **“Has the surface tilted?”**
- Node B primarily answers: **“Has the vibration pattern changed?”**

**Where:** Another fixed surface location on the miniature, chosen so the demo can show:

- A disturbance near one monitored location
- A disturbance affecting the entire model

**Information it can provide (accelerometer-based):**

- Acceleration readings
- A calculated measure of vibration strength
- Short vibration peaks
- Repeated or sustained disturbances
- Sensor and communication status

**Why it matters:** A brief tap and a sustained disturbance can produce different patterns. Software can analyse duration and intensity.

**Do not claim** that one vibration sensor can reliably distinguish blasting, a roof failure, a passing vehicle, and an earthquake without suitable training data and validation.

**Hardware clarification:** An MPU6050 can provide acceleration useful for **both** tilt and vibration demonstrations. Both nodes may use the same sensor model while serving different primary roles. That does **not** make them “two identical things.” Placement and monitoring purpose differ.

Calling Node B a “reference” does **not** make it a scientifically stable surveyed reference point. That would require appropriate installation and surveying in a real deployment. In the starter it was labelled N2 / nearby reference. Prefer language: **disturbance / comparison location**.

**Existing starter firmware behaviour for Node B:** Same IMU family as Node A, **no** crack potentiometer. Healthy validity mask is 5 (IMU + vibration), not 7.

### Rover — mobile inspection unit (core hackathon hardware)

The rover is a **core part of MOLE** and part of this hackathon implementation. It gives a capability the stationary nodes do not have: it can **move to inspect another location**.

**Purpose:** Once monitoring identifies a concerning condition, the operator can use the rover to investigate inside the miniature tunnel. It can help answer:

- Is there an obstacle in the passage?
- Is the route blocked?
- What can be observed at the inspection location?
- Are its onboard sensors reporting an unusual condition?

**Basic hardware functions needed:**

- A controller
- Motors and wheels
- A suitable motor driver
- A power source
- Communication with the control interface
- An inspection sensor payload

**Movement controls (baseline):** Forward, Reverse, Left, Right, Stop.

**Remote operation is the current baseline.** Fully autonomous navigation has **not** been confirmed or demonstrated. The rover can be part of an AI-assisted workflow without pretending its driving is autonomous.

**Frozen rover payload (9 Sep):** MPU6050, HC-SR04 (ECHO via 1k/2k divider into GPIO18), MQ-7 analog raw on GPIO36, IR on GPIO19 (LOW = obstacle), L298N IN1–IN4 = 13/12/14/27. Control is Wi-Fi AP `Mine-Rover-AP` at `192.168.4.1` (`/forward /backward /left /right /stop /telemetry`).

| Rover capability | Information returned |
|---|---|
| Ultrasonic (HC-SR04) | Distance ahead (cm) |
| IR obstacle | Boolean obstacle flag |
| MQ-7 | **Raw ADC** and NORMAL/HIGH vs a tested threshold — not CO ppm until calibrated |
| MPU6050 | Roll / pitch / vibration proxy (inspection only; never merge into Node B) |
| Communication | AP connection status and last `/telemetry` update |

A camera is **not** in this freeze. A camera feed would not be AI vision anyway unless a vision model is actually implemented. Flame, DHT11, and LoRa stay out unless separately built.

**Relationship with the nodes:** The rover does **not** replace either node. While the rover investigates, the fixed nodes continue monitoring. The dashboard must distinguish:

- Surface monitoring data (Node A, Node B)
- Mobile inspection data (Rover)

A vibration reading from the moving rover must **never** be interpreted as vibration measured by a stationary surface node. Device identity on every reading is mandatory.

Rover operation for the hackathon is in the **safe tabletop model**. Real underground deployment would need appropriate equipment, approvals, and procedures.

**Important integration fact:** The node ESP-NOW USB receiver does **not** handle rover commands, inspection telemetry, or video. Rover communication is a **separate Wi-Fi AP** (`Mine-Rover-AP`). The laptop dashboard must talk to both: USB serial for nodes, HTTP to `192.168.4.1` for the rover.

### USB gateway / receiver (not a monitoring node)

**Board: Waveshare ESP32-S3-Zero** (ESP32-S3FH4R2, native USB-C, onboard antenna). Not the classic ESP32-WROOM-32 DevKit used on Node A/B/rover, and not an ESP32-S2.

- ESP-NOW from the fixed nodes (2.4 GHz **channel 1**, unencrypted broadcast `FF:FF:FF:FF:FF:FF`, local tabletop only)
- No MPU or other sensors on the receiver
- Arduino: `Waveshare ESP32-S3-Zero` or fallback `ESP32S3 Dev Module`; **USB CDC On Boot = Enabled**
- `Serial.begin(115200)`; laptop reads newline-delimited JSON
- If upload fails: hold BOOT, connect USB / press RESET, release BOOT, then upload

The receiver only: listen → check size/version → emit one JSON object per line. It does not run rules or AI.

**LoRa is not currently demonstrated.** Do not claim LoRa unless it is built and shown. The S3-Zero path does **not** carry rover commands or video.

---

## 5. What the software receives

Each reading should identify its **source** and its **time**.

| Source | Main inputs |
|---|---|
| Node A | Tilt (roll/pitch), vibration proxy, crack slider ADC |
| Node B | Tilt (roll/pitch), vibration proxy (comparison location) |
| Rover | Distance, IR obstacle, MQ-7 raw, rover IMU, AP status |
| All units | Device ID, timestamp or sequence, data-validity status |
| Operator | Acknowledgement, inspection request, rover movement commands |

---

## 6. What happens to those inputs

### Step 1 — Check whether the data is usable

Before analysing a reading:

- Did it arrive recently?
- Is the sensor reporting a fault?
- Is the value valid?
- Is this a duplicate packet?
- Has the required calibration been completed?

A disconnected sensor must **not** produce a reassuring green status.

### Step 2 — Compare with the starting baseline

Examples:

- Tilt change from the initial position
- Vibration strength compared with normal activity
- Crack-gap change, if that measurement is included

### Step 3 — Look at changes over time

A single unusual sample can be noise. Examine whether the condition:

- Persists
- Repeats
- Increases
- Appears at another node
- Returns to its previous range

### Step 4 — Warning rules and AI analysis

These serve different purposes:

- **Rules:** respond to defined conditions and persistent threshold crossings.
- **AI:** identifies patterns that differ from the learned baseline.

AI must **never** suppress or clear a rule-based alert.

### Step 5 — Present the result

The dashboard shows readings, status, reason, and history so the operator can decide what to do.

---

## 7. Exactly where ML fits (core, not optional)

**ML is a required product layer for SIH26025.** The PS is *AI-enabled monitoring, prediction, and early warning*. Hardware collects; **scikit-learn on the laptop** is how we honestly do AI-enabled + prediction. Rules do early-warning latch. The rover does not replace ML.

It does **not** need to control motors or invent geology. It **does** need to be trained, persisted, scored, and shown.

Hackathon ML is specified in `AI-PLAN.md`. Summary:

### A. Anomaly detection (Isolation Forest)

Learns this tabletop’s quiet behaviour. Flags unusual combinations of tilt change, vibration, optional crack mm, and A-vs-B residual. Persisted with joblib. Train only on live NORMAL samples (≥120/node). Output: INACTIVE / READY / UNUSUAL + score + top feature. **Not** a collapse probability.

### B. Combining evidence

Dashboard presents both nodes: e.g. “Movement increased at Node A while Node B stayed near baseline” (local) vs both moving together (common / table).

### C. Prediction — two different claims

1. **Sensor-trend prediction (built):** Ridge forecasts the **next 30 seconds** of the measured tilt/vibration/crack series, with MAE. Optional time-to-WATCH/ALERT **if the current rate holds**. On-screen label: not a collapse prediction.
2. **Mine subsidence or collapse prediction (not claimed):** needs surveyed mounts, labelled events, geotechnical validation. Spoken as field path only.

### D. Explanations

Template sentences from actual fields. **No LLM.** Must not invent an underground event.

### E. Rover

Remote drive + inspection sensors. **No camera, no vision model, no autonomous AI driving.** Rover samples do not train node models.

---

## 8. What the dashboard should show

The dashboard is the common interface for the entire project.

### Monitoring view

- Node A and Node B locations
- Current readings
- Connection and sensor health
- Last update time

### Graphs

- Tilt against time
- Vibration against time
- Crack movement against time, if included
- Markers showing when warnings occurred

### Status display

| Status | Meaning |
|---|---|
| Green / Normal | Healthy data with no current configured trigger |
| Orange / Watch | A condition requires attention |
| Red / Alert | A configured significant condition persists |
| Grey / Unknown | Missing, faulty or insufficient data |

**Green does not certify that a mine is safe.**

### AI and explanation view

- Whether the AI model is active
- Any anomaly indication
- Relevant measured changes
- The reason for a warning
- Clear separation between AI findings and rule-based alarms

### Rover inspection view (required for the integrated project)

- Rover movement controls (hold-to-move + STOP)
- Connection status
- Distance, IR, MQ-7 raw, rover IMU (inspection only)

**No camera view.** A camera is not in this build.

### Event history

- When an issue began
- Which unit reported it
- Whether the operator acknowledged it
- Inspection activity
- Recovery information

Acknowledging an alert must **not** erase the underlying event.

Starter demo thresholds (local, visible, **not** scientific mine trigger levels):

- WATCH: 3 degrees tilt or 2 mm crack
- ALERT: 6 degrees tilt or 4 mm crack
- Persistence: 3 consecutive samples (~3 seconds at 1 Hz)
- Stale / missing: UNKNOWN after 5 seconds
- ALERT is latched separately from current status
- Acknowledge records operator awareness; it does not clear
- Clear recovered alert requires three fresh NORMAL samples
- Node B never cancels Node A’s alert

Simulation must be permanently labelled **SIMULATED DATA**. Live mode must never silently fall back to simulation.

---

## 9. What the miniature demonstrates

The miniature is a **physical demonstration environment**, not a scientifically accurate recreation of a mine.

It includes:

- A surface area for Node A and Node B
- An underground tunnel visible through a cutaway
- Space for the rover to travel
- A controlled way to tilt or disturb part of the surface
- A movable gap if crack measurement remains in scope

**Demonstration sequence (acceptance path):**

1. Show normal monitoring.
2. Introduce controlled movement or vibration.
3. Show the readings changing.
4. Show the warning and supporting evidence.
5. Operate the rover inside the tunnel.
6. Show its inspection information.
7. Show the recorded event and recovery.

That demonstrates an integrated monitoring-and-inspection workflow.

---

## 10. Confirmed scope vs still open

### Confirmed

- Node A, Node B, Rover, AI analysis, shared dashboard, tabletop demo
- All three hardware units belong to the hackathon implementation (rover is **core**; its **radio is separate**)
- Receiver = **Waveshare ESP32-S3-Zero**, native USB CDC, ESP-NOW channel 1, JSON at 115200
- Node A slider (10 kΩ linear, GPIO34) is in the build
- Rover pins and payload: L298N 13/12/14/27, MPU 21/22, TRIG 5, ECHO 18 via divider, MQ-7 GPIO36 raw, IR GPIO19
- Rover control: Wi-Fi AP `Mine-Rover-AP` / `192.168.4.1`
- Six team members; parts already available; budget is **not** a blocking constraint
- Software is to be written in this repo from zero per `SOFTWARE-PLAN.md`

### Still needing care (do not silently over-claim)

- Camera (not in the frozen rover map)
- Autonomous driving (default: **no**)
- Calibrated MQ-7 ppm (default: raw + NORMAL/HIGH only)
- LoRa / field range
- How much live NORMAL data you actually collect for Isolation Forest before the pitch

**Owning a part does not mean it is a promised feature** until it is selected, wired, and shown. The 9 Sep freeze *is* that selection for slider, S3-Zero, and rover payload.

---

## 11. Current software evidence (as of 9 September 2026)

This git repo has firmware (`firmware/`) and a local dashboard (`software/`). An earlier **runnable starter** (two nodes + simulated dashboard, 11 tests) existed as a 6 Sep pack **outside this tree**; this tree now has its own implementation.

When that starter is ported or rewritten, it should still support:

- Two surface nodes: Node A (IMU + crack slider) and Node B (IMU, no pot)
- Waveshare ESP32-S3-Zero USB receiver (replace any classic-ESP32 `gateway.ino`)
- ESP-NOW for nodes, **not** LoRa
- Local Python HTTP dashboard (`python app.py --mode simulate` or `--mode live --serial COMx`)
- Packet validation, stale nodes, duplicate rejection, calibration, rule engine, latch/ack/clear
- Optional Isolation Forest after live baseline collection
- SQLite storage and CSV export tagged live vs simulate
- Then **extend** with rover AP proxy + rover panel (the old starter did not)

The laptop must **not** actuate a rover over the node USB path, send SMS, implement LoRa, predict mine collapse, or certify safety.

### Node telemetry JSON contract (schema 1)

Receiver sends one JSON object per line at 115200 baud. On air, nodes send the binary `SensorPacket` in `SOFTWARE-PLAN.md`; the S3-Zero translates to JSON.

Node A example:

```json
{"type":"telemetry","schema":1,"node_id":1,"seq":17,"uptime_ms":17000,"gateway_ms":18500,"valid":7,"roll_deg":0.12,"pitch_deg":-0.08,"vibration_g":0.004,"adc_raw":2048}
```

Node B example (no crack sensor):

```json
{"type":"telemetry","schema":1,"node_id":2,"seq":17,"uptime_ms":17000,"gateway_ms":18500,"valid":5,"roll_deg":0.03,"pitch_deg":0.06,"vibration_g":0.003,"adc_raw":null}
```

`valid` bitmask: IMU angles = 1, potentiometer ADC = 2, complete vibration window = 4. Healthy Node A = 7; healthy Node B = 5. Invalid fields are `null`. Laptop receipt time governs freshness. Receiver `type:"status"` lines are diagnostics, not measurements.

**`node_id` 1 and 2 are reserved.** Rover uses `device_id: "rover"` over HTTP, not this USB schema.

Local routes to implement:

- GET `/` dashboard
- GET `/api/state`
- GET `/api/export.csv`
- POST `/api/scenario` (simulation only: normal / watch / alert / offline / sensor_fault)
- POST `/api/baseline`, `/api/ack`, `/api/clear`, `/api/train` with `node_id`
- POST `/api/calibration` with `adc0`, `adc1`, `mm0`, `mm1`
- Rover proxy: POST `/api/rover/{forward,backward,left,right,stop}`, GET `/api/rover/telemetry`

No cloud. Server listens on localhost.

Firmware target: Node A/B/rover = classic ESP32-WROOM-32, Arduino ESP32 core; receiver = S3-Zero with USB CDC. Firmware should be compiled/flashed on the team's machines; do not pretend this environment has already flashed boards.

---

## 12. Node firmware measurement notes (starter)

- MPU6050: ±2 g accelerometer, ~1 Hz report of mean orientation and vibration proxy
- Firmware orientation proxies: `roll_deg = atan2(ay, az)` and `pitch_deg = atan2(-ax, sqrt(ay² + az²))`. Gravity-based; trustworthy only when the sensor is approximately stationary
- `vibration_g` is RMS residual of the three acceleration axes around their one-second mean. It is **not** a calibrated seismic measure
- Node A ADC: 12-bit, 11 dB attenuation, interior travel (raw roughly 100–3900 usable). Firmware does **not** convert ADC to millimetres; the laptop does after two-point ruler calibration
- Pins (classic ESP32): SDA GPIO21, SCL GPIO22, AD0 to GND (0x68), Node A slider wiper through 1 kΩ to **GPIO34 (ADC1, not ADC2)**. Never 5 V into ADC. Do not use ADC2 with Wi-Fi/ESP-NOW
- Broadcast ESP-NOW is unencrypted and has no application acknowledgement. Missing nodes become UNKNOWN/OFFLINE on the laptop. Do not claim guaranteed mine/field range
- MPU VCC is 3.3 V, not 5 V

### Frozen rover GPIOs (classic ESP32)

| Hardware | GPIO |
|---|---|
| L298N IN1 IN2 IN3 IN4 | 13, 12, 14, 27 |
| MPU SDA / SCL | 21 / 22 |
| HC-SR04 TRIG / ECHO | 5 / 18 (ECHO through 1k/2k divider) |
| MQ-7 AO | 36 |
| IR OUT | 19 (LOW = obstacle) |

Do not randomly reassign these. STOP = all IN low; FWD 1,0,1,0; BACK 0,1,0,1; LEFT 0,1,1,0; RIGHT 1,0,0,1. If wheels invert, swap motor wires or the map once.

---

## 13. Honesty rules — never claim these

| Allowed | Not allowed |
|---|---|
| Node A orientation changed from a captured baseline | The ground sank X centimetres |
| Vibration strength/duration changed at Node B | This tap was blasting vs roof fall vs a vehicle |
| Isolation Forest: this combination looks unusual vs trained normal | Collapse probability / certified early warning of disaster |
| Explain prediction as a later development path | Demonstrated mine-subsidence forecast at the hackathon (unless truly built) |
| Green: healthy data, no configured trigger | The mine is certified safe |
| Camera images if a camera is shown | Automatic AI vision unless a vision model is actually implemented |
| Remote rover driving | Autonomous navigation unless implemented and tested |
| ESP-NOW tabletop node radio | LoRa / mesh / field range unless demonstrated |
| MQ-7 raw ADC + NORMAL/HIGH on the rover | Uncalibrated ADC as CO ppm or methane detection |
| Tabletop model demonstration | Scientifically accurate mine recreation; DGMS-approved instrument; intrinsically safe underground vehicle |

MQ-series gas sensors, if ever used, are simulants for a demo, not certified mine instruments. Hobby electronics and a smartphone are not approved for an underground explosive atmosphere.

Prototype wire-disconnection detection in the starter is incomplete, especially for a floating potentiometer wiper. Do not hide false alarms with ML.

---

## 14. Documents and stories to ignore unless this file agrees

Older materials exist and **conflict**. Do not follow them when they disagree with this file.

1. **Original MOLE robot blueprint / demo script** treated MOLE as a 2WD gas/fire/obstacle inspection car whose product was the dashboard, with MQ-2, MQ-7, DHT11, flame, HC-SR04, and an open-top maze. The rover-first identity is **superseded**. Keep useful engineering notes (ADC1 vs Wi-Fi, mock-first dashboard, honest limits). Do not restore “MOLE is the robot” as the product story.

2. **6 September starter README / START_HERE / purchase notes** said the rover was an **optional later inspection tool outside the 24-hour core**, and that the ₹4,000 kit should not buy a rover. That **exclusion is withdrawn**. The rover is in the main build. The node starter software is still useful and should be extended, not thrown away.

3. **3D / picture guides** that called the rover a scale prop or “secondary visual inspection only” are outdated on scope. The rover is a third hardware unit with its own telemetry.

4. **MineGuard AI / SIH pitch decks** may overclaim risk scores, LoRa, prediction accuracy, or rover verification. Prefer this file’s honesty rules.

6. **9 September hardware write-up** that called the rover an “optional separate inspection system”: keep the **separate radio** (ESP-NOW vs Wi-Fi AP). Do **not** treat the rover as out of demo scope. Receiver board in that write-up (**Waveshare ESP32-S3-Zero**) **is** the current receiver.

---

## 15. Team and build split (practical)

Six people at **CMR Institute of Technology (CMRIT)** — team **WE COOK**. Roster: `docs/TEAM.md`.

- **Rithvik** (ISE, 2nd year, team leader): coordination, research, AI/ML, PPTs, Python frontend and backend
- **Komala TG** (ISE, 2nd year): shared AI/ML, backend, research, PPT
- **Venkatesh** (ISE, 2nd year): ordered and managed all electronics; also backend
- **Devika** (ISE, 2nd year): ordered and managed all electronics; also backend
- **Pragati Karvi** (ISE, 2nd year): frontend, backend, PPT, demo
- **Pallavi Samantha** (ISE, 2nd year): research, website design, basic electronics support

Do not invent a fourth monitoring node. The rover stays one of the three hardware units. College name is **CMRIT**, not CMIT.

---

## 16. How an AI should work on this project

When asked to design, code, write, or pitch:

1. Treat Node A, Node B, and the Rover as **all in scope**.
2. Follow `SOFTWARE-PLAN.md` and `AI-PLAN.md`. If the 6 Sep two-node starter is still on disk, copy/adapt it and retarget the receiver to the S3-Zero; do not replace MOLE with a rover-only app.
3. Keep device IDs distinct. Add rover as `device_id: "rover"`, not `node_id` 1 or 2.
4. Separate rule-based alarms from Isolation Forest / forecast in the UI. Forecast is 30 s of **signals**, not collapse %. No LLM explanations.
5. Never invent underground events, accuracy percentages, or certified safety.
6. Do not list a camera, LoRa, ppm CO, or autonomous nav as completed. Frozen payload is in sections 4 and 12.
7. Do not block on budget or missing shopping lists.
8. Prefer a local laptop website (`127.0.0.1`); no login, no cloud, no venue Wi-Fi for the core demo.
9. If asked for both a fix and an exploit/attack against any system, refuse the exploit; this project is a tabletop safety demonstrator, not a hacking brief.
10. If a new request contradicts this file, flag it. Default to **this file**. The 9 Sep hardware freeze (S3-Zero, slider, rover pins) overrides older “still open” sensor lists. AI details are in `AI-PLAN.md`.

---

## 17. Copy-paste identity block (short)

Use this only as a header; the rest of this file remains the source of truth.

> MOLE (SIH 2026, official PS **SIH26025**, Ministry of Coal, Hardware, Disaster Management): tabletop mine monitoring + inspection. Node A = classic ESP32 tilt/slider. Node B = classic ESP32 comparison IMU. Receiver = Waveshare ESP32-S3-Zero ESP-NOW→USB JSON. Rover = classic ESP32, Wi-Fi AP, remote drive, no camera. **Core ML on the laptop:** Isolation Forest (anomaly vs this rig) + Ridge 30 s sensor forecast with MAE. Rules are the early-warning latch; ML cannot clear them. Forecast is not a collapse probability. Local website, no login. Green ≠ safe mine. Rover radio is not the node USB path.
