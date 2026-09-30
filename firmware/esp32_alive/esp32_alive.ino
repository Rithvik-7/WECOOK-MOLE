// Classic ESP32 alive test. Board: ESP32 Dev Module. Serial: 115200.
// Onboard LED on most DevKit boards is GPIO 2.

void setup() {
  Serial.begin(115200);
  pinMode(2, OUTPUT);
  delay(300);
  Serial.println("ESP32 alive");
}

void loop() {
  digitalWrite(2, !digitalRead(2));
  Serial.print("tick ");
  Serial.println(millis());
  delay(500);
}
