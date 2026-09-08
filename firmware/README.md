# Flash (Arduino IDE)

## Node A — classic ESP32 Dev Module
Open `firmware/node/node.ino`. Keep `NODE_ID 1` and `HAS_POT 1`. Board: ESP32 Dev Module.

## Node B — classic ESP32 Dev Module
Open `firmware/node_b/node.ino` (`NODE_ID 2`, `HAS_POT 0`). Board: ESP32 Dev Module.

## Receiver — Waveshare ESP32-S3-Zero
Open `firmware/receiver_s3/receiver_s3.ino`.
Board: Waveshare ESP32-S3-Zero **or** ESP32S3 Dev Module.
**USB CDC On Boot = Enabled.**
If upload fails: hold BOOT, tap RESET, release BOOT, upload.

## Rover — classic ESP32 Dev Module
Open `firmware/rover/rover.ino`. AP `Mine-Rover-AP` at 192.168.4.1.

Pins: L298N IN1=13 IN2=12 IN3=14 IN4=27; MPU 21/22; HC-SR04 TRIG=5 ECHO=18 via 1k/2k divider; MQ-7 AO=36 raw; **IR OUT=19, LOW=obstacle**. Leave L298N ENA/ENB jumpers on. GPIO19 is not a motor pin.

IR is a digital near-field flag. It does not auto-stop the rover. Debounced (majority of 3). Ambient light and glossy tabletops can false-trip it.

Laptop website: `software/TELEMETRY.md`
