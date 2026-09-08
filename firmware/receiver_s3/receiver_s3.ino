/*
 * MOLE USB receiver — Waveshare ESP32-S3-Zero (ESP32-S3FH4R2)
 *
 * Arduino: "Waveshare ESP32-S3-Zero" or "ESP32S3 Dev Module"
 * Tools → USB CDC On Boot → Enabled
 * Serial 115200. No sensors on this board.
 *
 * If upload fails: hold BOOT, tap RESET, release BOOT, then upload.
 *
 * Listens ESP-NOW channel 1, prints one JSON object per line.
 */

#include <Arduino.h>
#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>

#define WIFI_CHANNEL 1
#define PACKET_VERSION 1
#define FLAG_IMU 0x01
#define FLAG_POT 0x02
#define FLAG_VIB 0x04

struct __attribute__((packed)) SensorPacket {
  uint8_t version;
  uint8_t nodeId;
  uint32_t sequence;
  uint32_t uptimeMs;
  float roll;
  float pitch;
  float vibration;
  int16_t sliderRaw;
  uint8_t flags;
};

static void forceChannel(uint8_t ch) {
  esp_wifi_set_promiscuous(true);
  esp_wifi_set_channel(ch, WIFI_SECOND_CHAN_NONE);
  esp_wifi_set_promiscuous(false);
}

static void emitJson(const SensorPacket &p) {
  if (p.version != PACKET_VERSION) {
    Serial.printf("{\"type\":\"status\",\"schema\":1,\"error\":\"bad_version\",\"version\":%u,\"gateway_ms\":%lu}\n",
                  p.version, (unsigned long)millis());
    return;
  }
  if (p.nodeId != 1 && p.nodeId != 2) {
    Serial.printf("{\"type\":\"status\",\"schema\":1,\"error\":\"bad_node\",\"node_id\":%u,\"gateway_ms\":%lu}\n",
                  p.nodeId, (unsigned long)millis());
    return;
  }

  char roll_buf[24];
  char pitch_buf[24];
  char vib_buf[24];
  char adc_buf[24];

  if (p.flags & FLAG_IMU) {
    snprintf(roll_buf, sizeof(roll_buf), "%.3f", p.roll);
    snprintf(pitch_buf, sizeof(pitch_buf), "%.3f", p.pitch);
  } else {
    snprintf(roll_buf, sizeof(roll_buf), "null");
    snprintf(pitch_buf, sizeof(pitch_buf), "null");
  }
  if (p.flags & FLAG_VIB) {
    snprintf(vib_buf, sizeof(vib_buf), "%.5f", p.vibration);
  } else {
    snprintf(vib_buf, sizeof(vib_buf), "null");
  }
  if ((p.flags & FLAG_POT) && p.sliderRaw >= 0) {
    snprintf(adc_buf, sizeof(adc_buf), "%d", (int)p.sliderRaw);
  } else {
    snprintf(adc_buf, sizeof(adc_buf), "null");
  }

  Serial.printf(
      "{\"type\":\"telemetry\",\"schema\":1,\"node_id\":%u,\"seq\":%lu,\"uptime_ms\":%lu,"
      "\"gateway_ms\":%lu,\"valid\":%u,\"roll_deg\":%s,\"pitch_deg\":%s,"
      "\"vibration_g\":%s,\"adc_raw\":%s}\n",
      p.nodeId, (unsigned long)p.sequence, (unsigned long)p.uptimeMs, (unsigned long)millis(),
      p.flags, roll_buf, pitch_buf, vib_buf, adc_buf);
}

static void onRecv(const esp_now_recv_info_t *info, const uint8_t *data, int len) {
  (void)info;
  if (len != (int)sizeof(SensorPacket)) {
    Serial.printf("{\"type\":\"status\",\"schema\":1,\"error\":\"bad_size\",\"len\":%d,\"gateway_ms\":%lu}\n",
                  len, (unsigned long)millis());
    return;
  }
  SensorPacket pkt;
  memcpy(&pkt, data, sizeof(pkt));
  emitJson(pkt);
}

void setup() {
  Serial.begin(115200);
  delay(400);
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  forceChannel(WIFI_CHANNEL);
  if (esp_now_init() != ESP_OK) {
    Serial.println("{\"type\":\"status\",\"schema\":1,\"error\":\"esp_now_init\"}");
    return;
  }
  esp_now_register_recv_cb(onRecv);
  Serial.printf("{\"type\":\"status\",\"schema\":1,\"boot\":\"mole-receiver-s3\",\"channel\":%u,\"gateway_ms\":%lu}\n",
                WIFI_CHANNEL, (unsigned long)millis());
}

void loop() {
  delay(100);
}
