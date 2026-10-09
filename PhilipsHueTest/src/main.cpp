#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>

// === Wi-Fi Credentials ===
const char* ssid     = "ICO-3CDEDB";
const char* password = "avvufutKarj7";

// === Philips Hue Bridge Settings ===
const char* hueBridgeIP = "192.168.0.161";
const char* hueUsername = "vPADFQtPb5GarFNcyjuReSGZNFJLG-y3f88PS0BQ";
const int groupId       = 5; // "Sean værelse" (contains lights 8, 11, 12, 15)

// === Hardware Pin ===
#define POT_PIN 32

// === Timing & Filtering ===
int lastSentBri = -1;
unsigned long lastSendTime = 0;
const unsigned long SEND_INTERVAL_MS = 100; // Limit requests to 10 Hz max

void setHueBrightness(int bri) {
  if (WiFi.status() != WL_CONNECTED) return;

  HTTPClient http;
  // Use /groups/<id>/action for controlling an entire room
  String url = String("http://") + hueBridgeIP + "/api/" + hueUsername + "/groups/" + groupId + "/action";

  http.begin(url);
  http.addHeader("Content-Type", "application/json");

  String payload;
  if (bri <= 0) {
    // If turned all the way down, switch off the entire room
    payload = "{\"on\":false}";
  } else {
    // Keep brightness within valid Hue range [1, 254]
    int safeBri = constrain(bri, 1, 254);
    payload = "{\"on\":true,\"bri\":" + String(safeBri) + ",\"transitiontime\":1}";
  }

  int httpCode = http.PUT(payload);
  if (httpCode > 0) {
    String response = http.getString();
    Serial.printf("Room Bri: %d (HTTP %d) -> %s\n", bri, httpCode, response.c_str());
  } else {
    Serial.printf("HTTP PUT failed: %s\n", http.errorToString(httpCode).c_str());
  }

  http.end();
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.printf("Connecting to Wi-Fi: %s", ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWi-Fi connected!");
  Serial.print("ESP32 IP: ");
  Serial.println(WiFi.localIP());
}

void loop() {
  // 1. Read calibrated millivolts
  float measuredVolts = analogReadMilliVolts(POT_PIN) / 1000.0f;

  // 2. Compensate for ESP32 ADC non-linear dead zones (0.15V to 3.15V)
  float cleanVolts = constrain(measuredVolts, 0.15f, 3.15f);

  // 3. Map linear voltage to Hue brightness: 0 (off) to 254 (max)
  int targetBri = (int)(((cleanVolts - 0.15f) / (3.15f - 0.15f)) * 254.0f);

  // 4. Rate-limit and apply deadband to avoid flooding the Zigbee network
  unsigned long now = millis();
  if (abs(targetBri - lastSentBri) >= 4 && (now - lastSendTime >= SEND_INTERVAL_MS)) {
    lastSentBri = targetBri;
    lastSendTime = now;
    setHueBrightness(targetBri);
  }

  delay(20);
}