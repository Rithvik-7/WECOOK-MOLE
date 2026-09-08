# MOLE — Mine Observation & Live-alert Engine

**Team WE COOK** · GitHub: [Rithvik-7/WECOOK-MOLE](https://github.com/Rithvik-7/WECOOK-MOLE)

**Smart India Hackathon 2026** · Official problem ID **SIH26025** (SIH 2026 problem 025) · **Ministry of Coal** · category **Hardware** · theme **Disaster Management**.

Catalogues and the 6-slide template use **SIH26025**. Do not write SIH2026025.

MOLE is a tabletop **mine-monitoring and inspection** system: two fixed sensor nodes, laptop ML (Isolation Forest + 30 s sensor-trend forecast), a remote inspection rover, and one local dashboard. Measurements indicate disturbance. They do not prove a collapse.

**Future agents / teammates:** start at [`AGENTS.md`](AGENTS.md) (complete A–Z hardware + software contract).

---

MOLE combines:

- **Node A:** fixed ESP32 + MPU6050 + crack slider
- **Node B:** fixed ESP32 + MPU6050 comparison point
- **Receiver:** Waveshare ESP32-S3-Zero, ESP-NOW channel 1 → USB-C JSON
- **Rover:** separate ESP32 Wi-Fi AP, remote drive + inspection sensors
- **Laptop:** local Flask website, SQLite, rules, Isolation Forest, Ridge forecast

No account, cloud, camera, LLM, or venue internet is required.

## Run now without hardware

```powershell
cd C:\Users\brith\Desktop\mole\software
python -m pip install -r requirements.txt
python app.py --mode simulate
```

Open:

- Monitoring + AI: <http://127.0.0.1:5000/monitoring>
- Separate rover control: <http://127.0.0.1:5000/rover>

Simulation is permanently labelled and cannot train Isolation Forest. It does
exercise node status, persistence, stale/fault handling, charts, Ridge forecasts,
rover telemetry, hold-to-move controls, event history, and CSV export. Simulate
mode starts with 40 seconds of quiet history so the chart and 30 s prediction
are visible immediately. Use **Rising trend** to show Node A climbing while
Node B stays quiet.

## Tomorrow: move from simulation to live hardware

### 1. Flash all four controllers

Use Arduino IDE:

| Unit | Sketch | Board |
|---|---|---|
| Node A | `firmware/node/node.ino` | ESP32 Dev Module |
| Node B | `firmware/node_b/node.ino` | ESP32 Dev Module |
| Receiver | `firmware/receiver_s3/receiver_s3.ino` | Waveshare ESP32-S3-Zero, or ESP32S3 Dev Module |
| Rover | `firmware/rover/rover.ino` | ESP32 Dev Module |

Receiver setting: **USB CDC On Boot = Enabled**. If upload fails, hold BOOT,
tap RESET, release BOOT, then upload.

### 2. Prove node radio before opening the website

Open the S3-Zero Serial Monitor at 115200. Expect one JSON object per line for
Node A (`node_id:1`) and Node B (`node_id:2`). Close Serial Monitor before
starting Python because only one program can own the COM port.

### 3. Start live mode

```powershell
cd C:\Users\brith\Desktop\mole\software
python app.py --mode live --serial auto
```

If more than one COM port exists:

```powershell
python app.py --mode live --serial COM5
```

Live mode never silently switches to fake data. If USB disconnects, the service
keeps running and retries every two seconds. Nodes become UNKNOWN after five
seconds without a valid packet.

### 4. Calibrate

On Monitoring + AI:

1. Keep both node mounts still.
2. Select **Baseline A**, then **Baseline B**.
3. For Node A slider, place the linkage at ruler position 1 and record ADC + mm.
4. Move it to ruler position 2 and record ADC + mm.
5. Open **Slider two-point calibration**, enter both pairs, and save.

Live calibration and orientation baselines persist in SQLite across restarts.
Changing calibration resets the Node A anomaly model because its feature scale changed.

### 5. AI models are already trained

Shipped tabletop priors load automatically:

- `software/artifacts/node1.prior.joblib`
- `software/artifacts/node2.prior.joblib`
- `software/artifacts/joint.prior.joblib`

You do **not** need to wait 120 samples or click Train for the demo. Isolation Forest
+ LOF start READY. Optional later retrain on live quiet data writes `node1.joblib` /
`node2.joblib` and overrides the prior until you reset.

### 6. Connect and test the rover

1. Power the rover.
2. Join laptop Wi-Fi **Mine-Rover-AP**.
3. Open <http://127.0.0.1:5000/rover>.
4. Raise driven wheels off the table.
5. Hold FWD/REV/LEFT/RIGHT, release, then verify STOP.
6. Confirm distance, IR, MQ-7 raw, roll, pitch, and vibration.

Direction commands are repeated while held. Release sends STOP twice to defeat
an in-flight request race. Rover firmware independently stops after about 400 ms
without a fresh drive command.

## What the AI actually does

### Isolation Forest + Local Outlier Factor — anomaly detection

One ensemble per fixed node learns this rig's live NORMAL combinations:

- Tilt change from captured baseline
- Vibration proxy
- Tilt rate
- Node A crack gap, once calibrated

Output is INACTIVE / READY / UNUSUAL, Isolation Forest score, LOF vote, and largest standardized
feature deviation. A third Isolation Forest watches Node A vs Node B residuals (local vs common
motion). AI cannot clear a rule warning.

Shipped **tabletop prior** models load in both simulate and live so Isolation Forest
is READY without a training wait. They describe quiet-tabletop NORMAL, not a mine.
Optional live retrain still exists if you later have two quiet minutes.

### Holdout-selected 30-second sensor prediction

Ridge, HuberRegressor, LinearRegression, and a persistence baseline compete on a holdout window.
The winner forecasts the next 30 points of:

- Node A/B tilt change
- Node A/B vibration
- Node A crack gap

The dashboard shows measured lines, dashed prediction, an error band, holdout MAE,
candidate MAE table, quality, forecast-surprise z-score, and time-to-WATCH/ALERT only when
the fitted slope is moving toward a configured tabletop threshold.

This is a **sensor-trend forecast, not a collapse/subsidence probability**.

### Rules — early warning

- WATCH: 3° tilt or 2 mm crack for three readings
- ALERT: 6° tilt or 4 mm crack for three readings
- UNKNOWN: stale, unseen, invalid, or uncalibrated required data
- ALERT latches; acknowledgement records awareness but does not erase it
- Clear requires three fresh NORMAL readings

These are visible tabletop demo thresholds, not scientific mine trigger levels.

## Judge demonstration

1. Show both fixed nodes NORMAL and updating.
2. Show model names, training count, features, and forecast MAE.
3. Use **Rising trend** in rehearsal, then use a real controlled tilt in the demo.
4. Show WATCH → ALERT and the measured reason.
5. Show Node A moved while Node B remained quiet: localized disturbance evidence.
6. Open the separate Rover Inspection page because a warning appeared.
7. Drive, STOP, and show inspection sensor feedback.
8. Acknowledge, restore the model, clear after recovery, and show retained history.

Pitch sentence:

> Isolation Forest + LOF detect unusual combinations relative to this rig's learned
> normal. A joint forest watches A vs B residual. Holdout-selected Ridge/Huber/Linear
> forecasts the next 30 seconds of measured signals with MAE. Rules remain the
> independent early-warning latch.

## Verification

```powershell
cd software
python -m pytest -q
python -m py_compile app.py engine.py forecast.py anomaly.py
```

Current software verification: **25 tests pass**. Browser QA covers the separate
monitoring and rover pages, simulated rising forecasts, hold-to-move → STOP, and
the IR flag (digital pin, does not auto-brake). Physical flashing, motor polarity,
actual COM number, radio range, and real-sensor threshold tuning must be completed
with the hardware.
