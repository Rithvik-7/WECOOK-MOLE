// MOLE receiver for ESP32-S3. Star collector. No cloud queue.
// Board: ESP32S3 Dev Module. USB CDC On Boot: Enabled. Serial: 115200.
// The laptop bridge reads this USB line.

#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include <string.h>
#include "../common/mole_packet.h"

static const uint32_t FRESH_MS = 120000;

struct Seen {
  char node;
  char session[16];
  uint16_t sequence;
  uint32_t at_ms;
  uint8_t condition;
  bool used;
};

static Seen seen[8];
static MolePacket pending;
static volatile bool has_packet = false;
static volatile uint32_t radio_frames = 0;
static volatile int radio_last_len = 0;
const char *lcd_for(uint8_t condition) {
  switch (condition) {
    case 0: return "NORMAL";
    case 1: return "WATCH";
    case 2: return "MOVEMENT";
    case 3: return "GAS";
    case 4: return "SENSOR FAULT";
    case 5: return "STALE";
    default: return "UNAVAILABLE";
  }
}

int find_seen(char node, const char *session) {
  for (int i = 0; i < 8; i++) {
    if (seen[i].used && seen[i].node == node && strncmp(seen[i].session, session, 16) == 0) return i;
  }
  return -1;
}

int claim_slot() {
  for (int i = 0; i < 8; i++) if (!seen[i].used) return i;
  return 0;
}

bool accept(const MolePacket &packet) {
  if (packet.version != MOLE_VERSION || packet.hops > MOLE_HOP_LIMIT) return false;
  if (packet.node_id < 'A' || packet.node_id > 'D') return false;
  int slot = find_seen(packet.node_id, packet.session_id);
  if (slot >= 0 && packet.sequence <= seen[slot].sequence) return false;
  if (slot < 0) slot = claim_slot();
  seen[slot].used = true;
  seen[slot].node = packet.node_id;
  strncpy(seen[slot].session, packet.session_id, 15);
  seen[slot].session[15] = 0;
  seen[slot].sequence = packet.sequence;
  seen[slot].at_ms = millis();
  seen[slot].condition = packet.condition;
  return true;
}

void print_scaled(const char *key, int value, int scale) {
  Serial.print(",\"");
  Serial.print(key);
  Serial.print("\":");
  Serial.print(value / scale);
  Serial.print(".");
  int frac = abs(value % scale);
  if (scale == 100 && frac < 10) Serial.print("0");
  Serial.print(frac);
}

void print_count(const char *key, int16_t value) {
  if (value == MOLE_MISSING) return;
  Serial.print(",\"");
  Serial.print(key);
  Serial.print("\":");
  Serial.print(value);
}

void print_packet(const MolePacket &packet) {
  Serial.print("{\"node_id\":\"");
  Serial.print(packet.node_id);
  Serial.print("\",\"session_id\":\"");
  Serial.print(packet.session_id);
  Serial.print("\",\"sequence\":");
  Serial.print(packet.sequence);
  Serial.print(",\"origin\":\"physical\",\"hops\":");
  Serial.print(packet.hops);
  Serial.print(",\"valid\":");
  Serial.print(packet.valid ? "true" : "false");
  if (!packet.valid) Serial.print(",\"fault\":true,\"fault_reason\":\"MPU missing\"");
  if (packet.tilt_cdeg != MOLE_MISSING) print_scaled("tilt_deg", packet.tilt_cdeg, 100);
  if (packet.vibration_c != MOLE_MISSING) print_scaled("vibration", packet.vibration_c, 100);
  print_count("gas_raw", packet.gas_raw);
  if (packet.gas_raw != MOLE_MISSING) {
    Serial.print(",\"gas_ready\":");
    Serial.print(packet.gas_ready ? "true" : "false");
  }
  print_count("potentiometer_raw", packet.slider_raw);
  print_count("linear_raw", packet.linear_raw);
  print_count("temperature_signal_raw", packet.temp_signal_raw);
  if (packet.temp_cdeg != MOLE_MISSING) print_scaled("temperature_c", packet.temp_cdeg, 100);
  if (packet.humidity_c != MOLE_MISSING) print_scaled("humidity_pct", packet.humidity_c, 100);
  if (packet.pressure_hpa10 != MOLE_MISSING) print_scaled("pressure_hpa", packet.pressure_hpa10, 10);
  Serial.println("}");
}

uint8_t highest_condition() {
  uint8_t best = 255;
  uint8_t rank[] = {0, 2, 5, 5, 4, 3};
  uint8_t best_rank = 0;
  for (int i = 0; i < 8; i++) {
    if (!seen[i].used) continue;
    uint8_t condition = (millis() - seen[i].at_ms > FRESH_MS) ? 5 : seen[i].condition;
    if (condition > 5) condition = 5;
    if (rank[condition] >= best_rank) {
      best_rank = rank[condition];
      best = condition;
    }
  }
  return best;
}

#if ESP_ARDUINO_VERSION >= ESP_ARDUINO_VERSION_VAL(3, 0, 0)
void on_receive(const esp_now_recv_info_t *info, const uint8_t *data, int len) {
#else
void on_receive(const uint8_t *mac, const uint8_t *data, int len) {
#endif
  radio_frames++;
  radio_last_len = len;
  if (len != (int)sizeof(MolePacket) || has_packet) return;
  memcpy(&pending, data, sizeof(MolePacket));
  has_packet = true;
}

uint8_t listen_channel() {
  uint8_t best = MOLE_CHANNEL;
  uint32_t best_count = 0;
  esp_wifi_set_protocol(WIFI_IF_STA, WIFI_PROTOCOL_11B | WIFI_PROTOCOL_11G | WIFI_PROTOCOL_11N);
  for (uint8_t channel = 1; channel <= 13; channel++) {
    esp_wifi_set_channel(channel, WIFI_SECOND_CHAN_NONE);
    uint32_t start = radio_frames;
    delay(1100);
    uint32_t heard = radio_frames - start;
    Serial.print("{\"unit\":\"receiver\",\"scan\":");
    Serial.print(channel);
    Serial.print(",\"frames\":");
    Serial.print(heard);
    Serial.print(",\"last_len\":");
    Serial.print(radio_last_len);
    Serial.println("}");
    if (heard > best_count) {
      best_count = heard;
      best = channel;
    }
  }
  esp_wifi_set_channel(best, WIFI_SECOND_CHAN_NONE);
  esp_now_peer_info_t buzzer = {};
  memcpy(buzzer.peer_addr, MOLE_NODE_D_MAC, 6);
  buzzer.channel = best;
  buzzer.encrypt = false;
  esp_now_add_peer(&buzzer);
  Serial.print("{\"unit\":\"receiver\",\"channel\":");
  Serial.print(best);
  Serial.print(",\"frames\":");
  Serial.print(best_count);
  Serial.println("}");
  return best;
}

void notify_tilt(const MolePacket &packet) {
  static int16_t last_tilt[4] = {MOLE_MISSING, MOLE_MISSING, MOLE_MISSING, MOLE_MISSING};
  static uint32_t last_sent = 0;
  int index = packet.node_id - 'A';
  bool jump = false;
  if (index >= 0 && index < 4 && packet.tilt_cdeg != MOLE_MISSING) {
    int delta = packet.tilt_cdeg - last_tilt[index];
    if (delta < 0) delta = -delta;
    if (last_tilt[index] != MOLE_MISSING && delta >= 300) jump = true;
    last_tilt[index] = packet.tilt_cdeg;
  }
  if (packet.condition != 2 && !jump) return;
  if (millis() - last_sent < 400) return;
  last_sent = millis();
  MoleAlert alert = {MOLE_VERSION, MOLE_ALERT_TILT};
  esp_now_send(MOLE_NODE_D_MAC, (const uint8_t *)&alert, sizeof(alert));
}

void setup() {
  Serial.begin(115200);
  delay(400);
#if defined(ARDUINO_USB_CDC_ON_BOOT) && ARDUINO_USB_CDC_ON_BOOT
  Serial.setTxTimeoutMs(0);
#endif
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  WiFi.setSleep(false);
  uint8_t mac[6];
  esp_wifi_get_mac(WIFI_IF_STA, mac);
  Serial.print("{\"unit\":\"receiver\",\"board\":\"ESP32-S3\",\"buffer\":\"none\",\"channel\":1,\"mac\":\"");
  for (int i = 0; i < 6; i++) {
    if (mac[i] < 16) Serial.print("0");
    Serial.print(mac[i], HEX);
    if (i < 5) Serial.print(":");
  }
  Serial.println("\"}");
  if (esp_now_init() != ESP_OK) {
    Serial.println("{\"unit\":\"receiver\",\"error\":\"esp-now-init\"}");
    return;
  }
  esp_now_register_recv_cb(on_receive);
  listen_channel();
}

void loop() {
  if (has_packet) {
    MolePacket copy = pending;
    has_packet = false;
    if (accept(copy)) {
      print_packet(copy);
      notify_tilt(copy);
    }
  }
  static uint32_t last_status = 0;
  if (millis() - last_status > 2000) {
    last_status = millis();
    uint8_t condition = highest_condition();
    Serial.print("{\"unit\":\"receiver\",\"lcd\":\"");
    Serial.print(condition == 255 ? "UNAVAILABLE" : lcd_for(condition));
    Serial.println("\"}");
  }
}
