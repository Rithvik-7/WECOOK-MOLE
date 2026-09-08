/*
 * MOLE Node A / Node B — classic ESP32-WROOM-32 (ESP32 Dev Module)
 *
 * Flash twice with only these two lines changed:
 *   Node A:  NODE_ID 1, HAS_POT 1
 *   Node B:  NODE_ID 2, HAS_POT 0
 *
 * MPU6050: VCC 3V3, GND, SDA 21, SCL 22, AD0 GND (addr 0x68)
 * Node A slider: SIG -- 1k -- GPIO34  (ADC1). Never 5 V into the ADC.
 *
 * ESP-NOW broadcast, channel 1, ~1 summarized packet per second.
 * Does not compute alerts, millimetres, or AI.
 */

#include <Arduino.h>
#include <Wire.h>
#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include <math.h>

#define NODE_ID 1
#define HAS_POT 1

#define WIFI_CHANNEL 1
#define MPU_ADDR 0x68
#define MPU_WHO_AM_I 0x75
#define MPU_PWR_MGMT_1 0x6B
#define MPU_ACCEL_XOUT_H 0x3B
#define SDA_PIN 21
#define SCL_PIN 22
#define POT_PIN 34
#define PACKET_VERSION 1
#define WINDOW_MS 1000
#define SAMPLE_US 12500  // 80 Hz
#define MAX_SAMPLES 96

static const uint8_t BROADCAST[] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};

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

static uint32_t g_sequence = 0;
static bool g_mpu_ok = false;

static bool mpuWrite(uint8_t reg, uint8_t val) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(reg);
  Wire.write(val);
  return Wire.endTransmission() == 0;
}

static bool mpuRead(uint8_t reg, uint8_t *buf, size_t n) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) {
    return false;
  }
  if (Wire.requestFrom((int)MPU_ADDR, (int)n) != (int)n) {
    return false;
  }
  for (size_t i = 0; i < n; i++) {
    buf[i] = Wire.read();
  }
  return true;
}

static int16_t be16(const uint8_t *p) {
  return (int16_t)((p[0] << 8) | p[1]);
}

static bool mpuBegin() {
  delay(50);
  uint8_t who = 0;
  if (!mpuRead(MPU_WHO_AM_I, &who, 1)) {
    return false;
  }
  // MPU6050 = 0x68; some clones report 0x70/0x71/0x98
  if (who != 0x68 && who != 0x70 && who != 0x71 && who != 0x98) {
    return false;
  }
  if (!mpuWrite(MPU_PWR_MGMT_1, 0x00)) {
    return false;
  }
  delay(50);
  return true;
}

static bool mpuSample(float *ax, float *ay, float *az, float *gx, float *gy, float *gz) {
  uint8_t raw[14];
  if (!mpuRead(MPU_ACCEL_XOUT_H, raw, 14)) {
    return false;
  }
  *ax = be16(raw + 0) / 16384.0f;
  *ay = be16(raw + 2) / 16384.0f;
  *az = be16(raw + 4) / 16384.0f;
  *gx = be16(raw + 8) / 131.0f;
  *gy = be16(raw + 10) / 131.0f;
  *gz = be16(raw + 12) / 131.0f;
  return true;
}

static void forceChannel(uint8_t ch) {
  esp_wifi_set_promiscuous(true);
  esp_wifi_set_channel(ch, WIFI_SECOND_CHAN_NONE);
  esp_wifi_set_promiscuous(false);
}

static bool radioBegin() {
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  forceChannel(WIFI_CHANNEL);
  if (esp_now_init() != ESP_OK) {
    return false;
  }
  esp_now_peer_info_t peer = {};
  memcpy(peer.peer_addr, BROADCAST, 6);
  peer.channel = WIFI_CHANNEL;
  peer.encrypt = false;
  if (esp_now_add_peer(&peer) != ESP_OK) {
    return false;
  }
  return true;
}

void setup() {
  Serial.begin(115200);
  analogReadResolution(12);
  analogSetPinAttenuation(POT_PIN, ADC_11db);
  pinMode(POT_PIN, INPUT);

  Wire.begin(SDA_PIN, SCL_PIN);
  Wire.setClock(400000);
  g_mpu_ok = mpuBegin();

  bool radio = radioBegin();
  Serial.printf("MOLE node id=%u pot=%u mpu=%u radio=%u\n",
                NODE_ID, HAS_POT, g_mpu_ok, radio);
}

void loop() {
  const uint32_t t0 = millis();
  float sax[MAX_SAMPLES];
  float say[MAX_SAMPLES];
  float saz[MAX_SAMPLES];
  int n = 0;
  int fails = 0;
  float ax, ay, az, gx, gy, gz;

  while ((millis() - t0) < WINDOW_MS && n < MAX_SAMPLES) {
    if (mpuSample(&ax, &ay, &az, &gx, &gy, &gz)) {
      sax[n] = ax;
      say[n] = ay;
      saz[n] = az;
      n++;
    } else {
      fails++;
    }
    delayMicroseconds(SAMPLE_US);
  }

  uint8_t flags = 0;
  float roll = 0, pitch = 0, vibration = 0;
  bool imu_ok = g_mpu_ok && n >= 20;
  if (imu_ok) {
    double sum_ax = 0, sum_ay = 0, sum_az = 0;
    for (int i = 0; i < n; i++) {
      sum_ax += sax[i];
      sum_ay += say[i];
      sum_az += saz[i];
    }
    const float mx = (float)(sum_ax / n);
    const float my = (float)(sum_ay / n);
    const float mz = (float)(sum_az / n);
    roll = atan2f(my, mz) * 180.0f / PI;
    pitch = atan2f(-mx, sqrtf(my * my + mz * mz)) * 180.0f / PI;
    flags |= 0x01;

    double acc = 0;
    for (int i = 0; i < n; i++) {
      const float dx = sax[i] - mx;
      const float dy = say[i] - my;
      const float dz = saz[i] - mz;
      acc += dx * dx + dy * dy + dz * dz;
    }
    vibration = sqrtf((float)(acc / n));
    flags |= 0x04;
  }

  int16_t slider = -1;
  if (HAS_POT) {
    int raw = analogRead(POT_PIN);
    slider = (int16_t)raw;
    // Usable interior travel roughly 100–3900 on 12-bit / 11 dB
    if (raw >= 100 && raw <= 3900) {
      flags |= 0x02;
    }
  }

  SensorPacket pkt;
  pkt.version = PACKET_VERSION;
  pkt.nodeId = NODE_ID;
  pkt.sequence = g_sequence++;
  pkt.uptimeMs = millis();
  pkt.roll = imu_ok ? roll : 0;
  pkt.pitch = imu_ok ? pitch : 0;
  pkt.vibration = (flags & 0x04) ? vibration : 0;
  pkt.sliderRaw = HAS_POT ? slider : (int16_t)-1;
  pkt.flags = flags;

  esp_now_send(BROADCAST, reinterpret_cast<uint8_t *>(&pkt), sizeof(pkt));

  Serial.printf("tx id=%u seq=%lu roll=%.2f pitch=%.2f vib=%.4f adc=%d flags=%u n=%d fail=%d\n",
                pkt.nodeId, (unsigned long)pkt.sequence, pkt.roll, pkt.pitch, pkt.vibration,
                (int)pkt.sliderRaw, pkt.flags, n, fails);

  const uint32_t used = millis() - t0;
  if (used < WINDOW_MS) {
    delay(WINDOW_MS - used);
  }
}
