# Node wiring and mounting

Saved 29 September 2026. Every board, including the four nodes, is an ESP32-S3. This is the build plan, not a field certificate. The receiver MAC is `a0:f2:62:f4:66:d0`.

ESP32-S3 does not have GPIO 22 or GPIO 25. Its ADC pins that stay valid with ESP-NOW are GPIO 1–10. GPIO 19 and 20 are the USB pins. Do not use them for sensors.

| Project node | Software id | Parts |
|---|---|---|
| Node 1 | A | ESP32-S3, MPU, slider |
| Node 2 | B | Classic ESP32, MPU-6050, DS18B20 |
| Node 3 | C | Classic ESP32, MPU-6050, 10 kΩ slider, MQ-2 |
| Node 4 | D | Classic ESP32, MPU-6050, buzzer, LCD, BME280 |

Node 2 is a classic ESP32. Its temperature sensor is a DS18B20 and reports degrees Celsius, not rainfall or soil moisture. The slider and the linear sensor report raw counts until they are mechanically fixed and calibrated. The MQ-2 reports a raw gas signal after warm-up, not a concentration. The BME reports temperature, humidity, and pressure only.

## Power rules

- MPU, BME, slider, linear sensor, and the LCD I2C backpack use 3.3 V from the ESP32-S3.
- Share one ground on every node.
- The MQ-2 heater uses 5 V. Its analog output must stay at or below 3.3 V before it touches an ESP32-S3 pin.
- Analog sensors use GPIO 4, 5 and 6. Those are ADC1 pins and stay readable while ESP-NOW is on.

## Shared I2C bus

Every node uses the same two wires for the MPU.

| Signal | ESP32-S3 pin |
|---|---|
| SDA | GPIO 8 |
| SCL | GPIO 9 |
| Power | 3.3 V |
| Ground | GND |

On Node 4 the BME and the I2C LCD join this same pair. Typical addresses: MPU `0x68`, BME `0x76` or `0x77`, LCD backpack `0x27`.

```text
ESP32-S3 GPIO 8 ---- SDA of MPU, and on Node 4 also BME and LCD
ESP32-S3 GPIO 9 ---- SCL of MPU, and on Node 4 also BME and LCD
ESP32-S3 3.3 V  ---- VCC of those boards
ESP32-S3 GND    ---- GND of those boards
```

## Node 1 — ESP32, MPU, slider

| Part | Connection |
|---|---|
| MPU | I2C bus above |
| Slider end 1 | 3.3 V |
| Slider end 2 | GND |
| Slider wiper | GPIO 4 |

```text
3.3 V ---- slider end
GND   ---- slider end
GPIO 4 -- slider wiper
```

The slider is a position input in counts. Millimetres are unavailable until the slider is fixed to the surface mechanism and calibrated.

## Node 2 — classic ESP32, MPU-6050, DS18B20

This board is the CP210x ESP32, not an ESP32-S3. Its I2C pins are GPIO 21 and GPIO 22.

| Part | Connection |
|---|---|
| MPU-6050 SDA | GPIO 21 |
| MPU-6050 SCL | GPIO 22 |
| MPU-6050 VCC | 3.3 V |
| MPU-6050 GND | GND |
| DS18B20 VCC | 3.3 V |
| DS18B20 GND | GND |
| DS18B20 data | GPIO 4 |
| 4.7 kΩ resistor | GPIO 4 to 3.3 V |

```text
3.3 V ---- MPU VCC, DS18B20 VCC, and one end of the 4.7 kΩ resistor
GND   ---- MPU GND and DS18B20 GND
GPIO 21 -- MPU SDA
GPIO 22 -- MPU SCL
GPIO 4 --- DS18B20 data and the other end of the 4.7 kΩ resistor
```

The DS18B20 reading is air temperature in degrees Celsius. It is not rainfall, soil moisture, or groundwater.

## Node 3 — classic ESP32, MPU-6050, 10 kΩ slider, MQ-2

This board uses the same classic ESP32 pins as Node 2. GPIO 34 and GPIO 35 are input-only analog pins.

| Part | Connection |
|---|---|
| MPU-6050 SDA | GPIO 21 |
| MPU-6050 SCL | GPIO 22 |
| MPU-6050 VCC | 3.3 V |
| MPU-6050 GND | GND |
| Slider end 1 | 3.3 V |
| Slider end 2 | GND |
| Slider wiper | GPIO 34 |
| MQ-2 heater VCC | 5 V |
| MQ-2 GND | GND, common with the ESP32 |
| MQ-2 analog out | GPIO 35 |

```text
3.3 V ---- MPU VCC and one end of the 10 kΩ slider
GND   ---- MPU GND, the other slider end, and MQ-2 GND
5 V   ---- MQ-2 heater VCC
GPIO 21 -- MPU SDA
GPIO 22 -- MPU SCL
GPIO 34 -- slider wiper
GPIO 35 -- MQ-2 analog output
```

The slider count is not millimetres. The MQ-2 analog pin must stay at or below 3.3 V. Keep the sensor in open air. Its gas reading is ignored for 60 seconds after power-up, and it is a raw count, not a concentration.

## Node 4 — classic ESP32, MPU-6050, BME280, LCD, buzzer

The MPU, BME280, and LCD backpack share one I2C bus. Typical addresses: MPU `0x68`, BME `0x76` or `0x77`, LCD `0x27` or `0x3F`.

| Part | Connection |
|---|---|
| SDA | GPIO 21 |
| SCL | GPIO 22 |
| VCC | 3.3 V |
| GND | GND |
| Buzzer signal | GPIO 25 |
| Buzzer power | 3.3 V or 5 V, as printed on that module |
| Buzzer ground | GND |

```text
GPIO 21 -- SDA of MPU, BME280, and LCD
GPIO 22 -- SCL of MPU, BME280, and LCD
GPIO 25 -- buzzer signal
3.3 V / GND -- MPU, BME280, LCD, and buzzer ground
```

The LCD may say `NORMAL`. It must not say the mine is safe. The buzzer is a short pulse, not a loop that freezes the radio. The BME280 reports air temperature, humidity, and pressure only.

## How to fix the hardware

1. Mount each ESP32 on its own rigid plate, antenna clear of metal.
2. Mark the MPU axes on the plate before tightening it. The same face should point the same way on every node.
3. Fix Node 1 and Node 3 sliders to the moving piece they measure. Leave the wiper free to travel the whole slot. Do not convert counts to millimetres until that travel is measured.
4. Keep the MQ-2 upright, holes open to the air, and its wires away from the slider.
5. Fix the MQ-2 upright, holes open, away from the enclosure wall. Allow warm-up before trusting the gas channel.
6. Fix Node 2’s temperature sensor in free air beside the MPU, not buried, and not used as a ground-movement sensor.
7. Fix Node 4 where a person can read the LCD and hear the buzzer. Keep the BME out of direct sun and out of a sealed box.
8. Give every node a stable 5 V supply if it must feed an MQ-2 heater. The ESP32-S3 itself still talks at 3.3 V.
9. Point every node’s ESP-NOW radio at the receiver MAC `a0:f2:62:f4:66:d0`. This is a star. Nodes do not relay each other.
10. After mounting, record which physical spot is Node 1, 2, 3, and 4. Those places are still not survey coordinates.

## What is saved, and what is still open

Saved here: the four parts lists, the pin plan, the receiver MAC, and the mounting order.

Still open before this sheet becomes a flashed wiring contract: the LCD backpack address if it is not `0x27`, and the BME address if it is not `0x76`.
