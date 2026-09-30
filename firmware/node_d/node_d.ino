// Node 4 / D. Classic ESP32 Dev Module.
// MPU-6050, BME280, and the I2C LCD share SDA GPIO 21 and SCL GPIO 22, at 3.3 V.
// Buzzer signal: GPIO 25. Module VCC is 3.3 V or 5 V, as printed on that module.
// The LCD may say NORMAL. It must not say the mine is safe.
// Board: ESP32 Dev Module. Serial: 115200.
#define MOLE_NODE_ID 'D'
#define MOLE_HAS_BME 1
#define MOLE_HAS_LCD 1
#define MOLE_HAS_BUZZER 1
#define MOLE_I2C_SDA 21
#define MOLE_I2C_SCL 22
#define MOLE_BUZZER_PIN 25
#define MOLE_BOARD_LABEL "ESP32"
#include "../common/mole_node.hpp"

void setup() { mole_setup(); }
void loop() { mole_loop(); }
