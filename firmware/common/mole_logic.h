// Shared node and receiver decisions. No pins. No mesh.
// Thresholds match firmware/logic.py and api/analysis.py.
#pragma once
#include <string.h>

static const int MOLE_VERSION = 1;
static const int MOLE_HOP_LIMIT = 1;
static const int MOLE_MAX_RETRIES = 3;
static const int MOLE_FRESH_SECONDS = 120;
static const float MOLE_MOVEMENT_DEG = 1.2f;
static const float MOLE_WATCH_DEG = 0.6f;
static const int MOLE_SUSTAINED = 3;
static const float MOLE_GAS_RAW = 1800.f;

inline const char *mole_lcd(const char *condition) {
  if (strcmp(condition, "normal") == 0) return "NORMAL";
  if (strcmp(condition, "watch") == 0) return "WATCH";
  if (strcmp(condition, "movement") == 0) return "MOVEMENT";
  if (strcmp(condition, "gas") == 0) return "GAS";
  if (strcmp(condition, "sensor_fault") == 0) return "SENSOR FAULT";
  if (strcmp(condition, "stale") == 0) return "STALE";
  return "UNAVAILABLE";
}

inline bool mole_buzzer(const char *condition) {
  return strcmp(condition, "movement") == 0 || strcmp(condition, "gas") == 0 ||
         strcmp(condition, "sensor_fault") == 0 || strcmp(condition, "stale") == 0;
}

inline bool mole_command_current(long expires_at, long now_s) { return now_s < expires_at; }

// Direct star only. A hop above 1 is not forwarded.
inline bool mole_star_hop(int hops) { return hops >= 0 && hops <= MOLE_HOP_LIMIT; }
