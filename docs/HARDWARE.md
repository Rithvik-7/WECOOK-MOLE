# Hardware and capability manifest

Updated 29 September 2026. Every board is an ESP32-S3. The parts below replace the earlier node list. Pin-by-pin connections are in `docs/WIRING.md`. Those pins are the ESP32-S3 plan. Classic ESP32 GPIO 22, 25, 34 and 35 are not used.

| Unit | Role | Parts now specified | Readings the software may show | Not claimed |
|---|---|---|---|---|
| Node 1 (A) | Surface motion | ESP32-S3, MPU, slider | Tilt, vibration summary, slider counts | Millimetres until the slider is fixed and calibrated |
| Node 2 (B) | Surface motion and air temperature | Classic ESP32, MPU-6050, DS18B20 | Tilt, vibration summary, air temperature in °C | Rain, soil moisture, groundwater |
| Node 3 (C) | Motion, displacement, gas | Classic ESP32, MPU-6050, 10 kΩ slider, MQ-2 | Tilt, vibration, slider counts, MQ-2 raw gas after warm-up | Gas concentration. Millimetres |
| Node 4 (D) | Local alarm and climate | Classic ESP32, buzzer, LCD, BMP280 | °C, hPa, local temperature text | Humidity, tilt until an MPU is fitted. Rain, soil moisture, groundwater, rock pressure |
| Receiver | Star collector | ESP32-S3 on the laptop USB port, MAC `a0:f2:62:f4:66:d0` | Highest active warning on USB serial | Cloud buffering on the receiver |
| Rover R1 | Inspection only | Not part of these four nodes | Mission records | Driving |

## Radio

Nodes send to the receiver. That is a star. It is not a mesh.

## Data rules

Slider counts and linear-sensor counts are not millimetres. MQ-2 is a warmed-up raw gas signal. A missing reading is unavailable, not zero. An offline node is not normal.
