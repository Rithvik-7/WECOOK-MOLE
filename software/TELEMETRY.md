# USB JSON from the Waveshare ESP32-S3-Zero (115200, one object per line)

Node A:
{"type":"telemetry","schema":1,"node_id":1,"seq":17,"uptime_ms":17000,"gateway_ms":18500,"valid":7,"roll_deg":0.12,"pitch_deg":-0.08,"vibration_g":0.004,"adc_raw":2048}

Node B:
{"type":"telemetry","schema":1,"node_id":2,"seq":17,"uptime_ms":17000,"gateway_ms":18500,"valid":5,"roll_deg":0.03,"pitch_deg":0.06,"vibration_g":0.003,"adc_raw":null}

valid bitmask: IMU=1, potentiometer=2, vibration window=4. Healthy A=7, healthy B=5.
Invalid fields are null. Laptop receipt time governs freshness.

Run the website:

```powershell
cd software
python -m pip install -r requirements.txt
python app.py --mode simulate
python app.py --mode live --serial auto
python app.py --mode live --serial COM5
```

Open:

- Monitoring + AI: http://127.0.0.1:5000/monitoring
- Separate rover control: http://127.0.0.1:5000/rover

No login. Live mode reconnects USB after errors; it never falls back to simulation.

Arduino:
  Node A/B / rover: ESP32 Dev Module
  Receiver: Waveshare ESP32-S3-Zero or ESP32S3 Dev Module, USB CDC On Boot = Enabled
  Node A: NODE_ID 1, HAS_POT 1
  Node B: NODE_ID 2, HAS_POT 0

Rover HTTP at 192.168.4.1:

```text
GET /forward /backward /left /right /stop
GET /telemetry
```

The laptop site uses POST `/api/rover/<command>` and proxies that to the rover.
Rover telemetry uses `device_id:"rover"` and never enters the Node A/B ML features.
