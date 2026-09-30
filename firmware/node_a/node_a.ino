// Node 1 / A. Classic ESP32 Dev Module (CP210x USB), same family as Nodes 2-4.
// MPU-6050: SDA GPIO 21, SCL GPIO 22, VCC 3.3 V, GND.
// Slider: one end 3.3 V, other end GND, wiper GPIO 34.
// Board: ESP32 Dev Module. Serial: 115200.
#define MOLE_NODE_ID 'A'
#define MOLE_HAS_SLIDER 1
#define MOLE_I2C_SDA 21
#define MOLE_I2C_SCL 22
#define MOLE_SLIDER_PIN 34
#define MOLE_BOARD_LABEL "ESP32"
#include "../common/mole_node.hpp"

void setup() { mole_setup(); }
void loop() { mole_loop(); }
