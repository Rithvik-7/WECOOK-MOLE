// Shared ESP-NOW packet for every ESP32-S3 node and the receiver.
// Star only. A hop above 1 is ignored. Missing channels use MOLE_MISSING, never zero.
#pragma once
#include <stdint.h>

static const uint8_t MOLE_VERSION = 1;
static const uint8_t MOLE_HOP_LIMIT = 1;
static const uint8_t MOLE_CHANNEL = 1;
static const int16_t MOLE_MISSING = -32768;
static const uint8_t MOLE_RECEIVER_MAC[6] = {0xA0, 0xF2, 0x62, 0xF4, 0x66, 0xD0};

// ESP32-S3 pins. GPIO 22 and GPIO 25 do not exist on this chip.
// ADC1 (usable while ESP-NOW is on) is GPIO 1-10.
// GPIO 19 and 20 are USB. GPIO 0, 3, 45 and 46 are strapping pins.
static const int MOLE_PIN_SDA = 8;
static const int MOLE_PIN_SCL = 9;
static const int MOLE_PIN_SLIDER = 4;
static const int MOLE_PIN_TEMP_SIGNAL = 4;
static const int MOLE_PIN_LINEAR = 5;
static const int MOLE_PIN_GAS = 6;
static const int MOLE_PIN_BUZZER = 10;

struct __attribute__((packed)) MolePacket {
  uint8_t version;
  char node_id;
  char session_id[16];
  uint16_t sequence;
  uint8_t hops;
  uint8_t valid;
  uint8_t condition;
  uint8_t gas_ready;
  int16_t tilt_cdeg;
  int16_t vibration_c;
  int16_t gas_raw;
  int16_t slider_raw;
  int16_t linear_raw;
  int16_t temp_signal_raw;
  int16_t temp_cdeg;
  int16_t humidity_c;
  int16_t pressure_hpa10;
};

// Short command from the receiver to the node that has the buzzer.
// Kept separate so the sensor packet size does not change.
struct __attribute__((packed)) MoleAlert {
  uint8_t version;
  uint8_t kind;
};

static const uint8_t MOLE_ALERT_TILT = 1;
static const uint8_t MOLE_NODE_D_MAC[6] = {0x1C, 0xC3, 0xAB, 0xA0, 0x55, 0x5C};
