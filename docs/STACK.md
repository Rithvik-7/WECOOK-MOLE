# Stack — what MOLE actually uses

Nothing here requires venue internet for the **core demo**. The operator website is local Flask. Optional Pip helper can call Mistral if a key is present; that chatbot is **not** the product AI.

## Local websites (this laptop)

| URL | Page |
|---|---|
| http://127.0.0.1:5000/ | Monitoring + AI (same as `/monitoring`) |
| http://127.0.0.1:5000/monitoring | Node A / Node B, rules, Isolation Forest, 30 s forecast |
| http://127.0.0.1:5000/rover | Hold-to-move drive + inspection sensors |
| http://127.0.0.1:5000/api/state | JSON snapshot |
| http://127.0.0.1:5000/api/rover/state | Rover proxy status |
| http://127.0.0.1:5000/api/export.csv | Tagged live/sim history |
| http://192.168.4.1/ | Rover AP (only after joining **Mine-Rover-AP**) |

No login. No cloud dashboard. No npm build.

## Languages and runtimes

| Piece | Choice |
|---|---|
| Nodes, receiver, rover | C++ Arduino sketches (`Wire`, `WiFi`, `esp_now`, rover `WebServer`) |
| Laptop | Python 3 + Flask |
| ML | scikit-learn on the laptop only |
| Store | SQLite |
| Charts | Canvas (no Chart.js CDN) |
| Tests | pytest |

Python packages: see [`software/requirements.txt`](../software/requirements.txt) — Flask, pyserial, requests, numpy, scikit-learn, joblib, pytest.

## Hardware (frozen)

| Unit | Board / parts |
|---|---|
| Node A | Classic ESP32-WROOM-32, MPU6050 (GPIO21/22, 0x68), 10 kΩ slider → 1 kΩ → GPIO34 |
| Node B | Same ESP32 + MPU, no slider |
| Receiver | **Waveshare ESP32-S3-Zero**, ESP-NOW ch 1 → USB-C JSON 115200 |
| Rover | Classic ESP32, L298N (IN1=13 IN2=12 IN3=14 IN4=27, **ENA/ENB jumpers ON**), MPU, HC-SR04 TRIG=5 ECHO=18 via divider, MQ-7 AO=36 raw, IR GPIO19 |

## Websites and references we used (not a product dependency)

| Site / document | Why |
|---|---|
| [Smart India Hackathon](https://www.sih.gov.in/) | Problem **SIH26025**, 6-slide idea template |
| [Ministry of Coal](https://coal.nic.in/) | Problem owner (disaster management / mine safety context) |
| [scikit-learn IsolationForest](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html) | Anomaly vs this rig’s normal |
| [scikit-learn Ridge](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html) | Candidate 30 s sensor forecast |
| Liu, Ting, Zhou — Isolation Forest (ICDM 2008) | Named detector, not a collapse model |
| [Espressif ESP-NOW](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/network/esp_now.html) | Node radio, channel 1 broadcast |
| [Arduino-ESP32](https://docs.espressif.com/projects/arduino-esp32/) | Board package / USB CDC on S3 |
| [Waveshare ESP32-S3-Zero](https://www.waveshare.com/wiki/ESP32-S3-Zero) | Receiver board |
| InvenSense MPU-6050 datasheet | Tilt / vibration proxy |
| ST / generic HC-SR04 notes | Rover distance; 5 V echo **must** be divided |
| MQ-7 datasheet | Analog heater sensor; we show **raw ADC**, not ppm |
| L298N module notes | Dual H-bridge; jumpers enable motors |
| Silicon Labs CP210x | USB-UART on classic DevKits |
| [Flask](https://flask.palletsprojects.com/) | Local operator site |
| [Mistral API](https://docs.mistral.ai/) | Optional Pip helper only (`software/.env.example`) |
| [GitHub WECOOK-MOLE](https://github.com/Rithvik-7/WECOOK-MOLE) | Source of truth for this build |

DGMS circulars and mine-science papers are **context** for the problem, not implemented certification.

## What we deliberately do not use

Camera / vision models, LoRa, login, cloud hosting, Chart.js CDN, TensorFlow, ChatGPT as geology, CO ppm conversion, autonomous navigation.
