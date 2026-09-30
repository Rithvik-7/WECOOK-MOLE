// Node 3 / C. Classic ESP32 Dev Module, same family as Node 2.
// MPU-6050: SDA GPIO 21, SCL GPIO 22, VCC 3.3 V, GND.
// 10 kΩ slider: one end 3.3 V, other end GND, wiper GPIO 34.
// MQ-2: heater VCC 5 V, GND shared, analog output GPIO 35. Keep that pin at or below 3.3 V.
// Board: ESP32 Dev Module. Serial: 115200.
#define MOLE_NODE_ID 'C'
#define MOLE_HAS_SLIDER 1
#define MOLE_HAS_GAS 1
#define MOLE_I2C_SDA 21
#define MOLE_I2C_SCL 22
#define MOLE_SLIDER_PIN 34
#define MOLE_GAS_PIN 35
#define MOLE_BOARD_LABEL "ESP32"
#include "../common/mole_node.hpp"

void setup() { mole_setup(); }
void loop() { mole_loop(); }
