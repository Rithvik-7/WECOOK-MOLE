# MOLE requirements tracker

Latest instructions override earlier notes. This file is the working record of what is confirmed, assumed, waiting, implemented, and tested.

## Confirmed requirements

- Surface monitoring for underground coal-mine effects on people, roads, buildings, farmland, and forest.
- Fixed nodes A–D, ESP32-S3 receiver, local gateway, website, mobile app, and a separate rover R1.
- All four nodes and the receiver are ESP32-S3 boards. Node C uses a linear sensor and MQ-2, not an IR channel. Node B's temperature module name is still open, so that channel stays an ADC count.
- BME280 reports temperature, humidity, and pressure only, and only where installed.
- Potentiometer millimetres require calibration. MQ-5 starts as a warmed-up raw/relative gas signal.
- Anomaly scores are not collapse probabilities. Acknowledgement does not close an incident. Offline is never shown as normal.
- Public monitoring without a login screen. Privileged actions need a paired capability credential.
- Palette: `#F7F1DE`, `#B0BA99`, `#9D6638`, `#4E220F`, plus an accessible critical red with a text or symbol label.
- Typography: Lexend for titles, Source Sans 3 for body. No gradients. Text wordmark MOLE only.
- Map-first website, node drawer, 2D default and 3D cutaway, demonstration schematic until real geometry arrives.
- Incident path: OPEN → ACKNOWLEDGED → RECOVERED/PENDING REVIEW → CLOSED.
- One-page PDF and real xlsx/CSV. English and Hindi in the app.

## Assumptions

- Local development uses SQLite. The schema is the same shape intended for PostgreSQL.
- ESP-NOW is the initial radio, described as a star until relay forwarding is demonstrated.
- Node B matches Node A’s role (surface motion) but its exact parts are not confirmed, so its capability list stays partial.
- One BME280 is assumed on Node D only until a count is confirmed.
- The IR channel is present on Node C and marked unavailable. No invented IR units.
- Operator pairing stores the capability token in the browser session only. It is not compiled into the site.
- A labelled demonstration site, “East Panel Demonstration,” stands in for real coordinates.
- Direct receiver-to-laptop serial/HTTP is the first gateway path. Receiver Wi-Fi to the cloud is an adapter, not the default.

## Awaiting input

- Exact boards and sensor models, including the IR module and its purpose.
- Actual wiring and pin maps.
- How many BME280 modules exist, and which nodes contain them.
- Node positions, orientation, and whether Node C is on the surface or in a gallery.
- Rover controller, motors, driver, and protocol.
- Historical spreadsheets and time zones.
- Hosting, domain, weather, SMS/email, push, and LLM credentials.
- Approval of any logo beyond the text wordmark.

## Implemented in this repository

- Requirements and hardware manifest.
- Next.js monitoring website: overview map, drawer, 2D/3D, nodes, analytics, incidents, rover, assistant.
- FastAPI service: telemetry ingest, incidents, SOS, rover missions, live events, exports, PDF.
- Local gateway queue with duplicate-safe sync.
- Firmware sketches with explicit unconfirmed-pin configuration.
- Rule, baseline, and change-point analysis with an honest model card.
- Expo companion app screens for home, alerts, map, more, and SOS.
- Demonstration scenarios for the twelve review cases that do not need physical hardware.

## Tested in software

- Ingest persists, opens the correct node incident, and remains after a new read.
- Public requests cannot acknowledge, close, calibrate, or command the rover.
- Expired rover commands are rejected.
- Excel and PDF exports include units and an explicit demonstration origin.
- Node B movement does not recolor other nodes.

## Requires physical hardware

- Radio range, ESP-NOW delivery, and any future mesh relay.
- LCD pages, buzzer timing, and sensor warm-up on real boards.
- Potentiometer millimetre calibration.
- IR driver behavior.
- Push, SMS, and background notification delivery on a phone.
- Rover motion, camera, and return-to-base.
