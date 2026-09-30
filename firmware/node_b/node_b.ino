// Node 2 / B. Classic ESP32 Dev Module (CP210x USB), not the ESP32-S3 receiver.
// MPU-6050: SDA GPIO 21, SCL GPIO 22, VCC 3.3 V, GND.
// DS18B20: VCC 3.3 V, GND, data GPIO 4, and a 4.7 kΩ resistor from data to 3.3 V.
// Board: ESP32 Dev Module. Port: the CP210x COM port. Serial: 115200.
#define MOLE_NODE_ID 'B'
#define MOLE_HAS_DS18B20 1
#define MOLE_I2C_SDA 21
#define MOLE_I2C_SCL 22
#define MOLE_DS18B20_PIN 4
#define MOLE_BOARD_LABEL "ESP32"
#include <OneWire.h>
#include <DallasTemperature.h>
#include "../common/mole_node.hpp"

void setup() { mole_setup(); }
void loop() { mole_loop(); }
