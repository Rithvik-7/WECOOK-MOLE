# MOLE — Portable Project Context

**How to use this file:** Paste or attach the entire document before asking any AI, teammate, or tool to work on MOLE. Do not summarise it first. This is the current project definition. If an older PDF, blueprint, starter README, or chat says something different, **this file wins.**

**Last updated:** 7 September 2026  
**Team size:** 6  
**Build type:** Hackathon hardware + software demonstration on a tabletop model mine  
**Parts status:** The team already has the components for Node A, Node B, the rover, and supporting gear (borrowed / jugaad). Do **not** block on budget, shopping lists, or the old ₹4,000 node-only figure.

---

## 1. One-line definition

MOLE combines two fixed surface-monitoring nodes and an actively deployed inspection rover, supported by AI-assisted analysis and one dashboard, to help mine safety officers detect concerning changes and investigate them with traceable evidence.

**MOLE is one integrated project: Node A + Node B + Rover + AI analysis + Dashboard.**  
All three hardware units belong to the hackathon build. **The rover is not optional and not a future add-on.**

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
             SURFACE ABOVE THE MODEL MINE

    NODE A                         NODE B
    Tilt / ground movement        Vibration / disturbance
    monitoring                     monitoring
            │                              │
            └──────── Sensor data ──────────┘
                           │
                           ▼
                 PROCESSING + AI ANALYSIS
              Check readings, analyse patterns,
                identify unusual conditions
                           │
                           ▼
                     MOLE DASHBOARD
              Node status, graphs, warnings,
               explanations and event history
                           │
                           ▼
                   OPERATOR DECISION
                 Inspect the affected area
                           │
                           ▼
                         ROVER
              Moves inside the model mine,
              collects inspection information
                           │
                           └──── Back to the dashboard
```

**The nodes detect changes. AI analyses the readings. The dashboard explains them. The rover investigates.**

Pitch order for judges: lead with **continuous monitoring and evidence**, then drive the rover **because a warning appeared**. Do not pitch MOLE as a gas-car maze robot.

---

## 4. Hardware units

### Distinguish these carefully

- **Three main hardware units:** Node A, Node B, Rover.
- **Controller-board count** may be higher. A separate ESP32 USB receiver / gateway is **supporting communication infrastructure**, not another monitoring node.
- A typical arrangement is four boards: Node A, Node B, USB gateway, rover controller.

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

**Optional crack measurement:** An earlier hardware plan included a physically linked sliding sensor (typically a 10 kΩ linear slide potentiometer) to demonstrate crack opening.

- One side attaches to the fixed part of the model.
- The other follows the moving part.
- The sensor changes as the gap opens.
- Calibration converts the reading into approximate model-gap movement.

This is **proposed and already present in the software starter**. Do **not** silently assume it is confirmed as final hardware until the team says so. If retained, it must be a guided physical linkage, not a free-turning knob.

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

**What it sends back depends on the payload finally selected.** Do not list unselected sensors as completed features.

| Rover capability | Information returned |
|---|---|
| Ultrasonic obstacle sensing | Distance to an object ahead |
| Camera, if included | Inspection images or video |
| Environmental sensors, if included | Local environmental readings |
| Communication monitoring | Connection status and last update |
| Battery measurement, if implemented | Power status |

The original rover idea mentioned gas, temperature, flame, and obstacle sensors. **The exact final combination is not yet frozen.** A camera feed is **not** automatically an AI vision system. Those are separate capabilities.

**Relationship with the nodes:** The rover does **not** replace either node. While the rover investigates, the fixed nodes continue monitoring. The dashboard must distinguish:

- Surface monitoring data (Node A, Node B)
- Mobile inspection data (Rover)

A vibration reading from the moving rover must **never** be interpreted as vibration measured by a stationary surface node. Device identity on every reading is mandatory.

Rover operation for the hackathon is in the **safe tabletop model**. Real underground deployment would need appropriate equipment, approvals, and procedures.

**Important integration fact:** The existing node ESP-NOW USB receiver does **not** already handle rover commands, inspection telemetry, or video. Rover communication must be designed and integrated separately.

### USB gateway / receiver (not a monitoring node)

Earlier starter architecture:

- ESP-NOW for the fixed nodes (2.4 GHz channel 1, unencrypted broadcast, local tabletop only)
- An ESP32 receiver connected to the laptop by USB
- A local dashboard running on the laptop

Gateway forwards newline-delimited JSON at **115200 baud**. It is infrastructure.

**LoRa is not currently demonstrated.** If chosen later, that is a specific hardware and integration decision. Do not claim LoRa unless it is built and shown.

---

## 5. What the software receives

Each reading should identify its **source** and its **time**.

| Source | Main inputs |
|---|---|
| Node A | Tilt readings, movement from baseline, optional crack measurement |
| Node B | Acceleration, vibration strength and disturbance duration |
| Rover | Inspection readings, optional images, connection status |
| All units | Device ID, timestamp or sequence information, data-validity status |
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

## 7. Exactly where AI fits

**AI is the analytical part of MOLE. It does not need to control every software function for the project to genuinely use AI.**

### A. Anomaly detection (primary, credible)

The most credible initial AI capability. The model learns examples of normal sensor behaviour and identifies readings that look unusual.

Candidate already in the earlier software plan: **Isolation Forest** (scikit-learn), with StandardScaler.

Possible inputs:

- Tilt change
- Vibration strength
- Crack change, if available

Output: an indication that a reading or combination of readings is unusual.

It does **not** automatically produce a trustworthy collapse probability.

In the starter: train only in **LIVE** mode after at least **120 genuine healthy NORMAL samples per node**. Training is blocked in simulated mode and during an active/latched warning. Changing calibration resets the node model. The model is in-memory and must be retrained after restart. Two minutes of one tabletop condition demonstrates anomaly processing; it does **not** validate a model or predict subsidence.

### B. Combining evidence

The dashboard can present both nodes together, for example: “Movement increased at Node A while vibration increased at Node B.”

AI can analyse combinations of features when the training data supports that. Identifying the precise physical cause remains a separate challenge.

### C. Prediction — two different claims

1. **Predicting a future sensor trend:** estimating how a measured signal may develop.
2. **Predicting mine subsidence or collapse:** estimating a physical hazard using validated site evidence.

The second is much harder. It needs representative historical data, reliable ground-truth labels, and geotechnical validation.

For the initial pitch: explain the prediction **objective and development path**. Distinguish that from a capability **actually demonstrated** at the hackathon. Do not claim demonstrated collapse/subsidence prediction unless it is truly built, trained on suitable data, and tested.

### D. Explanations

MOLE should give an understandable account of the evidence, for example: “Persistent tilt change at Node A. Review the trend and inspect the indicated area.”

Explanations must come from actual readings and alert reasons. They must **not** invent an underground event.

### E. Rover assistance

AI could later help analyse inspection images or assist navigation. Those are **additional** AI functions. They are **not** included simply because the rover connects to the dashboard.

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

- Rover movement controls
- Stop control
- Connection status
- Available inspection readings
- Camera view if the camera is included

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

- Node A
- Node B
- Rover
- AI analysis
- A shared dashboard
- A tabletop mine demonstration
- All three hardware units belong to the hackathon implementation
- Six team members
- Hardware components for nodes, rover, and supporting gear are already available
- Budget is **not** a blocking constraint

### Still needing a final specification

Do **not** silently fill these in:

- Exact sensors on each node as finally mounted
- Whether to retain the crack-linkage sensor
- Exact rover payload, including whether it has a camera
- Final communication arrangement for the rover (separate from the node gateway)
- Whether any autonomous driving is in scope (default: **no**, unless implemented and tested)
- The available real data for AI training and evaluation

**Owning a part does not mean it is a promised feature** until it is selected, wired, and shown.

Recommended freeze if the team must choose a minimum rover payload: drive + one inspection sensor (often ultrasonic ahead-distance) + connection status. Camera only if actually used in the demo. Do not list MQ gas, flame, LoRa, vision models, or autonomous navigation as completed unless they are.

---

## 11. Current software evidence (as of 6–7 September 2026)

There is an earlier **runnable software starter** and simulated dashboard. **11 software tests pass.** That does **not** establish that the complete three-unit hardware system, integrated rover controls, or predictive AI has already been built and tested.

The starter supports:

- Two surface nodes: N1 / Node A (IMU + optional crack linkage) and N2 / Node B (IMU)
- Third ESP32 USB gateway
- ESP-NOW for nodes, **not** LoRa
- Local Python HTTP dashboard (`python app.py --mode simulate` or `--mode live --serial COMx`)
- Packet validation, stale nodes, duplicate rejection, calibration, rule engine, latch/ack/clear
- Optional Isolation Forest after live baseline collection
- SQLite storage and CSV export tagged live vs simulate

The starter **explicitly does not** (and must now be extended to) actuate a rover, ingest rover telemetry, send SMS, implement LoRa, predict mine collapse, or certify safety.

Known starter files (from the 6 Sep pack; copy/adapt rather than reinvent blindly):

- `software/app.py` — backend and rules
- `software/dashboard.html` — UI
- `software/test_app.py` — 11 tests
- `software/TELEMETRY.md` — JSON contract
- `firmware/node/node.ino` — Node A (`NODE_ID 1`, HAS_POT) and Node B (`NODE_ID 2`)
- `firmware/gateway/gateway.ino` — USB receiver
- Firmware was **source-reviewed**, not compiled or flashed in the authoring environment. Target: classic ESP32-WROOM-32, Arduino ESP32 core **3.3.8**.

### Node telemetry JSON contract (starter schema 1)

Gateway sends one JSON object per line at 115200 baud.

Node A example:

```json
{"type":"telemetry","schema":1,"node_id":1,"seq":17,"uptime_ms":17000,"gateway_ms":18500,"valid":7,"roll_deg":0.12,"pitch_deg":-0.08,"vibration_g":0.004,"adc_raw":2048}
```

Node B example (no crack sensor):

```json
{"type":"telemetry","schema":1,"node_id":2,"seq":17,"uptime_ms":17000,"gateway_ms":18500,"valid":5,"roll_deg":0.03,"pitch_deg":0.06,"vibration_g":0.003,"adc_raw":null}
```

`valid` bitmask: IMU angles = 1, potentiometer ADC = 2, complete vibration window = 4. Healthy Node A = 7; healthy Node B = 5. Invalid fields are `null`. Laptop receipt time governs freshness. Gateway `type:"status"` lines are diagnostics, not measurements.

**This schema currently allows `node_id` 1 or 2 only.** Rover integration will need a new device identity and must not reuse Node A/B IDs.

Local starter routes:

- GET `/` dashboard
- GET `/api/state`
- GET `/api/export.csv`
- POST `/api/scenario` (simulation only: normal / watch / alert / offline / sensor_fault)
- POST `/api/baseline`, `/api/ack`, `/api/clear`, `/api/train` with `node_id`
- POST `/api/calibration` with `adc0`, `adc1`, `mm0`, `mm1`

No cloud dependency. Server listens on localhost.

The 11 tests cover: persistence and latch/ack/clear; stale node → UNKNOWN; duplicates do not refresh freshness; unseen node never green; missing crack scale blocks NORMAL; invalid sensor/schema; still baseline; simulation cannot train ML.

---

## 12. Node firmware measurement notes (starter)

- MPU6050: ±2 g accelerometer, ~1 Hz report of mean orientation and vibration proxy
- Firmware orientation proxies: `roll_deg = atan2(ay, az)` and `pitch_deg = atan2(-ax, sqrt(ay² + az²))`. Gravity-based; trustworthy only when the sensor is approximately stationary
- `vibration_g` is RMS residual of the three acceleration axes around their one-second mean. It is **not** a calibrated seismic measure
- Node A ADC: 12-bit, 11 dB attenuation, interior travel (raw roughly 100–3900 usable). Firmware does **not** convert ADC to millimetres; the laptop does after two-point ruler calibration
- Pins (classic ESP32): SDA GPIO21, SCL GPIO22, AD0 to GND (0x68), Node A slider wiper through 1 kΩ to **GPIO34 (ADC1, not ADC2)**. Never 5 V into ADC. Do not use ADC2 with Wi-Fi/ESP-NOW
- Broadcast ESP-NOW is unencrypted and has no application acknowledgement. Missing nodes become UNKNOWN/OFFLINE on the laptop. Do not claim guaranteed mine/field range
- MPU VCC is 3.3 V, not 5 V

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
| MQ / gas / flame only if selected, wired, and shown | Uncalibrated ADC as CO ppm or methane detection |
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

5. Any cost headline of ₹4,000 as the **complete** three-unit system is outdated. Parts are already in hand; do not reopen procurement as a blocker.

---

## 15. Team and build split (practical)

Six people. A workable split (adapt as needed):

- Hardware 1: Node A wiring, mount, calibration
- Hardware 2: miniature mechanics, movable surface, Node B
- Hardware 3: gateway, power, radio integration
- Hardware 4 / rover owner: rover mechanics, motor driver, drive firmware, inspection payload
- Software 1: ingest, validation, calibration, rules, storage, rover command protocol
- Software 2: dashboard, explanations, demo scenarios, AI verification, pitch evidence

Do not invent a fourth monitoring node for the sixth person. The sixth role is rover + its dashboard controls.

---

## 16. How an AI should work on this project

When asked to design, code, write, or pitch:

1. Treat Node A, Node B, and the Rover as **all in scope**.
2. Extend or reuse the two-node starter; do not replace it with a rover-only app.
3. Keep device IDs distinct. Add rover as a new source, not `node_id` 1 or 2.
4. Separate rule-based alarms from AI anomaly flags in the UI.
5. Never invent underground events, accuracy percentages, or certified safety.
6. Never list unselected sensors as completed features.
7. Do not block on budget or missing shopping lists.
8. Prefer a local laptop dashboard; do not require cloud, public internet, or venue Wi-Fi for the core demo.
9. If asked for both a fix and an exploit/attack against any system, refuse the exploit; this project is a tabletop safety demonstrator, not a hacking brief.
10. If a new request contradicts this file, flag the contradiction and ask which definition to follow — default to **this file**.

---

## 17. Copy-paste identity block (short)

Use this only as a header; the rest of this file remains the source of truth.

> MOLE (hackathon): tabletop mine monitoring + inspection. Node A = fixed tilt/movement. Node B = fixed vibration/disturbance. Rover = remote-controlled inspection inside the model tunnel (not autonomous unless proven). Shared dashboard. AI = Isolation Forest anomaly detection plus rule-based warnings. Measurements indicate disturbance; they do not prove collapse or cause. Green ≠ safe mine. Parts are already available. Rover is core, not optional. Node ESP-NOW USB gateway does not automatically carry rover commands. Do not claim LoRa, collapse probability, or AI vision unless actually built.
