# Demo script — SIH26025 / Team WE COOK

Pitch order: **monitor and evidence first**, then drive the rover **because a warning appeared**. Do not pitch a gas-car maze robot. Do not pitch sensors-plus-a-rover with a decorative “AI” badge.

## 0. Before judges walk up

- [ ] Four boards flashed (Node A, Node B, Waveshare ESP32-S3-Zero, rover).
- [ ] Arduino Serial Monitor **closed** (it steals the S3 COM port).
- [ ] Laptop: `python app.py --mode live --serial COM3` (or the S3 port). Never `--serial` the rover USB.
- [ ] Slider two-point cal saved; Baseline A and Baseline B captured with mounts still.
- [ ] Rehearsal fallback: `python app.py --mode simulate` — labelled **Simulated**, cannot persist-train Isolation Forest.

## 1. Simulate (no hardware / rain day)

```powershell
cd software
python -m pip install -r requirements.txt
python app.py --mode simulate
```

Open [http://127.0.0.1:5000/monitoring](http://127.0.0.1:5000/monitoring).

1. Show both nodes updating. Name **SIH26025**.
2. Point at Isolation Forest + LOF, joint A–B forest, holdout forecast MAE. Say **not collapse %**.
3. Rehearsal **Rising trend**: Node A climbs, Node B stays quiet.
4. WATCH → ALERT with the measured reason. Rules latch; ML cannot clear them.
5. Open [Rover Inspection](http://127.0.0.1:5000/rover) **because a warning appeared**.
6. Hold FWD (simulated), STOP. IR does not auto-brake.
7. Back on monitoring, **Inspection done** after recovery. History still lists the event.

## 2. Live tabletop

```powershell
cd software
python app.py --mode live --serial COM3 --host 127.0.0.1 --port 5000
```

1. USB receiver **2/2 fresh**. Node A crack in mm, Node B comparison tilt.
2. Physically tilt Node A; leave Node B quieter → localized evidence.
3. Show WATCH then latched ALERT and the written rule reason.
4. Join Wi-Fi **Mine-Rover-AP**. Keep Flask on localhost.
5. Raise wheels. **Hold** FWD / REV / LEFT / RIGHT. Release or Space = STOP. Firmware also stops after **400 ms**.
6. Show ultrasonic cm, IR flag on GPIO19 (does not stop motors), MQ-7 **raw ADC** (not ppm).
7. Recover mounts. **Inspection done** closes a recovered latch on both nodes. Ack ≠ erase.

## 3. Speaker sentence

> Isolation Forest + LOF flag unusual combinations versus this rig’s learned normal. A joint forest watches A vs B residual. Holdout-selected sklearn regression forecasts the next 30 seconds of those same signals with MAE. Rules remain the independent early-warning latch. The rover is remote inspection, not autonomy.

## 4. If something fails

| Symptom | What to do |
|---|---|
| Waiting for data | Plug S3-Zero; close Serial Monitor; confirm COM is the receiver (VID `303A`), not rover CP2102 |
| Rover unreachable | Laptop is probably still on campus Wi-Fi. Join **Mine-Rover-AP** |
| Motors dead | ENA/ENB **jumpers ON** (do not wire them to ESP32); motor battery; common GND; IN1=13 IN2=12 IN3=14 IN4=27 |
| Alert never leaves | Recover mounts, then **Inspection done** |
| Slider stuck at 0 mm | SIG → 1 kΩ → GPIO34; recapture two-point cal |
