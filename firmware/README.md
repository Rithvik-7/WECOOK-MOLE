# ESP32-S3 firmware

The receiver and all four nodes are ESP32-S3 boards. Nodes send to the receiver. The receiver does not relay them. Its USB serial line is the laptop gateway.

Receiver MAC used by every node: `a0:f2:62:f4:66:d0`

| Sketch | Board | Parts |
|---|---|---|
| `firmware/receiver/receiver.ino` | Receiver, plugged into the laptop | ESP-NOW collector, USB serial |
| `firmware/node_a/node_a.ino` | Node 1 / A | MPU-6050, slider |
| `firmware/node_b/node_b.ino` | Node 2 / B | MPU-6050, temperature signal |
| `firmware/node_c/node_c.ino` | Node 3 / C | MPU-6050, slider, MQ-2, linear sensor |
| `firmware/node_d/node_d.ino` | Node 4 / D | MPU-6050, BME280, I2C LCD, buzzer |

## Pins

These are ESP32-S3 pins. GPIO 22 and GPIO 25 do not exist on this chip.

| Signal | GPIO |
|---|---|
| I2C SDA (MPU, and on Node D the BME and LCD) | 8 |
| I2C SCL | 9 |
| Slider wiper, Nodes A and C | 4 |
| Temperature signal, Node B | 4 |
| Linear sensor, Node C | 5 |
| MQ-2 analog output, Node C | 6 |
| Buzzer, Node D | 10 |

Power the MPU, BME, slider, linear sensor, and LCD from 3.3 V. The MQ-2 heater uses 5 V, and its analog pin must stay at or below 3.3 V. Share one ground. Mount every MPU flat with the same face up. Tilt is the angle away from that face.

The Node B temperature module is still unnamed. The sketch reports an ADC count, not degrees. The linear sensor is also a count, not millimetres. MQ-2 stays a raw count, and the gas rule waits 60 seconds after boot.

The Node D LCD may say `NORMAL`. It does not say the mine is safe. The buzzer is a 200 ms pulse.

## Flash

1. Install the ESP32 board package in the Arduino IDE.
2. Board: **ESP32S3 Dev Module**.
3. USB CDC On Boot: **Enabled**.
4. Open one sketch folder, select the COM port for that board, and upload.
5. Flash the receiver that is already on the laptop first, then each node.
6. Serial Monitor at **115200**. The receiver's first line is its MAC. It should be `a0:f2:62:f4:66:d0`. If it is different, put the printed MAC into `MOLE_RECEIVER_MAC` in `firmware/common/mole_packet.h` and flash the nodes again.

No extra Arduino libraries are required. The MPU, BME, and LCD are driven from the sketch.

## Laptop

```powershell
python -m pip install pyserial
python firmware/receiver/serial_bridge.py COM3
```

Replace `COM3` with the port Windows shows for the receiver. The bridge stamps the clock once, when the line first arrives, then the gateway queue sends it to the API. Lines that begin with `"unit":"receiver"` are status only and are not stored as node readings.
