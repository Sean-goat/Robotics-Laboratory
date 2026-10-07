#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>

// === 1. Put Your Home Wi-Fi Details Here ===
const char* ssid     = "ICO-3CDEDB";
const char* password = "avvufutKarj7";

// === 2. Your Confirmed Philips Hue Details ===
const char* hueBridgeIP = "192.168.0.161";
const char* hueUser     = "dsOZKVQZU7RR9P-jBnJY1CrlUduebKzrytGLYehP";
const int   groupId     = 5; // "0 = the entire house, 5 = Sean værelse"

// === 3. Hardware Button ===
// Top button on the LILYGO T-Display is GPIO 35
#define BUTTON_PIN 35 

bool roomState = false;

void setRoomLights(bool turnOn) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi not connected!");
    return;
  }

  HTTPClient http;
  String url = String("http://") + hueBridgeIP + "/api/" + hueUser + "/groups/" + String(groupId) + "/action";

  http.begin(url);
  http.addHeader("Content-Type", "application/json");

  String payload = turnOn ? "{\"on\":true}" : "{\"on\":false}";
  Serial.printf("Sending to Room %d: %s\n", groupId, payload.c_str());

  int httpCode = http.PUT(payload);

  if (httpCode > 0) {
    String resp = http.getString();
    Serial.printf("Response [%d]: %s\n", httpCode, resp.c_str());
  } else {
    Serial.printf("HTTP PUT failed: %s\n", http.errorToString(httpCode).c_str());
  }

  http.end();
}

void setup() {
  Serial.begin(115200);
  pinMode(BUTTON_PIN, INPUT_PULLUP);

  Serial.printf("\nConnecting to %s", ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi connected!");
  Serial.print("ESP32 IP: ");
  Serial.println(WiFi.localIP());
  Serial.println("Ready! Press the top button (GPIO 35) to toggle Sean værelse.");
}

void loop() {
  // Read button (active LOW on GPIO 35)
  if (digitalRead(BUTTON_PIN) == LOW) {
    delay(50); // Software debounce
    if (digitalRead(BUTTON_PIN) == LOW) {
      roomState = !roomState;
      setRoomLights(roomState);

      // Wait until button is released
      while (digitalRead(BUTTON_PIN) == LOW) {
        delay(10);
      }
    }
  }
}