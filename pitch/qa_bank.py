"""Viva / judge Q&A bank for MOLE (SIH26025). Speak the answer; use push only if they follow up."""

from __future__ import annotations

SECTIONS: list[dict] = [
    {
        "title": "1. Identity and problem statement",
        "blurb": (
            "Start every judging round with the official ID, the user, and the honesty line. "
            "Do not recast the problem as a maze robot or a collapse-percentage app."
        ),
        "items": [
            {
                "q": "What is your project, in one sentence?",
                "a": (
                    "MOLE is a tabletop mine-monitoring and inspection system: two fixed nodes watch tilt, "
                    "vibration and a crack gap; the laptop latches an early warning and runs Isolation Forest "
                    "plus a 30-second sensor forecast; then an officer can remotely drive a rover because a "
                    "warning appeared. Readings show disturbance on this model. They do not prove a collapse."
                ),
            },
            {
                "q": "What is the official problem ID? Why not SIH2026025?",
                "a": (
                    "The catalogue ID is SIH26025 — Smart India Hackathon 2026, problem 025, Ministry of Coal, "
                    "Hardware, Disaster Management. SIH2026025 is year-plus-025 concatenated. Judges, catalogues "
                    "and the six-slide template match SIH26025. We never write the other string on the portal or the idea PPT."
                ),
            },
            {
                "q": "State the problem title.",
                "a": (
                    "Development of an AI-enabled Low Cost Real Time Mine Subsidence Monitoring, Prediction and "
                    "Early Warning System for Underground Coal Mines in India."
                ),
            },
            {
                "q": "Who is the user, and who owns the problem?",
                "a": (
                    "On demo day the user is a mine safety officer looking at a tabletop model. The Ministry of Coal "
                    "owns the problem statement. We help that officer notice a concerning change, see the evidence, "
                    "and inspect remotely. We do not replace a colliery control room or a DGMS-approved instrument."
                ),
            },
            {
                "q": "What does MOLE stand for? Team name?",
                "a": (
                    "Mine Observation & Live-alert Engine. Team name on the portal is WE COOK. Public code is "
                    "github.com/Rithvik-7/WECOOK-MOLE. Team ID is filled from the SIH portal after nomination."
                ),
            },
            {
                "q": "How does MOLE answer each word of the problem statement?",
                "a": (
                    "AI-enabled: named sklearn models, features, score and MAE on screen. Low-cost: ESP32-class boards "
                    "we already have; no cloud bill. Real-time: about one summarised packet per second per node. "
                    "Monitoring: two fixed nodes that keep watching. Prediction: next 30 seconds of tilt, vibration and "
                    "crack millimetres, with MAE — not collapse percent. Early warning: WATCH then a latched ALERT from "
                    "rules; ML cannot clear the latch. Underground coal mines: the PS context; the demonstration is a tabletop."
                ),
            },
            {
                "q": "Is ML optional? Is the rover optional?",
                "a": (
                    "Neither is optional. Hardware without visible ML does not answer “AI-enabled” or “prediction”. "
                    "A rover without standing nodes is a maze car, not this PS. Pitch order is monitor and evidence first, "
                    "then drive the rover because a warning appeared."
                ),
            },
            {
                "q": "Is this a certified mine-safety system?",
                "a": (
                    "No. It is a working Smart India Hackathon Hardware demonstration on a tabletop model. Hobby ESP32 "
                    "and MPU6050 boards are not intrinsically safe and are not DGMS-approved underground instruments. "
                    "Green on our dashboard means fresh valid data and no configured tabletop trigger. It does not certify a mine."
                ),
                "trap": True,
            },
            {
                "q": "Give the 15-second architecture.",
                "a": (
                    "Node A and Node B, classic ESP32, ESP-NOW channel 1, into a Waveshare ESP32-S3-Zero that prints JSON "
                    "on USB. Laptop Flask: store, rules, Isolation Forest, 30-second forecast, one local website. Rover is "
                    "a separate classic ESP32 on Wi-Fi AP Mine-Rover-AP. Two radios on purpose."
                ),
            },
            {
                "q": "What must never appear on the six-slide portal PDF?",
                "a": (
                    "SIH2026025, collapse probability, lives saved, LoRa we did not build, autonomous driving, CO ppm from "
                    "MQ-7, a seventh slide, a budget/BOM, or teammate photos. Upload only the official six-slide idea PDF. "
                    "This Q&A book and the long judge document are for the room, not the portal."
                ),
            },
        ],
    },
    {
        "title": "2. Domain: subsidence, mines, and existing methods",
        "blurb": (
            "Judges from mining or remote sensing will test whether you know the difference between a proxy and a "
            "geodetic measurement. Stay in that honesty. Context citations are not features we implemented."
        ),
        "items": [
            {
                "q": "What is mine subsidence, in plain language?",
                "a": (
                    "Subsidence is downward or differential movement of the ground, often above underground workings, "
                    "as the rock mass settles or is disturbed. It can show up as tilt, cracks, or unusual vibration at "
                    "the surface or in the workings. Measuring it properly in a colliery uses surveyed monuments, "
                    "approved geophones, extensometers, or satellite InSAR — not a student IMU on a model."
                ),
            },
            {
                "q": "Does a tilt reading prove subsidence or a collapse?",
                "a": (
                    "No. Tilt is a change of orientation from a captured baseline. On our table it means the mount moved. "
                    "It is not vertical settlement in centimetres, and it does not name the cause — blasting, a tap, "
                    "a roof fall, or a vehicle. Measurements can indicate disturbance. They do not prove a collapse."
                ),
                "trap": True,
            },
            {
                "q": "How is this done in real Indian mines today?",
                "a": (
                    "Typical tools are periodic surveys and total stations, piezometers and extensometers, walk-in "
                    "inspections, and at some longwall sites surface geophones. Satellite SBAS-InSAR is used in research "
                    "and some monitoring programmes for wide-area deformation, but it is not a one-second heading for "
                    "an officer at a face. DGMS (S&T) Technical Circular 01 of 2017, clause 6.1, asks longwall mines "
                    "for surface geophones in strata-control plans. We cite that as field-grade context. We do not implement it."
                ),
                "push": "If they ask for a paper: Sivakumar et al., 2005, on microseismic event-rate changes at Rajendra / SECL is the published Indian longwall hint we mention — again as context, not as our algorithm.",
            },
            {
                "q": "Then why has a cheap IoT kit not replaced those methods?",
                "a": (
                    "Because underground coal is a hazardous atmosphere: equipment must be approved, mounts must be "
                    "surveyed, radio must survive rock and regulation, and a false green light is dangerous. Cheap IMUs "
                    "drift, ESP-NOW is unencrypted and short-range, and there are almost no labelled collapse events "
                    "for a student model. The blocker is certification, labelling and environment — not that “nobody thought of ESP32”."
                ),
            },
            {
                "q": "Why is a tabletop model a valid answer to this Hardware PS?",
                "a": (
                    "SIH Hardware asks for a working loop a judge can verify in minutes: disturb → warn → explain → inspect. "
                    "A tabletop lets us show live packets, a latch, named ML, and a rover without claiming a colliery "
                    "installation. The field path — surveyed mounts, DGMS-approved sensing and communications, mine "
                    "thresholds — is spoken as future work, not as today’s output."
                ),
            },
            {
                "q": "MPU6050 versus a geophone or an inclinometer — why this sensor?",
                "a": (
                    "MPU6050 gives gravity-based roll/pitch and a crude RMS vibration proxy on a 3.3 V I²C chip we can "
                    "wire today. A geophone is a velocity sensor for seismic/microseismic arrays. A surveying inclinometer "
                    "or total station measures displacement with a known datum. We are an honest low-cost proxy for "
                    "mounting-surface micro-movement, not a professional microseismic array."
                ),
            },
            {
                "q": "Will you quote CIL fatality numbers as impact?",
                "a": (
                    "Only as published ministry context if a judge asks why the PS exists — for example MoC Annual Report "
                    "figures on accidents, subject to DGMS reconciliation. We do not invent “lives MOLE will save” or "
                    "disasters averted. Impact we can defend is notice, evidence, and a remote look on the table."
                ),
                "trap": True,
            },
            {
                "q": "What does Coal Mines Regulations, 2017 have to do with this?",
                "a": (
                    "CMR 2017 sets duties around dangerous occurrences and strata control. It explains why an officer "
                    "needs timely evidence. It is not implemented as software, and our 3° / 6° bands are not regulation "
                    "trigger levels."
                ),
            },
            {
                "q": "Could InSAR replace your nodes?",
                "a": (
                    "InSAR is excellent for wide-area, millimetre-to-centimetre deformation over days to weeks. It does "
                    "not give a one-hertz heading inside a model heading, and it does not drive a rover. We would treat "
                    "InSAR as a later fusion path, not as something we built."
                ),
            },
            {
                "q": "Why two points on the surface, not a dense mesh?",
                "a": (
                    "Two points are enough to show local versus common motion on a table: Node A moves, Node B stays "
                    "quiet. A real site would need a surveyed array. We do not pretend six hobby boards are a mine network."
                ),
            },
        ],
    },
    {
        "title": "3. Solution, uniqueness, and what we refuse to claim",
        "blurb": "If a judge has seen other student kits, this is the differentiation section.",
        "items": [
            {
                "q": "Walk through how it works, in order.",
                "a": (
                    "Nodes sample the MPU about 80 times a second and send one summary packet per second on ESP-NOW "
                    "channel 1. The S3-Zero prints one JSON line per packet on USB at 115200. The laptop checks freshness "
                    "and validity, converts tilt from the officer’s baseline, converts Node A ADC to millimetres after "
                    "two-point calibration, latches WATCH/ALERT from rules, scores Isolation Forest and a joint A–B forest, "
                    "and forecasts the next 30 seconds of those same signals. The officer reads both columns. If they "
                    "decide to look, they join Mine-Rover-AP and hold-to-move the rover."
                ),
            },
            {
                "q": "What is actually unique — not slogan unique?",
                "a": (
                    "One product, two radios, so rover vibration cannot poison Node B or node ML. Rules and ML sit side "
                    "by side; Isolation Forest cannot talk a red warning back to green. Prediction is labelled as a "
                    "30-second sensor-trend forecast with MAE, not a collapse prediction. Node B is a comparison location, "
                    "not a fake surveyed monument. Simulation is permanently labelled and cannot persist-train. Live USB "
                    "never silently fakes data. Green does not mean certified safe."
                ),
            },
            {
                "q": "Why not one node?",
                "a": (
                    "One node cannot tell local disturbance from the whole table being bumped. Joint Isolation Forest "
                    "uses absolute A–B tilt and vibration residuals and patterns such as QUIET, LOCAL_A, LOCAL_B, COMMON. "
                    "That is still not geology. It is a localisation hint a judge can see."
                ),
            },
            {
                "q": "Why is Node B not a “reference station”?",
                "a": (
                    "A geodetic reference needs a surveyed stable monument. Node B is another hobby IMU on the model. "
                    "We call it a comparison location. Calling it a reference would over-claim the physics."
                ),
            },
            {
                "q": "Why is intelligence on the laptop, not on the ESP32?",
                "a": (
                    "ESP32 measures and sends. Calibration, millimetres, A versus B, SQLite, sklearn, and the website "
                    "need CPU, storage and a screen the officer already has. Firmware does not compute millimetres, "
                    "alerts or AI. That split keeps the nodes simple and the claims auditable in Python."
                ),
            },
            {
                "q": "Why not pitch this as a gas-sensor maze robot?",
                "a": (
                    "That is an older, superseded identity. SIH26025 is monitoring, prediction and early warning of "
                    "subsidence-style disturbance, then inspection. The rover exists because a warning appeared. MQ-7 "
                    "is an inspection ADC on the rover, not the product, and it is not calibrated ppm."
                ),
            },
            {
                "q": "Walk-in inspection already exists. Why a rover?",
                "a": (
                    "Walk-in sends a person in first. Fixed nodes keep watching while the rover, if used, looks in a "
                    "different place. On the table the officer inspects the model tunnel without putting a hand in first. "
                    "It is remote drive, not autonomous rescue."
                ),
            },
            {
                "q": "What do you explicitly refuse to claim?",
                "a": (
                    "Mine is safe or certified. Collapse or subsidence probability. Roof will fail in N minutes. Ground "
                    "sank X centimetres. CO ppm from MQ-7. IR as auto-brake or lidar. Autonomous navigation. Camera "
                    "vision. LLM geology. LoRa or colliery mesh. Login or cloud operations centre. ML clearing a latched alert."
                ),
                "trap": True,
            },
        ],
    },
    {
        "title": "4. Hardware — Node A, Node B, and the USB receiver",
        "blurb": "Pins and boards are frozen. If you invent a different MCU or GPIO in the room, you lose the as-built contract.",
        "items": [
            {
                "q": "List every board and its job.",
                "a": (
                    "Node A: classic ESP32-WROOM-32 DevKit — tilt, vibration, crack slider. Node B: same DevKit — "
                    "comparison tilt and vibration, no slider. Receiver: Waveshare ESP32-S3-Zero (ESP32-S3FH4R2) — "
                    "ESP-NOW to USB-C JSON, no sensors. Rover: classic ESP32-WROOM-32 — drive and inspect on its own Wi-Fi AP. "
                    "That is four boards. The S3-Zero is infrastructure, not a third monitoring node."
                ),
            },
            {
                "q": "Node A pins and defines?",
                "a": (
                    "MPU6050 I²C address 0x68, SDA GPIO21, SCL GPIO22, 3.3 V, AD0 to GND. 10 kΩ linear slider SIG through "
                    "1 kΩ into GPIO34 (ADC1). NODE_ID 1, HAS_POT 1. Never 5 V into the ADC. Sketch: firmware/node/node.ino. "
                    "Arduino board: ESP32 Dev Module."
                ),
            },
            {
                "q": "Node B — what is different?",
                "a": (
                    "Same MPU pins. Slider not fitted. sliderRaw is always −1. NODE_ID 2, HAS_POT 0. Healthy valid mask "
                    "is 5 (IMU + vibration), not 7. Sketch: firmware/node_b/node.ino."
                ),
            },
            {
                "q": "How is tilt computed?",
                "a": (
                    "Firmware sends gravity roll and pitch: roll = atan2(ay, az), pitch = atan2(−ax, sqrt(ay²+az²)). "
                    "That is trustworthy only when the mount is approximately still. The laptop, after the officer "
                    "captures a baseline, computes tilt change as sqrt((roll−roll0)² + (pitch−pitch0)²). That is "
                    "orientation change, not vertical ground displacement."
                ),
            },
            {
                "q": "What is vibration_g?",
                "a": (
                    "RMS residual of the three acceleration axes around their one-second mean, computed in firmware "
                    "and sent as a proxy. It is not a calibrated seismic or geophone measure. A tap and a sustained "
                    "disturbance look different in duration; we still do not classify blasting versus roof fall."
                ),
            },
            {
                "q": "How does the crack slider become millimetres?",
                "a": (
                    "Firmware sends raw 12-bit ADC only. The laptop applies a two-point ruler calibration: two distinct "
                    "ADC values and two millimetre readings. Node A cannot show NORMAL until that scale exists. The "
                    "linkage must be guided, not a free knob. Changing calibration resets Node A anomaly features."
                ),
            },
            {
                "q": "Why GPIO34 and a 1 kΩ series resistor?",
                "a": (
                    "GPIO34 is ADC1. ADC2 is not used with Wi-Fi or ESP-NOW. The 1 kΩ series resistor protects the pin. "
                    "Optional 100 nF from GPIO34 to GND. Never feed 5 V into the ESP32 ADC."
                ),
            },
            {
                "q": "Sample rate and radio packet rate?",
                "a": (
                    "MPU is sampled about 80 Hz (SAMPLE_US 12500). Nodes broadcast about one summarised packet per second "
                    "to FF:FF:FF:FF:FF:FF on ESP-NOW channel 1. Sequence increments after each send."
                ),
            },
            {
                "q": "Explain the valid bitmask.",
                "a": (
                    "IMU = 1, potentiometer = 2, vibration window = 4. Healthy Node A = 7, healthy Node B = 5. Invalid "
                    "fields in USB JSON are null, never 0, so a dead sensor cannot look like a perfect zero reading."
                ),
            },
            {
                "q": "What does node firmware refuse to compute?",
                "a": (
                    "Millimetres, WATCH/ALERT, Isolation Forest, forecasts. The ESP32 measures and sends. That is deliberate "
                    "so a judge can audit rules and ML in Python."
                ),
            },
            {
                "q": "Why Waveshare ESP32-S3-Zero, not a classic ESP32 or an S2?",
                "a": (
                    "We need native USB-C CDC at 115200, no CH340, no sensors on the gateway. The freeze is Waveshare "
                    "ESP32-S3-Zero. Arduino: Waveshare ESP32-S3-Zero or ESP32S3 Dev Module, USB CDC On Boot = Enabled. "
                    "It is not the Node A/B board and not ESP32-S2."
                ),
            },
            {
                "q": "What does the receiver do, and what does it not do?",
                "a": (
                    "Wi-Fi STA forced to channel 1, ESP-NOW receive, size/version/node_id check, one JSON object per line "
                    "on Serial 115200. It may add gateway_ms. It does not compute tilt-delta, millimetres, rules or AI. "
                    "Sketch: firmware/receiver_s3/receiver_s3.ino."
                ),
            },
            {
                "q": "Upload is stuck on Connecting… What do you do?",
                "a": (
                    "One USB board at a time. Hold BOOT, tap RESET, release BOOT, then upload. Classic ESP32 uses the same "
                    "BOOT/RESET trick. Close Serial Monitor before Python — only one program may own the COM port."
                ),
            },
            {
                "q": "Give a USB JSON example the judge can look for.",
                "a": (
                    "Node A: type telemetry, schema 1, node_id 1, valid 7, roll_deg, pitch_deg, vibration_g, adc_raw. "
                    "Node B: node_id 2, valid 5, adc_raw null. node_id 1 and 2 are reserved. Rover is device_id rover over HTTP, not this USB schema."
                ),
            },
        ],
    },
    {
        "title": "5. Hardware — rover (core unit, separate radio)",
        "blurb": "Raise wheels before any motor demo. GPIO19 is IR. ECHO needs a divider.",
        "items": [
            {
                "q": "Why is the rover in the build at all?",
                "a": (
                    "Fixed nodes cannot move. After a warning, the officer may need to look down a heading. The rover "
                    "is that inspection unit: remote FWD/REV/LEFT/RIGHT/STOP plus ultrasonic centimetres, an IR near-flag, "
                    "MQ-7 raw ADC, and rover IMU. It does not replace Node A or B. While it drives, the nodes keep watching."
                ),
            },
            {
                "q": "Rover motor pins and stop behaviour?",
                "a": (
                    "L298N IN1=13, IN2=12, IN3=14, IN4=27. Leave ENA/ENB jumpers ON. STOP is all IN low. Firmware also "
                    "stops if no repeated command arrives for about 400 ms. If a side runs backward, swap that motor’s "
                    "two wires. Do not invent new GPIOs."
                ),
            },
            {
                "q": "Drive bit map?",
                "a": (
                    "STOP 0000, FWD 1010, REV 0101, LEFT 0110, RIGHT 1001 on IN1 IN2 IN3 IN4. HTTP GET on the rover: "
                    "/forward /backward /left /right /stop /telemetry /."
                ),
            },
            {
                "q": "Why is GPIO19 IR and not a motor pin?",
                "a": (
                    "Older drawings that put GPIO19 on L298N IN4 are wrong. IR OUT is GPIO19, INPUT_PULLUP, active LOW "
                    "means near, majority-of-3 debounce. It does not stop the motors. Treating IR as auto-brake would be autonomy."
                ),
                "trap": True,
            },
            {
                "q": "HC-SR04 wiring — why a divider?",
                "a": (
                    "TRIG is GPIO5. ECHO is 5 V. It goes through a 1 kΩ / 2 kΩ divider into GPIO18. Never wire ECHO "
                    "straight into the ESP32. The dashboard shows hobby centimetres, not a lidar map."
                ),
            },
            {
                "q": "What does MQ-7 actually report?",
                "a": (
                    "GPIO36, raw 12-bit ADC. Local HIGH if raw ≥ 2500 (MQ7_HIGH_RAW). Not carbon monoxide ppm, not methane, "
                    "not a certified gas instrument. Uncalibrated ppm would mislead a judge."
                ),
                "trap": True,
            },
            {
                "q": "Rover IMU — can it be Node B?",
                "a": (
                    "Never. Rover vibration is inspection-only, tagged device_id rover. Mixing a moving IMU into Node B "
                    "or into node Isolation Forest would poison the comparison story. This is a frequent trap question."
                ),
                "trap": True,
            },
            {
                "q": "Why Wi-Fi AP instead of ESP-NOW for the rover?",
                "a": (
                    "Drive needs request/response HTTP from the laptop. Nodes need a quiet, low-rate sensor broadcast "
                    "into USB. Mixing those paths would put rover traffic on the monitoring radio and invite feature leakage. "
                    "SSID Mine-Rover-AP, IP 192.168.4.1, open AP in firmware. Laptop must join that AP to drive. "
                    "S3-Zero USB does not carry rover commands or video."
                ),
            },
            {
                "q": "Is driving autonomous? Is there a camera?",
                "a": (
                    "No and no. Remote hold-to-move only. No camera, no vision model, no auto-brake, no SLAM. A camera "
                    "feed would not be “AI vision” unless a vision model were actually implemented — and it is not in this freeze."
                ),
                "trap": True,
            },
            {
                "q": "IR and ultrasonic disagree. Is that a bug?",
                "a": (
                    "Not necessarily. IR is a digital near-flag, not range. In simulation, IR can trip under about 12 cm "
                    "while ultrasonic “tight” is 25 cm, so they can disagree on purpose. On live hardware the pins are "
                    "independent. Dashboard explains agree_near / ir_only / sonar_only / clear. IR still does not cut motors."
                ),
            },
        ],
    },
    {
        "title": "6. Communication, freshness, and failure modes",
        "blurb": "Judges will unplug USB or ask what happens if Wi-Fi dies. Have the UNKNOWN / STOP answers ready.",
        "items": [
            {
                "q": "Why ESP-NOW channel 1, broadcast, unencrypted?",
                "a": (
                    "ESP-NOW and the receiver’s Wi-Fi STA must share a channel; we force channel 1. Broadcast to "
                    "FF:FF:FF:FF:FF:FF avoids a pairing ceremony for two nodes and one gateway on a table. It is "
                    "unencrypted and short-range. We do not claim LoRa, mesh, leaky feeder, or colliery networking."
                ),
            },
            {
                "q": "What happens if USB dies in live mode?",
                "a": (
                    "Live never falls back to simulation. The service retries the serial port every 2 seconds. Nodes "
                    "become UNKNOWN after 5 seconds without a valid packet. UNKNOWN is not green. We would rather show "
                    "“we do not know” than a fake healthy mine."
                ),
                "trap": True,
            },
            {
                "q": "What happens if rover Wi-Fi dies?",
                "a": (
                    "Firmware stops motors after about 400 ms with no repeated command. The laptop also sends STOP twice "
                    "on release or Space to beat in-flight HTTP races. Hold-to-move is the operator contract."
                ),
            },
            {
                "q": "Why 5 seconds for UNKNOWN?",
                "a": (
                    "Packets are about 1 Hz. Five seconds of silence is long enough to reject a glitch and short enough "
                    "that a dead node cannot sit on a stale NORMAL. Freshness is laptop receipt time, not a fake clock on the node."
                ),
            },
            {
                "q": "Duplicate packets?",
                "a": (
                    "Schema 1, known node_id, non-decreasing sequence. Duplicates do not refresh freshness. Junk JSON is dropped."
                ),
            },
            {
                "q": "Why can the phone app not replace the laptop website?",
                "a": (
                    "The S3-Zero arrives over USB serial. A phone cannot see that COM port. Flask on 127.0.0.1:5000 is "
                    "the operator app. No accounts, no venue cloud, no npm. Judges look at the laptop browser so nodes "
                    "and rover stay one product."
                ),
            },
            {
                "q": "Do we need venue internet?",
                "a": (
                    "No. Nodes work over USB with Wi-Fi off. Rover needs only the rover AP. sklearn runs locally. "
                    "Optional helper chatbot Pip may use a cloud key; it is not the product AI and the demo does not depend on it."
                ),
            },
        ],
    },
    {
        "title": "7. Software, dashboard, and operator workflow",
        "blurb": "Two pages on purpose. Drive controls must not appear on monitoring.",
        "items": [
            {
                "q": "What is the software stack?",
                "a": (
                    "Python 3, Flask, SQLite, numpy, scikit-learn, joblib, pyserial, requests, pytest. Charts are canvas, "
                    "not a CDN Chart.js. Bind 127.0.0.1:5000. No login. From software/: pip install -r requirements.txt, "
                    "then python app.py --mode simulate or --mode live --serial auto."
                ),
            },
            {
                "q": "Why two web pages?",
                "a": (
                    "Monitoring + AI is /monitoring (also /). Rover Inspection is /rover. If drive buttons sit on the "
                    "monitoring page, judges treat MOLE as a gamepad. The story is evidence first, inspection second."
                ),
            },
            {
                "q": "Simulate versus live — rules a judge will test?",
                "a": (
                    "Simulate is permanently labelled Rehearsal. It cannot persist-train Isolation Forest (POST /api/train "
                    "blocked). Tabletop prior .joblib files still load so IF can be READY; the UI says Tabletop prior. "
                    "Live never silently fakes data. CSV export is tagged live or sim."
                ),
            },
            {
                "q": "How do you capture baseline and slider calibration?",
                "a": (
                    "Keep mounts still. Baseline A, then Baseline B. For the slider, record ADC+mm at two ruler positions "
                    "with distinct ADC values and save two-point calibration. Node A stays UNKNOWN until that exists. "
                    "Live baselines persist in SQLite across restarts."
                ),
            },
            {
                "q": "Ack versus clear — what does the officer actually do?",
                "a": (
                    "Ack records awareness. It does not erase history and does not un-latch ALERT. Clear is allowed only "
                    "after three consecutive recovered NORMAL samples; otherwise the API returns 409. History still lists the event."
                ),
            },
            {
                "q": "What is Pip?",
                "a": (
                    "An optional local helper chatbot with a handbook and FAQ, Mistral or Ollama if a key exists. Pip is "
                    "not the SIH “AI-enabled” claim. Product AI is sklearn. If a judge points at a chat box, say that sentence first."
                ),
                "trap": True,
            },
            {
                "q": "Name the important Python modules in one breath.",
                "a": (
                    "app.py Flask and threads; engine.py ingest and snapshot; rules.py latch; anomaly.py Isolation Forest "
                    "and LOF; forecast.py holdout regression; features.py vectors; calibration.py ADC to mm; "
                    "rover_client.py HTTP to 192.168.4.1; serial_reader.py COM JSON; simulate.py rehearsal."
                ),
            },
            {
                "q": "How do you know the software contract still holds?",
                "a": (
                    "python -m pytest -q from software/. Contract tests cover simulate-cannot-train, AI cannot clear a "
                    "latch, rover packet cannot update Node B, IR does not stop motors, and honesty on collapse % / ppm."
                ),
            },
            {
                "q": "Rising trend — what is it?",
                "a": (
                    "A simulate scenario: Node A climbs, Node B stays quieter. It is the judge-friendly forecast and "
                    "localisation demo. Live equivalent is physically tilt Node A and leave Node B still."
                ),
            },
        ],
    },
    {
        "title": "8. Early-warning rules (the latch)",
        "blurb": "Say “tabletop demo numbers, not DGMS trigger levels” every time thresholds come up.",
        "items": [
            {
                "q": "State the WATCH and ALERT rules.",
                "a": (
                    "WATCH: tilt ≥ 3° or crack ≥ 2 mm, three consecutive samples. ALERT: tilt ≥ 6° or crack ≥ 4 mm, "
                    "three consecutive samples. ALERT latches. Files: software/rules.py."
                ),
            },
            {
                "q": "Why three consecutive samples?",
                "a": (
                    "A single spike can be a knock or ADC glitch. Three samples at about 1 Hz is a short persistence "
                    "check a judge can watch. It is not a geotechnical dwell time."
                ),
            },
            {
                "q": "Why latch? Why can Isolation Forest not clear it?",
                "a": (
                    "Early warning must not flicker off because a model score improved. The officer acknowledges, recovers "
                    "the mounts, and clears only after three fresh NORMAL samples. ML may add UNUSUAL. It may not hide a rule."
                ),
            },
            {
                "q": "When is a node UNKNOWN?",
                "a": (
                    "Stale more than 5 s, unseen node, invalid IMU, or Node A slider not millimetre-calibrated. UNKNOWN "
                    "is not NORMAL. Silence is not safety."
                ),
            },
            {
                "q": "Can Node B cancel Node A?",
                "a": (
                    "No. Comparison never vetoes the disturbed point. That would be a dangerous design even on a tabletop."
                ),
            },
            {
                "q": "Are 3° and 6° mine standards?",
                "a": (
                    "No. They are visible tabletop bands so a judge can tilt a board and see WATCH then ALERT. Real sites "
                    "would need surveyed mounts and approved trigger policy. We will say that even if they press for a standard."
                ),
                "trap": True,
            },
        ],
    },
    {
        "title": "9. Machine learning — the questions that win or lose “AI-enabled”",
        "blurb": (
            "Name the models. Point at features, train count or Tabletop prior, score, LOF vote, MAE. "
            "Never say collapse probability. Isolation Forest is real AI; the PS word prediction is the 30-second forecast."
        ),
        "items": [
            {
                "q": "What is the AI in this product?",
                "a": (
                    "Laptop scikit-learn only. Per node: Isolation Forest (contamination 0.05) plus Local Outlier Factor, "
                    "with StandardScaler. Joint Isolation Forest on |A−B| tilt and vibration. Holdout-selected regression "
                    "forecasts the next 30 seconds of tilt, vibration and Node A gap, with MAE. Explanations are number "
                    "templates, not an LLM. Rover IMU, IR, ultrasonic and MQ-7 are not ML features."
                ),
            },
            {
                "q": "Explain Isolation Forest so a non-ML judge gets it.",
                "a": (
                    "Liu, Ting and Zhou, IEEE ICDM 2008. The algorithm grows random trees that isolate points. Unusual "
                    "combinations of our features take fewer splits to isolate than the quiet cloud. We train on this "
                    "rig’s NORMAL behaviour. Output is UNUSUAL versus this tabletop, plus a score and the top standardised "
                    "feature — not a collapse probability."
                ),
            },
            {
                "q": "Why Isolation Forest, not a neural net or SVM?",
                "a": (
                    "We have unlabelled quiet data, not a library of mine collapses. Isolation Forest is unsupervised, "
                    "small-data friendly, inspectable, and standard in sklearn. A neural net would overclaim and overfit "
                    "thirty noisy IMU points. Judges can see feature names and a score. That is the point."
                ),
            },
            {
                "q": "What does contamination 0.05 mean here?",
                "a": (
                    "It is sklearn’s expected outlier fraction inside the forest — a sensitivity knob, not a scientific "
                    "statement that 5% of a mine is collapsing. We train only on samples rules already called NORMAL."
                ),
            },
            {
                "q": "What features go into the per-node forest?",
                "a": (
                    "tilt_change_deg, vibration_g, d_tilt (one-second rate), and Node A relative_mm once calibrated. "
                    "Node B has no millimetre feature. Features are scaled. The officer sees the names and which one "
                    "deviated most."
                ),
            },
            {
                "q": "Why add Local Outlier Factor?",
                "a": (
                    "LOF compares local density to neighbours. Isolation Forest isolates globally with random partitions. "
                    "Together they vote. The dashboard shows Isolation Forest state, LOF state, and vote count. LOF is "
                    "support, not a second product."
                ),
            },
            {
                "q": "What is the joint forest?",
                "a": (
                    "A third Isolation Forest on [abs(A_tilt−B_tilt), abs(A_vib−B_vib)]. Patterns such as QUIET, LOCAL_A, "
                    "LOCAL_B, COMMON. It is a localisation hint: did one mount move or did the whole model move? It is "
                    "not a geology or fault model."
                ),
            },
            {
                "q": "INACTIVE / READY / UNUSUAL?",
                "a": (
                    "INACTIVE: no usable model. READY: model loaded, current vector not flagged unusual. UNUSUAL: forest "
                    "and/or LOF flag this combination versus trained normal. Tabletop priors ship READY without waiting "
                    "120 live samples; the label is Tabletop prior, not “trained on a real mine”."
                ),
            },
            {
                "q": "When are you allowed to retrain live?",
                "a": (
                    "Live mode only, at least 120 NORMAL samples per node, blocked if WATCH, ALERT, UNKNOWN or simulate. "
                    "Writes nodeN.joblib and overrides the prior until reset. Simulate cannot persist-train so a rehearsal "
                    "cannot pretend to be a field model."
                ),
            },
            {
                "q": "Are the shipped priors a real-mine model?",
                "a": (
                    "No. artifacts/node1.prior.joblib, node2.prior.joblib and joint.prior.joblib describe synthetic "
                    "quiet-tabletop NORMAL so a demo can start READY. After a physical baseline, scores may be noisy "
                    "until optional live retrain on that MPU."
                ),
                "trap": True,
            },
            {
                "q": "The PS says prediction. What did you actually build?",
                "a": (
                    "Sensor-trend prediction: last roughly 30–60 one-hertz points; candidates Ridge, HuberRegressor, "
                    "LinearRegression versus a persistence baseline; holdout MAE picks the winner; horizon is the next "
                    "30 samples of the same signals. On-screen label: 30 s sensor trend forecast — not a collapse prediction. "
                    "Mine-subsidence or collapse prediction is not claimed. That needs surveyed mounts, labelled events and geotech validation."
                ),
                "trap": True,
            },
            {
                "q": "Why 30 seconds, not 30 minutes or 30 days?",
                "a": (
                    "The officer is watching a live heading. Thirty seconds is long enough to see a dashed line and check "
                    "MAE, short enough that a linear model on IMU noise is honest. Multi-day subsidence is InSAR and survey "
                    "territory. We will not put a 30-day roof forecast on the screen."
                ),
            },
            {
                "q": "Why holdout MAE instead of always using Ridge?",
                "a": (
                    "Quiet data can be almost flat; LinearRegression or persistence may win with tiny MAE. Huber is robust "
                    "to spikes but may fail to converge — it is a candidate, not sacred. Holdout MAE is the evidence the "
                    "officer sees. We do not hide a worse model behind a brand name."
                ),
            },
            {
                "q": "What is the persistence baseline?",
                "a": (
                    "The naive forecast “next value equals last value”. If Ridge cannot beat that on holdout MAE, we should "
                    "not brag. Showing the competition is part of not doing decorative AI."
                ),
            },
            {
                "q": "Time-to-WATCH / time-to-ALERT — is that a collapse clock?",
                "a": (
                    "Only if the fitted slope heads toward the tabletop threshold. Otherwise it is null. Even then it is "
                    "“if this rate holds on these signals”, not “roof fails in N minutes”. Quiet or falling slope must not invent a countdown."
                ),
                "trap": True,
            },
            {
                "q": "MAE is nearly zero. Are you overfitting?",
                "a": (
                    "On a flat quiet signal, predicting “stays flat” has MAE near 0. That is a boring truth, not magic. "
                    "Say that sentence. Do not call it 99% accuracy."
                ),
            },
            {
                "q": "Why not LSTM / Prophet / ChatGPT for prediction?",
                "a": (
                    "Thirty noisy points, no labelled disasters, offline laptop, inspectable MAE. An LLM inventing geology "
                    "is exactly the AI slop this PS should not reward. Pip, if shown, is a helper for operators, not the mine model."
                ),
            },
            {
                "q": "Can UNUSUAL exist while rules are still NORMAL?",
                "a": (
                    "Yes. That is the point of the forest: unusual combination below the 3° latch. The officer sees both "
                    "columns. Conversely, a latched ALERT stays even if the forest later looks quiet."
                ),
            },
            {
                "q": "n_estimators, random_state — any numbers to remember?",
                "a": (
                    "IsolationForest n_estimators=100, contamination=0.05, random_state=0, plus StandardScaler. "
                    "MIN_TRAIN live = 120 samples. Forecast HORIZON = 30, lag features from the last 6 samples plus mean and delta."
                ),
            },
        ],
    },
    {
        "title": "10. Honesty traps — answer these slowly",
        "blurb": "If you only memorise one section, memorise this one. Wrong answers here sink an otherwise working demo.",
        "items": [
            {
                "q": "Green / NORMAL — is the mine safe?",
                "a": (
                    "NORMAL means fresh valid packets and no configured tabletop trigger. It does not certify a mine, a roof, "
                    "or a workplace as safe. Hobby electronics are not approved for an explosive atmosphere."
                ),
                "trap": True,
            },
            {
                "q": "Give me the probability the roof will collapse.",
                "a": (
                    "We do not produce collapse or subsidence probability. Isolation Forest scores unusual versus this rig’s "
                    "normal. The forecast is the next 30 seconds of measured signals with MAE. Those are different claims."
                ),
                "trap": True,
            },
            {
                "q": "The ground sank 10 cm. Can you show that?",
                "a": (
                    "No. Tilt is orientation change from baseline. The slider is a model gap in millimetres after ruler "
                    "calibration. Neither is vertical geodetic settlement."
                ),
                "trap": True,
            },
            {
                "q": "What is the CO reading in ppm?",
                "a": (
                    "We do not quote ppm from this MQ-7. You will see raw ADC and a local NORMAL/HIGH flag at threshold 2500."
                ),
                "trap": True,
            },
            {
                "q": "Does IR stop the rover automatically?",
                "a": (
                    "No. IR is a flag. Motors stop when the officer releases, hits Space, or the 400 ms watchdog fires. "
                    "Auto-stop on IR would be autonomy we did not build and did not test as a safety function."
                ),
                "trap": True,
            },
            {
                "q": "You used LoRa / 4G / a mine leaky feeder, right?",
                "a": (
                    "No. Nodes are ESP-NOW tabletop into USB. Rover is a local Wi-Fi AP. Field radios are future work after "
                    "an RF and approvals survey."
                ),
                "trap": True,
            },
            {
                "q": "Show me the AI camera.",
                "a": (
                    "There is no camera in this freeze. Inspection is centimetres, IR flag, MQ-7 raw, rover IMU. A JPEG "
                    "on a phone is not computer vision."
                ),
                "trap": True,
            },
            {
                "q": "Your chatbot is the AI, yes?",
                "a": (
                    "No. sklearn on the laptop is the product AI. A helper named Pip answers from a handbook. If the chat "
                    "box is off, Isolation Forest and the forecast still run."
                ),
                "trap": True,
            },
            {
                "q": "If USB fails, do you keep showing the last nice chart as live?",
                "a": (
                    "No. Nodes go UNKNOWN. Live mode does not switch to simulation. Simulation, when used, is bannered."
                ),
                "trap": True,
            },
            {
                "q": "How many lives will this save?",
                "a": (
                    "We do not know and we will not invent a number. Benefit a judge can verify: see A versus B, see why "
                    "a warning latched, see model names and MAE, inspect without entering the model tunnel first, keep a CSV history."
                ),
                "trap": True,
            },
        ],
    },
    {
        "title": "11. Feasibility, cost, scale, and field path",
        "blurb": "SIH scoring cares about feasibility. Be concrete about what is in the repo versus what still needs a soldering iron.",
        "items": [
            {
                "q": "Can you actually demo this week?",
                "a": (
                    "Firmware sketches, Flask site, rules, IF+LOF+joint, holdout forecast, priors, simulate scenarios and "
                    "rover proxy are in the repository. Hardware day still requires: wire the freeze (especially echo divider "
                    "and GPIO19 = IR), flash four boards, prove JSON on the S3-Zero at 115200, live baseline and slider cal, "
                    "join Mine-Rover-AP, polarity test, STOP watchdog. SIH26025 is Hardware — extra sklearn does not replace working boards."
                ),
            },
            {
                "q": "You already have the parts. What did “low cost” mean?",
                "a": (
                    "ESP32-class COTS, no cloud bill, no licence server. We do not put a ₹ BOM on the idea PPT and we do "
                    "not block the story on an old ₹4,000 node-only figure. Low-cost is the architecture, not a shopping-channel claim."
                ),
            },
            {
                "q": "How would this scale to a real mine?",
                "a": (
                    "More surveyed nodes, site-calibrated thresholds, approved sensing and comms (possibly leaky feeder, "
                    "mesh, or mine LTE — after RF survey), integration with existing strata monitoring, labelled events "
                    "before any collapse model, intrinsically safe enclosures. That is a multi-year instrumentation project. "
                    "Today is the tabletop loop that proves the software split: measure on the edge, decide and learn on a local computer, inspect on command."
                ),
            },
            {
                "q": "Power and battery?",
                "a": (
                    "Demo is USB or bench supplies and a rover pack. We do not claim shift-long intrinsically safe batteries. "
                    "If they ask field power: that is part of the approved-equipment path, not this prototype."
                ),
            },
            {
                "q": "Range through rock?",
                "a": (
                    "Not demonstrated. ESP-NOW and a 2.4 GHz AP across a table are not a colliery RF design. We will not "
                    "quote a kilometre figure."
                ),
            },
            {
                "q": "Cybersecurity? Open AP?",
                "a": (
                    "Tabletop only. ESP-NOW is unencrypted. Rover AP has no password in firmware so a demo laptop can join "
                    "without a sticky note. A field system would need authenticated radios and a closed network. We do not "
                    "pretend the prototype is hardened OT."
                ),
            },
            {
                "q": "Main risks, spoken?",
                "a": (
                    "Over-claiming tilt as settlement. Mixing rover IMU into nodes. False comfort from a dead sensor — "
                    "mitigated by UNKNOWN. Uncalibrated slider — Node A cannot go NORMAL. IR/ultrasonic disagreement — "
                    "explained, no auto-brake. Hobby electronics underground — out of scope."
                ),
            },
            {
                "q": "Intellectual property / open source?",
                "a": (
                    "Implementation is in the public WECOOK-MOLE repository for the hackathon. Isolation Forest is a published "
                    "algorithm; sklearn is BSD-licensed. We are not selling a certified product in this round."
                ),
            },
            {
                "q": "What is explicitly leftover?",
                "a": (
                    "Physical flashing, COM port on the venue laptop, ESP-NOW reliability across the table, slider mechanics, "
                    "motor polarity, echo divider on the real board, IR aiming, AP join, live baseline, optional live retrain. "
                    "Camera, LoRa, ppm, autonomy, collapse % remain out of scope unless the freeze is formally changed."
                ),
            },
        ],
    },
    {
        "title": "12. Demo script, SIH process, and 36-hour questions",
        "blurb": "Internal college rounds often ask “what have you built so far?” and “what will you do in 36 hours?” Answer with artifacts, not hope.",
        "items": [
            {
                "q": "Show me the judge demo, step by step.",
                "a": (
                    "1) Both nodes updating; say SIH26025: monitor, warn, inspect. 2) Point at Isolation Forest, prior or "
                    "train count, features, forecast MAE; say not collapse percent. 3) Rising trend or tilt Node A; keep B "
                    "quieter. 4) WATCH then ALERT with the measured reason; rules and ML side by side. 5) Open Rover Inspection "
                    "because a warning appeared. 6) Wheels up; hold FWD; STOP; centimetres, IR, MQ-7 raw; IR does not auto-brake. "
                    "7) Ack; recover; clear after three NORMAL; history remains."
                ),
            },
            {
                "q": "Hardware fails during judging. What then?",
                "a": (
                    "python app.py --mode simulate, Rehearsal banner visible, same two pages, Rising trend. Say clearly it "
                    "is labelled simulation. Do not pass sim off as USB. Isolation Forest still loads tabletop priors; persist-train stays blocked."
                ),
            },
            {
                "q": "What is already built versus what 36 hours would add?",
                "a": (
                    "Already built: firmware, local website, ML, tests, idea PPT. A grand-finale 36 hours is integration "
                    "and reliability — flash, mounts, calibration, radio, rover polarity, a quiet 2-minute live retrain if "
                    "time — not a new architecture. We will not promise LoRa or a camera overnight."
                ),
            },
            {
                "q": "Why this team of six?",
                "a": (
                    "Split by unit, not “everyone codes”: Node A mount and slider; Node B and table mechanics; S3-Zero radio "
                    "and USB; rover mechanics and payload; laptop ingest/rules/rover proxy; dashboard, ML evidence, pitch. "
                    "There is no fourth monitoring node for the sixth person."
                ),
            },
            {
                "q": "What goes on the SIH portal?",
                "a": (
                    "PDF of the official six slides only. ID SIH26025. This Q&A PDF and the long judge document stay with "
                    "the team and the SPOC. They are not a seventh slide."
                ),
            },
            {
                "q": "Spoken close — the sentence to end on?",
                "a": (
                    "Isolation Forest and LOF flag unusual combinations versus this rig’s learned normal. A joint forest "
                    "watches A versus B residual. Holdout-selected sklearn regression forecasts the next 30 seconds of those "
                    "same signals with MAE. Rules remain the independent early-warning latch. The rover is remote inspection, not autonomy."
                ),
            },
            {
                "q": "Name the references you actually use.",
                "a": (
                    "Liu, Ting, Zhou — Isolation Forest, ICDM 2008. scikit-learn Ridge / Huber / LinearRegression and MAE. "
                    "InvenSense MPU-6000/6050 spec. Espressif ESP-NOW guide and ESP32 ADC1 notes. Waveshare ESP32-S3-Zero wiki. "
                    "MQ-7 datasheet as raw ADC. GitHub WECOOK-MOLE. CMR 2017 and DGMS (S&T) Circ. 01/2017 cl. 6.1 as context only."
                ),
            },
            {
                "q": "If a mentor says add camera, LoRa, and collapse percent tonight?",
                "a": (
                    "We will not. Those contradict the hardware freeze and the honesty table. We can discuss them as a "
                    "field roadmap. Shipping a fake percent would fail the PS more badly than a smaller honest demo."
                ),
            },
        ],
    },
]

RAPID_FIRE = [
    ["Official ID", "SIH26025 (never SIH2026025)"],
    ["Team / idea", "WE COOK / MOLE — Mine Observation & Live-alert Engine"],
    ["User", "Safety officer on a tabletop model"],
    ["Boards", "ESP32 A, ESP32 B, Waveshare S3-Zero, ESP32 rover"],
    ["Node radio", "ESP-NOW ch 1 broadcast → USB JSON 115200"],
    ["Rover radio", "Wi-Fi AP Mine-Rover-AP, 192.168.4.1"],
    ["WATCH", "3° or 2 mm, 3 samples (tabletop)"],
    ["ALERT", "6° or 4 mm, 3 samples, latches"],
    ["UNKNOWN", "Stale > 5 s, bad IMU, A uncalibrated"],
    ["Clear", "3 fresh NORMAL; ack ≠ clear"],
    ["AI", "sklearn IF + LOF + joint IF + 30 s forecast"],
    ["Prediction", "Next 30 s of signals + MAE, not collapse %"],
    ["Priors", "Quiet tabletop, labelled Tabletop prior"],
    ["Live train", "≥120 NORMAL, live only, not in sim"],
    ["IR", "GPIO19 LOW=near; does not stop motors"],
    ["MQ-7", "Raw ADC, HIGH ≥ 2500, not ppm"],
    ["ECHO", "GPIO18 after 1k/2k divider"],
    ["L298N", "IN 13/12/14/27; GPIO19 is not IN4"],
    ["Green", "Fresh data, no tabletop trigger — not “mine safe”"],
    ["Pitch order", "Monitor → warn → inspect on command"],
]

NEVER_SAY = [
    "The mine is safe / certified / collapse imminent",
    "Collapse probability, risk score, or “87% chance”",
    "Roof will fail in N minutes (as a geotech claim)",
    "The ground sank X centimetres from MPU tilt",
    "CO ppm from this MQ-7",
    "Autonomous navigation / auto-brake / lidar map",
    "Camera vision AI",
    "LoRa / mesh / kilometre range (not built)",
    "SIH2026025",
    "Optional rover or decorative AI badge",
    "Node B is a surveyed geodetic reference",
    "Rover IMU is Node B",
    "Lives saved / disasters averted (invented)",
    "DGMS-approved instrument (this prototype is not)",
]

ALWAYS_SAY = [
    "Tabletop demonstration, not a certified mine",
    "Disturbance, not proven collapse or named cause",
    "Rules latch; ML cannot clear a red warning",
    "30 s sensor forecast — not a collapse prediction",
    "Two radios: ESP-NOW/USB nodes, Wi-Fi AP rover",
    "Green = fresh valid data, not a safe mine",
]
