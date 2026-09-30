// ESP32-S3 node program. Each sketch sets MOLE_NODE_ID and the parts it has.
#pragma once
#include <WiFi.h>
#include <Wire.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include <math.h>
#include <string.h>
#include "mole_packet.h"

#ifndef MOLE_NODE_ID
#error Define MOLE_NODE_ID before including mole_node.hpp
#endif
#ifndef MOLE_HAS_SLIDER
#define MOLE_HAS_SLIDER 0
#endif
#ifndef MOLE_HAS_TEMP_SIGNAL
#define MOLE_HAS_TEMP_SIGNAL 0
#endif
#ifndef MOLE_HAS_LINEAR
#define MOLE_HAS_LINEAR 0
#endif
#ifndef MOLE_HAS_GAS
#define MOLE_HAS_GAS 0
#endif
#ifndef MOLE_HAS_BME
#define MOLE_HAS_BME 0
#endif
#ifndef MOLE_HAS_LCD
#define MOLE_HAS_LCD 0
#endif
#ifndef MOLE_HAS_BUZZER
#define MOLE_HAS_BUZZER 0
#endif
#ifndef MOLE_HAS_DS18B20
#define MOLE_HAS_DS18B20 0
#endif
#ifndef MOLE_I2C_SDA
#define MOLE_I2C_SDA MOLE_PIN_SDA
#define MOLE_I2C_SCL MOLE_PIN_SCL
#endif
#ifndef MOLE_BOARD_LABEL
#define MOLE_BOARD_LABEL "ESP32-S3"
#endif
#ifndef MOLE_DS18B20_PIN
#define MOLE_DS18B20_PIN 4
#endif
#ifndef MOLE_SLIDER_PIN
#define MOLE_SLIDER_PIN MOLE_PIN_SLIDER
#endif
#ifndef MOLE_GAS_PIN
#define MOLE_GAS_PIN MOLE_PIN_GAS
#endif
#ifndef MOLE_BUZZER_PIN
#define MOLE_BUZZER_PIN MOLE_PIN_BUZZER
#endif

static const uint32_t MOLE_GAS_WARMUP_MS = 60000;
static const float MOLE_WATCH_DEG = 0.6f;
static const float MOLE_MOVEMENT_DEG = 1.2f;
static const float MOLE_VIBRATION_WATCH = 2.5f;
static const int MOLE_GAS_RAW_ALERT = 1800;

static char mole_session[16];
static uint16_t mole_sequence = 0;
static bool mole_radio = false;
static uint8_t mole_mpu = 0;
static float mole_history[6];
static int mole_history_count = 0;
static volatile uint32_t mole_buzz_until = 0;
static volatile uint32_t mole_alert_at = 0;
static volatile uint8_t mole_buzz_latched = 0;

#if MOLE_HAS_DS18B20
static OneWire mole_ow(MOLE_DS18B20_PIN);
static DallasTemperature mole_ds(&mole_ow);
static uint32_t mole_ds_ready_at = 0;
static bool mole_ds_ok = false;
#endif

#if MOLE_HAS_BME
static uint8_t mole_bme = 0;
static uint8_t mole_bme_id = 0;
static bool mole_bme_humidity = false;
static int32_t mole_t_fine = 0;
static uint16_t dig_T1, dig_P1;
static int16_t dig_T2, dig_T3, dig_P2, dig_P3, dig_P4, dig_P5, dig_P6, dig_P7, dig_P8, dig_P9;
static uint8_t dig_H1, dig_H3;
static int16_t dig_H2, dig_H4, dig_H5;
static int8_t dig_H6;
#endif

#if MOLE_HAS_LCD
static uint8_t mole_lcd = 0;
#endif

static int16_t mole_clamp(int32_t value) {
  if (value > 32767) return 32767;
  if (value < -32767) return -32767;
  return (int16_t)value;
}

static bool i2c_write(uint8_t addr, uint8_t reg, uint8_t value) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  Wire.write(value);
  return Wire.endTransmission() == 0;
}

static bool i2c_read(uint8_t addr, uint8_t reg, uint8_t *buf, size_t len) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom((int)addr, (int)len) != (int)len) return false;
  for (size_t i = 0; i < len; i++) buf[i] = Wire.read();
  return true;
}

static bool mpu_begin() {
  uint8_t who = 0;
  const uint8_t addresses[] = {0x68, 0x69};
  for (uint8_t addr : addresses) {
    if (!i2c_read(addr, 0x75, &who, 1)) continue;
    if (who != 0x68 && who != 0x70 && who != 0x71) continue;
    if (!i2c_write(addr, 0x6B, 0x00)) continue;
    i2c_write(addr, 0x1C, 0x00);
    mole_mpu = addr;
    return true;
  }
  mole_mpu = 0;
  return false;
}

static bool mpu_sample(float *tilt_deg, float *vibration) {
  float sum = 0;
  float sumsq = 0;
  float tilt_sum = 0;
  int count = 0;
  for (int i = 0; i < 16; i++) {
    uint8_t raw[6];
    if (!i2c_read(mole_mpu, 0x3B, raw, 6)) return false;
    int16_t ax_i = (int16_t)((raw[0] << 8) | raw[1]);
    int16_t ay_i = (int16_t)((raw[2] << 8) | raw[3]);
    int16_t az_i = (int16_t)((raw[4] << 8) | raw[5]);
    float ax = ax_i / 16384.0f;
    float ay = ay_i / 16384.0f;
    float az = az_i / 16384.0f;
    float mag = sqrtf(ax * ax + ay * ay + az * az);
    if (mag < 0.2f) return false;
    tilt_sum += atan2f(sqrtf(ax * ax + ay * ay), az) * 57.2957795f;
    sum += mag;
    sumsq += mag * mag;
    count++;
    delay(15);
  }
  float mean = sum / count;
  float variance = sumsq / count - mean * mean;
  if (variance < 0) variance = 0;
  *tilt_deg = tilt_sum / count;
  *vibration = sqrtf(variance) * 10.0f;
  return true;
}

static float mole_median3(float a, float b, float c) {
  if (a > b) { float t = a; a = b; b = t; }
  if (b > c) { float t = b; b = c; c = t; }
  if (a > b) { float t = a; a = b; b = t; }
  return b;
}

static uint8_t mole_condition(float tilt, float vibration, bool gas_alarm, bool mpu_ok) {
  if (!mpu_ok) return 4;
  if (mole_history_count < 6) mole_history[mole_history_count++] = tilt;
  else {
    memmove(mole_history, mole_history + 1, 5 * sizeof(float));
    mole_history[5] = tilt;
  }
  uint8_t movement = 0;
  if (mole_history_count >= 6) {
    float baseline = mole_median3(mole_history[0], mole_history[1], mole_history[2]);
    float diff = tilt - baseline;
    int direction = diff >= 0 ? 1 : -1;
    int sustained = 0;
    for (int i = mole_history_count - 1; i >= 0; i--) {
      if (direction * (mole_history[i] - baseline) + 0.0001f < MOLE_MOVEMENT_DEG) break;
      sustained++;
    }
    if (sustained >= 3) movement = 2;
    else if (fabsf(diff) >= MOLE_WATCH_DEG || vibration >= MOLE_VIBRATION_WATCH) movement = 1;
  }
  if (movement == 2) return 2;
  if (gas_alarm) return 3;
  return movement;
}

static int mole_adc(int pin) {
  int reading = analogRead(pin);
  if (reading < 0) reading = 0;
  if (reading > 4095) reading = 4095;
  return reading;
}

#if MOLE_HAS_BME
static int16_t be16(const uint8_t *p) { return (int16_t)((p[1] << 8) | p[0]); }
static uint16_t bu16(const uint8_t *p) { return (uint16_t)((p[1] << 8) | p[0]); }

static bool bme_begin() {
  const uint8_t addresses[] = {0x76, 0x77};
  for (uint8_t addr : addresses) {
    uint8_t id = 0;
    if (!i2c_read(addr, 0xD0, &id, 1) || (id != 0x60 && id != 0x58)) continue;
    uint8_t cal[24];
    if (!i2c_read(addr, 0x88, cal, 24)) continue;
    dig_T1 = bu16(cal); dig_T2 = be16(cal + 2); dig_T3 = be16(cal + 4);
    dig_P1 = bu16(cal + 6); dig_P2 = be16(cal + 8); dig_P3 = be16(cal + 10);
    dig_P4 = be16(cal + 12); dig_P5 = be16(cal + 14); dig_P6 = be16(cal + 16);
    dig_P7 = be16(cal + 18); dig_P8 = be16(cal + 20); dig_P9 = be16(cal + 22);
    mole_bme_humidity = id == 0x60;
    if (mole_bme_humidity) {
      uint8_t h1 = 0;
      uint8_t hcal[7];
      if (!i2c_read(addr, 0xA1, &h1, 1)) continue;
      if (!i2c_read(addr, 0xE1, hcal, 7)) continue;
      dig_H1 = h1;
      dig_H2 = be16(hcal);
      dig_H3 = hcal[2];
      dig_H4 = (int16_t)((hcal[3] << 4) | (hcal[4] & 0x0F));
      dig_H5 = (int16_t)((hcal[5] << 4) | (hcal[4] >> 4));
      dig_H6 = (int8_t)hcal[6];
      if (!i2c_write(addr, 0xF2, 0x01)) continue;
    }
    if (!i2c_write(addr, 0xF4, 0x25)) continue;
    mole_bme = addr;
    mole_bme_id = id;
    return true;
  }
  mole_bme = 0;
  return false;
}

static bool bme_read(int16_t *temp_cdeg, int16_t *humidity_c, int16_t *pressure_hpa10) {
  if (mole_bme_humidity) {
    if (!i2c_write(mole_bme, 0xF2, 0x01)) return false;
  }
  if (!i2c_write(mole_bme, 0xF4, 0x25)) return false;
  delay(12);
  uint8_t raw[8];
  if (!i2c_read(mole_bme, 0xF7, raw, 8)) return false;
  int32_t adc_P = (int32_t)((raw[0] << 12) | (raw[1] << 4) | (raw[2] >> 4));
  int32_t adc_T = (int32_t)((raw[3] << 12) | (raw[4] << 4) | (raw[5] >> 4));
  int32_t adc_H = (int32_t)((raw[6] << 8) | raw[7]);
  int32_t var1 = ((((adc_T >> 3) - ((int32_t)dig_T1 << 1))) * ((int32_t)dig_T2)) >> 11;
  int32_t var2 = (((((adc_T >> 4) - ((int32_t)dig_T1)) * ((adc_T >> 4) - ((int32_t)dig_T1))) >> 12) * ((int32_t)dig_T3)) >> 14;
  mole_t_fine = var1 + var2;
  int32_t temperature = (mole_t_fine * 5 + 128) >> 8;
  int64_t v1 = ((int64_t)mole_t_fine) - 128000;
  int64_t v2 = v1 * v1 * (int64_t)dig_P6;
  v2 = v2 + ((v1 * (int64_t)dig_P5) << 17);
  v2 = v2 + (((int64_t)dig_P4) << 35);
  v1 = ((v1 * v1 * (int64_t)dig_P3) >> 8) + ((v1 * (int64_t)dig_P2) << 12);
  v1 = (((((int64_t)1) << 47) + v1) * ((int64_t)dig_P1)) >> 33;
  if (v1 == 0) return false;
  int64_t p = 1048576 - adc_P;
  p = (((p << 31) - v2) * 3125) / v1;
  v1 = (((int64_t)dig_P9) * (p >> 13) * (p >> 13)) >> 25;
  v2 = (((int64_t)dig_P8) * p) >> 19;
  p = ((p + v1 + v2) >> 8) + (((int64_t)dig_P7) << 4);
  *temp_cdeg = mole_clamp(temperature);
  *pressure_hpa10 = mole_clamp((int32_t)(p / 2560));
  if (!mole_bme_humidity) {
    *humidity_c = MOLE_MISSING;
    return true;
  }
  int32_t h = mole_t_fine - 76800;
  h = (((((adc_H << 14) - (((int32_t)dig_H4) << 20) - (((int32_t)dig_H5) * h)) + 16384) >> 15) *
       (((((((h * ((int32_t)dig_H6)) >> 10) * (((h * ((int32_t)dig_H3)) >> 11) + 32768)) >> 10) + 2097152) *
         ((int32_t)dig_H2) + 8192) >> 14));
  h = h - (((((h >> 15) * (h >> 15)) >> 7) * ((int32_t)dig_H1)) >> 4);
  if (h < 0) h = 0;
  if (h > 419430400) h = 419430400;
  *humidity_c = mole_clamp(((h >> 12) * 100) / 1024);
  return true;
}
#endif

#if MOLE_HAS_LCD
static void lcd_raw(uint8_t value) {
  Wire.beginTransmission(mole_lcd);
  Wire.write(value);
  Wire.endTransmission();
}

static void lcd_nibble(uint8_t nibble, bool rs) {
  uint8_t value = (uint8_t)((nibble << 4) | 0x08);
  if (rs) value |= 0x01;
  lcd_raw(value | 0x04);
  delayMicroseconds(2);
  lcd_raw(value);
  delayMicroseconds(40);
}

static void lcd_command(uint8_t command) {
  lcd_nibble(command >> 4, false);
  lcd_nibble(command & 0x0F, false);
}

static void lcd_begin() {
  const uint8_t addresses[] = {0x27, 0x3F};
  for (uint8_t addr : addresses) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() != 0) continue;
    mole_lcd = addr;
    delay(40);
    lcd_nibble(0x03, false); delay(5);
    lcd_nibble(0x03, false); delay(1);
    lcd_nibble(0x03, false);
    lcd_nibble(0x02, false);
    lcd_command(0x28);
    lcd_command(0x0C);
    lcd_command(0x01);
    delay(2);
    lcd_command(0x06);
    return;
  }
  mole_lcd = 0;
}

static void lcd_line(const char *text, uint8_t command) {
  if (!mole_lcd) return;
  lcd_command(command);
  char line[17];
  snprintf(line, sizeof(line), "%-16.16s", text);
  for (int i = 0; i < 16; i++) lcd_nibble((uint8_t)line[i] >> 4, true), lcd_nibble(line[i] & 0x0F, true);
}

static void lcd_live(int16_t temp_cdeg, int16_t pressure_hpa10, bool tilt) {
  if (!mole_lcd) return;
  lcd_line(tilt ? "SUBSIDE" : "NODE D", 0x80);
  if (temp_cdeg == MOLE_MISSING) {
    lcd_line("LIVE", 0xC0);
    return;
  }
  char value[17];
  int whole = temp_cdeg / 100;
  int frac = abs(temp_cdeg % 100) / 10;
  if (pressure_hpa10 == MOLE_MISSING) snprintf(value, sizeof(value), "%d.%dC", whole, frac);
  else snprintf(value, sizeof(value), "%d.%dC %dhPa", whole, frac, pressure_hpa10 / 10);
  lcd_line(value, 0xC0);
}
#endif

#if MOLE_HAS_BUZZER || MOLE_HAS_LCD
#if ESP_ARDUINO_VERSION >= ESP_ARDUINO_VERSION_VAL(3, 0, 0)
static void on_alert(const esp_now_recv_info_t *info, const uint8_t *data, int len) {
  (void)info;
#else
static void on_alert(const uint8_t *mac, const uint8_t *data, int len) {
  (void)mac;
#endif
  if (len != (int)sizeof(MoleAlert)) return;
  MoleAlert alert;
  memcpy(&alert, data, sizeof(alert));
  if (alert.version == MOLE_VERSION && alert.kind == MOLE_ALERT_TILT) {
    mole_alert_at = millis();
    if (!mole_buzz_latched) {
      mole_buzz_latched = 1;
      mole_buzz_until = millis() + 2000;
    }
  }
}
#endif

static void mole_setup() {
  Serial.begin(115200);
  delay(300);
#if defined(ARDUINO_USB_CDC_ON_BOOT) && ARDUINO_USB_CDC_ON_BOOT
  Serial.setTxTimeoutMs(0);
#endif
  Wire.begin(MOLE_I2C_SDA, MOLE_I2C_SCL);
  Wire.setClock(100000);
  analogReadResolution(12);
  analogSetAttenuation(ADC_11db);
#if MOLE_HAS_SLIDER
  pinMode(MOLE_SLIDER_PIN, INPUT);
#endif
#if MOLE_HAS_TEMP_SIGNAL
  pinMode(MOLE_PIN_TEMP_SIGNAL, INPUT);
#endif
#if MOLE_HAS_LINEAR
  pinMode(MOLE_PIN_LINEAR, INPUT);
#endif
#if MOLE_HAS_GAS
  pinMode(MOLE_GAS_PIN, INPUT);
#endif
#if MOLE_HAS_BUZZER
  pinMode(MOLE_BUZZER_PIN, OUTPUT);
  ledcAttach(MOLE_BUZZER_PIN, 2000, 8);
  ledcWrite(MOLE_BUZZER_PIN, 128);
  delay(120);
  ledcWrite(MOLE_BUZZER_PIN, 0);
#endif
  mpu_begin();
#if MOLE_HAS_DS18B20
  mole_ds.begin();
  mole_ds.setWaitForConversion(false);
  mole_ds_ok = mole_ds.getDeviceCount() > 0;
  if (mole_ds_ok) {
    mole_ds.requestTemperatures();
    mole_ds_ready_at = millis() + 800;
  }
#endif
#if MOLE_HAS_BME
  bme_begin();
#endif
#if MOLE_HAS_LCD
  lcd_begin();
  lcd_live(MOLE_MISSING, MOLE_MISSING, false);
#endif
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  WiFi.setSleep(false);
  uint8_t mac[6];
  esp_wifi_get_mac(WIFI_IF_STA, mac);
  snprintf(mole_session, sizeof(mole_session), "%c%02X%02X%02X%02X", MOLE_NODE_ID, mac[2], mac[3], mac[4], mac[5]);
  mole_radio = esp_now_init() == ESP_OK;
  if (mole_radio) {
    esp_wifi_set_protocol(WIFI_IF_STA, WIFI_PROTOCOL_11B | WIFI_PROTOCOL_11G | WIFI_PROTOCOL_11N);
    esp_wifi_set_channel(MOLE_CHANNEL, WIFI_SECOND_CHAN_NONE);
    esp_now_peer_info_t peer = {};
    memcpy(peer.peer_addr, MOLE_RECEIVER_MAC, 6);
    peer.channel = MOLE_CHANNEL;
    peer.encrypt = false;
    esp_now_add_peer(&peer);
#if MOLE_HAS_BUZZER || MOLE_HAS_LCD
    esp_now_register_recv_cb(on_alert);
#endif
  }
  Serial.print("{\"unit\":\"node\",\"id\":\"");
  Serial.print((char)MOLE_NODE_ID);
  Serial.print("\",\"board\":\"");
  Serial.print(MOLE_BOARD_LABEL);
  Serial.print("\",\"session\":\"");
  Serial.print(mole_session);
  Serial.print("\",\"mpu\":");
  Serial.print(mole_mpu ? "true" : "false");
#if MOLE_HAS_DS18B20
  Serial.print(",\"ds18b20\":");
  Serial.print(mole_ds_ok ? "true" : "false");
#endif
#if MOLE_HAS_SLIDER
  Serial.print(",\"slider\":");
  Serial.print(mole_adc(MOLE_SLIDER_PIN));
#endif
#if MOLE_HAS_GAS
  Serial.print(",\"mq2\":");
  Serial.print(mole_adc(MOLE_GAS_PIN));
#endif
#if MOLE_HAS_BME
  Serial.print(",\"bme\":");
  Serial.print(mole_bme ? "true" : "false");
  if (mole_bme_id == 0x58) Serial.print(",\"chip\":\"BMP280\"");
  if (mole_bme_id == 0x60) Serial.print(",\"chip\":\"BME280\"");
#endif
#if MOLE_HAS_LCD
  Serial.print(",\"lcd\":");
  Serial.print(mole_lcd ? "true" : "false");
#endif
  Serial.print(",\"radio\":");
  Serial.print(mole_radio ? "true" : "false");
  Serial.print(",\"i2c\":\"");
  bool i2c_any = false;
  for (uint8_t addr = 1; addr < 127; addr++) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() != 0) continue;
    if (i2c_any) Serial.print(",");
    i2c_any = true;
    Serial.print("0x");
    if (addr < 16) Serial.print("0");
    Serial.print(addr, HEX);
    uint8_t chip = 0;
    if (i2c_read(addr, 0xD0, &chip, 1)) {
      Serial.print("/");
      Serial.print(chip, HEX);
    }
  }
  if (!i2c_any) Serial.print("none");
  Serial.println("\"}");
}

static void mole_loop() {
  static uint32_t next_ms = 0;
  if ((int32_t)(millis() - next_ms) < 0) return;
  next_ms = millis() + 1000;

  MolePacket packet = {};
  packet.version = MOLE_VERSION;
  packet.node_id = MOLE_NODE_ID;
  strncpy(packet.session_id, mole_session, 15);
  packet.sequence = mole_sequence++;
  packet.hops = 1;
  packet.tilt_cdeg = MOLE_MISSING;
  packet.vibration_c = MOLE_MISSING;
  packet.gas_raw = MOLE_MISSING;
  packet.slider_raw = MOLE_MISSING;
  packet.linear_raw = MOLE_MISSING;
  packet.temp_signal_raw = MOLE_MISSING;
  packet.temp_cdeg = MOLE_MISSING;
  packet.humidity_c = MOLE_MISSING;
  packet.pressure_hpa10 = MOLE_MISSING;

  float tilt = 0;
  float vibration = 0;
  bool mpu_ok = mole_mpu && mpu_sample(&tilt, &vibration);
  if (!mpu_ok && mole_mpu == 0) mpu_begin();
  if (mpu_ok) {
    packet.valid = 1;
    packet.tilt_cdeg = mole_clamp((int32_t)lroundf(tilt * 100.0f));
    packet.vibration_c = mole_clamp((int32_t)lroundf(vibration * 100.0f));
  }

#if MOLE_HAS_SLIDER
  packet.slider_raw = (int16_t)mole_adc(MOLE_SLIDER_PIN);
#endif
#if MOLE_HAS_TEMP_SIGNAL
  packet.temp_signal_raw = (int16_t)mole_adc(MOLE_PIN_TEMP_SIGNAL);
#endif
#if MOLE_HAS_LINEAR
  packet.linear_raw = (int16_t)mole_adc(MOLE_PIN_LINEAR);
#endif
  bool gas_alarm = false;
#if MOLE_HAS_GAS
  packet.gas_raw = (int16_t)mole_adc(MOLE_GAS_PIN);
  packet.gas_ready = millis() >= MOLE_GAS_WARMUP_MS ? 1 : 0;
  gas_alarm = packet.gas_ready && packet.gas_raw >= MOLE_GAS_RAW_ALERT;
#endif
#if MOLE_HAS_DS18B20
  if (!mole_ds_ok) {
    mole_ds.begin();
    mole_ds_ok = mole_ds.getDeviceCount() > 0;
    if (mole_ds_ok) {
      mole_ds.requestTemperatures();
      mole_ds_ready_at = millis() + 800;
    }
  } else if ((int32_t)(millis() - mole_ds_ready_at) >= 0) {
    float celsius = mole_ds.getTempCByIndex(0);
    if (celsius > -55.0f && celsius < 125.0f) {
      packet.temp_cdeg = mole_clamp((int32_t)lroundf(celsius * 100.0f));
    } else {
      mole_ds_ok = false;
    }
    mole_ds.requestTemperatures();
    mole_ds_ready_at = millis() + 800;
  }
#endif
#if MOLE_HAS_BME
  if (mole_bme) {
    int16_t temp_cdeg, humidity_c, pressure_hpa10;
    if (bme_read(&temp_cdeg, &humidity_c, &pressure_hpa10)) {
      packet.temp_cdeg = temp_cdeg;
      packet.humidity_c = humidity_c;
      packet.pressure_hpa10 = pressure_hpa10;
    }
  } else {
    bme_begin();
  }
#endif

  packet.condition = mole_condition(tilt, vibration, gas_alarm, mpu_ok);
  if (packet.condition == 2) {
    mole_alert_at = millis();
    if (!mole_buzz_latched) {
      mole_buzz_latched = 1;
      mole_buzz_until = millis() + 2000;
    }
  }
  if (mole_buzz_latched && (int32_t)(millis() - mole_alert_at) > 3000) mole_buzz_latched = 0;
  bool tilt_now = (int32_t)(mole_buzz_until - millis()) > 0;
#if MOLE_HAS_BUZZER
  ledcWrite(MOLE_BUZZER_PIN, tilt_now ? 128 : 0);
#endif
#if MOLE_HAS_LCD
  lcd_live(packet.temp_cdeg, packet.pressure_hpa10, tilt_now);
#endif

  if (mole_radio) {
    for (int attempt = 0; attempt < 3; attempt++) {
      if (esp_now_send(MOLE_RECEIVER_MAC, (const uint8_t *)&packet, sizeof(packet)) == ESP_OK) break;
      delay(5);
    }
  } else if (esp_now_init() == ESP_OK) {
    esp_wifi_set_channel(MOLE_CHANNEL, WIFI_SECOND_CHAN_NONE);
    esp_now_peer_info_t peer = {};
    memcpy(peer.peer_addr, MOLE_RECEIVER_MAC, 6);
    peer.channel = MOLE_CHANNEL;
    peer.encrypt = false;
    mole_radio = esp_now_add_peer(&peer) == ESP_OK;
  }
}
