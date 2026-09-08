/*
 * MOLE rover — classic ESP32-WROOM-32 (ESP32 Dev Module)
 *
 * Wi-Fi AP: Mine-Rover-AP  →  http://192.168.4.1
 * /forward /backward /left /right /stop /telemetry
 *
 * Pins frozen. No camera. Driving is remote, not autonomous.
 * Stops if no drive command arrives for DRIVE_TIMEOUT_MS.
 *
 * HC-SR04 ECHO must go through the 1k/2k divider into GPIO18. Do not feed 5 V ECHO.
 * MQ-7 is raw ADC, not ppm.
 */

#include <Arduino.h>
#include <Wire.h>
#include <WiFi.h>
#include <WebServer.h>
#include <math.h>

#define L298_IN1 13
#define L298_IN2 12
#define L298_IN3 14
#define L298_IN4 27
#define TRIG_PIN 5
#define ECHO_PIN 18
#define MQ7_PIN 36
#define IR_PIN 19
#define MPU_SDA 21
#define MPU_SCL 22

#define MPU_ADDR 0x68
#define MPU_WHO_AM_I 0x75
#define MPU_PWR_MGMT_1 0x6B
#define MPU_ACCEL_XOUT_H 0x3B
#define DRIVE_TIMEOUT_MS 400
#define MQ7_HIGH_RAW 2500

static const char *AP_SSID = "Mine-Rover-AP";

WebServer server(80);

static uint32_t g_seq = 0;
static uint32_t g_last_cmd_ms = 0;
static bool g_driving = false;
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
  uint8_t who = 0;
  if (!mpuRead(MPU_WHO_AM_I, &who, 1)) {
    return false;
  }
  if (who != 0x68 && who != 0x70 && who != 0x71 && who != 0x98) {
    return false;
  }
  return mpuWrite(MPU_PWR_MGMT_1, 0x00);
}

static bool mpuOrientation(float *roll, float *pitch, float *vib) {
  uint8_t raw[14];
  if (!mpuRead(MPU_ACCEL_XOUT_H, raw, 14)) {
    return false;
  }
  const float ax = be16(raw + 0) / 16384.0f;
  const float ay = be16(raw + 2) / 16384.0f;
  const float az = be16(raw + 4) / 16384.0f;
  *roll = atan2f(ay, az) * 180.0f / PI;
  *pitch = atan2f(-ax, sqrtf(ay * ay + az * az)) * 180.0f / PI;
  const float mag = sqrtf(ax * ax + ay * ay + az * az);
  *vib = fabsf(mag - 1.0f);
  return true;
}

static void motors(int a, int b, int c, int d) {
  digitalWrite(L298_IN1, a);
  digitalWrite(L298_IN2, b);
  digitalWrite(L298_IN3, c);
  digitalWrite(L298_IN4, d);
}

static void cmdStop() {
  motors(0, 0, 0, 0);
  g_driving = false;
}

static void cmdForward() { motors(1, 0, 1, 0); g_driving = true; g_last_cmd_ms = millis(); }
static void cmdBack() { motors(0, 1, 0, 1); g_driving = true; g_last_cmd_ms = millis(); }
static void cmdLeft() { motors(0, 1, 1, 0); g_driving = true; g_last_cmd_ms = millis(); }
static void cmdRight() { motors(1, 0, 0, 1); g_driving = true; g_last_cmd_ms = millis(); }

static float distanceCm() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  unsigned long us = pulseIn(ECHO_PIN, HIGH, 25000);
  if (us == 0) {
    return -1.0f;
  }
  return (us * 0.0343f) / 2.0f;
}

/* Typical 3-pin IR module: OUT goes LOW when something is close.
 * INPUT_PULLUP covers open-collector boards. Majority-of-3 kills chatter.
 * This flag does not stop the motors — driving stays remote. */
static bool irObstacle() {
  uint8_t hits = 0;
  for (int i = 0; i < 3; i++) {
    if (digitalRead(IR_PIN) == LOW) {
      hits++;
    }
    delayMicroseconds(400);
  }
  return hits >= 2;
}

static void sendOk() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.send(200, "application/json", "{\"ok\":true}");
}

static void handleTelemetry() {
  float roll = 0, pitch = 0, vib = 0;
  bool imu = g_mpu_ok && mpuOrientation(&roll, &pitch, &vib);
  float dist = distanceCm();
  int mq7 = analogRead(MQ7_PIN);
  bool obstacle = irObstacle();
  const char *gas = (mq7 >= MQ7_HIGH_RAW) ? "HIGH" : "NORMAL";

  char dist_buf[24];
  if (dist < 0) {
    snprintf(dist_buf, sizeof(dist_buf), "null");
  } else {
    snprintf(dist_buf, sizeof(dist_buf), "%.1f", dist);
  }
  char roll_buf[24], pitch_buf[24], vib_buf[24];
  if (imu) {
    snprintf(roll_buf, sizeof(roll_buf), "%.2f", roll);
    snprintf(pitch_buf, sizeof(pitch_buf), "%.2f", pitch);
    snprintf(vib_buf, sizeof(vib_buf), "%.4f", vib);
  } else {
    snprintf(roll_buf, sizeof(roll_buf), "null");
    snprintf(pitch_buf, sizeof(pitch_buf), "null");
    snprintf(vib_buf, sizeof(vib_buf), "null");
  }

  char body[512];
  snprintf(body, sizeof(body),
           "{\"type\":\"rover\",\"device_id\":\"rover\",\"seq\":%lu,\"uptime_ms\":%lu,"
           "\"distance_cm\":%s,\"ir_obstacle\":%s,\"mq7_raw\":%d,\"mq7_level\":\"%s\","
           "\"roll_deg\":%s,\"pitch_deg\":%s,\"vibration_g\":%s,\"imu_valid\":%s,"
           "\"driving\":%s}",
           (unsigned long)g_seq++, (unsigned long)millis(), dist_buf,
           obstacle ? "true" : "false", mq7, gas, roll_buf, pitch_buf, vib_buf,
           imu ? "true" : "false", g_driving ? "true" : "false");
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.send(200, "application/json", body);
}

void setup() {
  Serial.begin(115200);
  pinMode(L298_IN1, OUTPUT);
  pinMode(L298_IN2, OUTPUT);
  pinMode(L298_IN3, OUTPUT);
  pinMode(L298_IN4, OUTPUT);
  cmdStop();
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(IR_PIN, INPUT_PULLUP);
  analogReadResolution(12);
  analogSetPinAttenuation(MQ7_PIN, ADC_11db);

  Wire.begin(MPU_SDA, MPU_SCL);
  Wire.setClock(400000);
  delay(40);
  g_mpu_ok = mpuBegin();

  WiFi.mode(WIFI_AP);
  WiFi.softAP(AP_SSID);
  server.on("/forward", HTTP_GET, []() { cmdForward(); sendOk(); });
  server.on("/backward", HTTP_GET, []() { cmdBack(); sendOk(); });
  server.on("/left", HTTP_GET, []() { cmdLeft(); sendOk(); });
  server.on("/right", HTTP_GET, []() { cmdRight(); sendOk(); });
  server.on("/stop", HTTP_GET, []() { cmdStop(); sendOk(); });
  server.on("/telemetry", HTTP_GET, handleTelemetry);
  server.on("/", HTTP_GET, []() {
    server.sendHeader("Access-Control-Allow-Origin", "*");
    server.send(200, "text/plain", "MOLE rover. Use the laptop dashboard.");
  });
  server.begin();
  Serial.printf("MOLE rover AP %s ip=%s mpu=%u\n", AP_SSID, WiFi.softAPIP().toString().c_str(), g_mpu_ok);
}

void loop() {
  server.handleClient();
  if (g_driving && (millis() - g_last_cmd_ms) > DRIVE_TIMEOUT_MS) {
    cmdStop();
  }
}
