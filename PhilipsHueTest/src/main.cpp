#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <TFT_eSPI.h>
#include <ArduinoJson.h>

// === Wi-Fi Credentials ===
const char* ssid     = "ICO-3CDEDB";
const char* password = "avvufutKarj7";

// === Philips Hue Bridge Settings ===
const char* hueBridgeIP = "192.168.0.161";
const char* hueUsername = "vPADFQtPb5GarFNcyjuReSGZNFJLG-y3f88PS0BQ";
const int groupId       = 5; // "Sean værelse"

// === Hardware Pins ===
#define POT_PIN      32  // Potentiometer wiper (ADC)
#define SWITCH_PIN   21  // T80-T toggle switch to GND
#define BTN_NEXT_PIN 35  // Onboard Right button: Next Scene
#define BTN_PREV_PIN 0   // Onboard Left button: Previous Scene

// === Display Instance ===
TFT_eSPI tft = TFT_eSPI();

// === Scenes Storage ===
struct SceneItem {
  String id;
  String name;
};
const int MAX_SCENES = 16;
SceneItem roomScenes[MAX_SCENES];
int totalScenes = 0;
int currentSceneIdx = 0;

// === Switch & Buttons State Tracking ===
bool isLightOn = true;
int lastStableSwitchVal = HIGH;
int lastReadSwitchVal   = HIGH;
unsigned long lastDebounceTime = 0;
const unsigned long DEBOUNCE_DELAY_MS = 25;

int lastBtnNextVal = HIGH;
unsigned long lastBtnNextPress = 0;

int lastBtnPrevVal = HIGH;
unsigned long lastBtnPrevPress = 0;

// === Potentiometer Tuning ===
float smoothedVolts = -1.0f;
const float EMA_ALPHA = 0.40f;
int lastSentBri = -1;
unsigned long lastSendTime = 0;
const unsigned long SEND_INTERVAL_MS = 250;
const int BRI_DEADBAND = 10;

// UI State Cache to prevent flicker
int lastDrawnPercent = -1;
bool lastDrawnPower = false;
String lastDrawnScene = "";

// -------------------------------------------------------------
// UI Drawing Functions
// -------------------------------------------------------------
void updateDisplay(int percent, bool forceRedraw = false) {
  if (forceRedraw) {
    tft.fillScreen(TFT_BLACK);
    tft.setTextColor(TFT_WHITE, TFT_BLACK);
    tft.drawString("Sean Værelse", 10, 10, 4);
    
    // Slider container outline
    tft.drawRoundRect(10, 50, 220, 24, 6, TFT_DARKGREY);
    tft.drawRoundRect(9, 49, 222, 26, 6, TFT_DARKGREY);
  }

  // 1. Power Circle (Filled when ON, Hollow when OFF)
  if (forceRedraw || (isLightOn != lastDrawnPower)) {
    lastDrawnPower = isLightOn;
    tft.fillCircle(210, 20, 12, TFT_BLACK);

    if (isLightOn) {
      tft.fillCircle(210, 20, 10, TFT_YELLOW);
    } else {
      tft.drawCircle(210, 20, 10, TFT_WHITE);
      tft.drawCircle(210, 20, 9, TFT_WHITE);
    }
  }

  // 2. Brightness Slider Bar
  if (forceRedraw || (percent != lastDrawnPercent)) {
    lastDrawnPercent = percent;

    int fillWidth = map(percent, 0, 100, 0, 214);
    if (fillWidth > 0 && isLightOn) {
      tft.fillRoundRect(13, 53, fillWidth, 18, 4, TFT_ORANGE);
    }
    if (fillWidth < 214) {
      tft.fillRoundRect(13 + fillWidth, 53, 214 - fillWidth, 18, 4, TFT_BLACK);
    }

    tft.fillRect(10, 85, 220, 20, TFT_BLACK);
    tft.setTextColor(TFT_CYAN, TFT_BLACK);
    tft.drawString("Brightness: " + String(percent) + "%", 10, 85, 2);
  }

  // 3. Scene Name
  String sceneName = (totalScenes > 0) ? roomScenes[currentSceneIdx].name : "No Scenes";
  if (forceRedraw || (sceneName != lastDrawnScene)) {
    lastDrawnScene = sceneName;
    tft.fillRect(10, 105, 220, 25, TFT_BLACK);
    tft.setTextColor(TFT_GREEN, TFT_BLACK);
    tft.drawString("Scene: " + sceneName, 10, 110, 2);
  }
}

// -------------------------------------------------------------
// Philips Hue Network Calls
// -------------------------------------------------------------
void sendHueCommand(const String& payload) {
  if (WiFi.status() != WL_CONNECTED) return;

  HTTPClient http;
  String url = String("http://") + hueBridgeIP + "/api/" + hueUsername + "/groups/" + groupId + "/action";

  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  http.PUT(payload);
  http.end();
}

void fetchRoomScenes() {
  if (WiFi.status() != WL_CONNECTED) return;

  HTTPClient http;
  String url = String("http://") + hueBridgeIP + "/api/" + hueUsername + "/scenes";

  http.begin(url);
  int httpCode = http.GET();

  if (httpCode == 200) {
    String payload = http.getString();
    JsonDocument doc;
    DeserializationError error = deserializeJson(doc, payload);

    if (!error) {
      totalScenes = 0;
      JsonObject root = doc.as<JsonObject>();

      for (JsonPair kv : root) {
        JsonObject sceneObj = kv.value().as<JsonObject>();
        if (sceneObj["group"].as<int>() == groupId && totalScenes < MAX_SCENES) {
          roomScenes[totalScenes].id = String(kv.key().c_str());
          roomScenes[totalScenes].name = sceneObj["name"].as<String>();
          totalScenes++;
        }
      }
      Serial.printf("Total scenes found: %d\n", totalScenes);
    }
  }
  http.end();
}

void recallScene(const String& sceneId) {
  sendHueCommand("{\"scene\":\"" + sceneId + "\"}");
}

// -------------------------------------------------------------
// Setup & Main Loop
// -------------------------------------------------------------
void setup() {
  Serial.begin(115200);

  // Initialize Display
  tft.init();
  tft.setRotation(1);
  tft.fillScreen(TFT_BLACK);
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.drawString("Connecting Wi-Fi...", 10, 50, 4);

  // Pin Modes
  pinMode(SWITCH_PIN, INPUT_PULLUP);
  pinMode(BTN_NEXT_PIN, INPUT);        // GPIO 35 (hardware pull-up onboard)
  pinMode(BTN_PREV_PIN, INPUT_PULLUP); // GPIO 0 (boot button, needs pull-up)

  lastStableSwitchVal = digitalRead(SWITCH_PIN);
  isLightOn = (lastStableSwitchVal == LOW);

  // Wi-Fi Connection
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWi-Fi connected!");

  fetchRoomScenes();

  float initial = analogReadMilliVolts(POT_PIN) / 1000.0f;
  smoothedVolts = constrain(initial, 0.15f, 3.15f);
  int initialPercent = map((int)(smoothedVolts * 1000), 150, 3150, 0, 100);
  lastSentBri = map(initialPercent, 0, 100, 1, 254);

  updateDisplay(initialPercent, true);
}

void loop() {
  unsigned long now = millis();

  // -------------------------------------------------------------
  // 1. Toggle Switch
  // -------------------------------------------------------------
  int reading = digitalRead(SWITCH_PIN);
  if (reading != lastReadSwitchVal) {
    lastDebounceTime = now;
    lastReadSwitchVal = reading;
  }

  if ((now - lastDebounceTime) > DEBOUNCE_DELAY_MS) {
    if (reading != lastStableSwitchVal) {
      lastStableSwitchVal = reading;
      isLightOn = (lastStableSwitchVal == LOW);

      if (isLightOn) {
        int briToSend = (lastSentBri > 0) ? lastSentBri : 150;
        sendHueCommand("{\"on\":true,\"bri\":" + String(briToSend) + ",\"transitiontime\":1}");
      } else {
        sendHueCommand("{\"on\":false}");
      }
      int currentPercent = map(constrain(lastSentBri, 1, 254), 1, 254, 0, 100);
      updateDisplay(currentPercent);
    }
  }

  // -------------------------------------------------------------
  // 2. Button 1: Next Scene (GPIO 35)
  // -------------------------------------------------------------
  int btnNextVal = digitalRead(BTN_NEXT_PIN);
  if (btnNextVal == LOW && lastBtnNextVal == HIGH && (now - lastBtnNextPress > 350)) {
    lastBtnNextPress = now;
    if (totalScenes > 0 && isLightOn) {
      currentSceneIdx = (currentSceneIdx + 1) % totalScenes; // Forward
      recallScene(roomScenes[currentSceneIdx].id);
      int currentPercent = map(constrain(lastSentBri, 1, 254), 1, 254, 0, 100);
      updateDisplay(currentPercent);
    }
  }
  lastBtnNextVal = btnNextVal;

  // -------------------------------------------------------------
  // 3. Button 2: Previous Scene (GPIO 0)
  // -------------------------------------------------------------
  int btnPrevVal = digitalRead(BTN_PREV_PIN);
  if (btnPrevVal == LOW && lastBtnPrevVal == HIGH && (now - lastBtnPrevPress > 350)) {
    lastBtnPrevPress = now;
    if (totalScenes > 0 && isLightOn) {
      currentSceneIdx = (currentSceneIdx - 1 + totalScenes) % totalScenes; // Backward
      recallScene(roomScenes[currentSceneIdx].id);
      int currentPercent = map(constrain(lastSentBri, 1, 254), 1, 254, 0, 100);
      updateDisplay(currentPercent);
    }
  }
  lastBtnPrevVal = btnPrevVal;

  // -------------------------------------------------------------
  // 4. Potentiometer Dimming & Snapping (3% -> 0%, 97% -> 100%)
  // -------------------------------------------------------------
  if (isLightOn) {
    float rawVolts = constrain(analogReadMilliVolts(POT_PIN) / 1000.0f, 0.15f, 3.15f);
    smoothedVolts = (EMA_ALPHA * rawVolts) + ((1.0f - EMA_ALPHA) * smoothedVolts);

    // Compute raw 0-100%
    float rawPercent = ((smoothedVolts - 0.15f) / (3.15f - 0.15f)) * 100.0f;
    int displayPercent = 0;
    int targetBri = 0;

    // Boundary snap thresholds
    if (rawPercent <= 3.0f) {
      displayPercent = 0;
      targetBri = 0;
    } else if (rawPercent >= 97.0f) {
      displayPercent = 100;
      targetBri = 254;
    } else {
      displayPercent = (int)rawPercent;
      targetBri = map(displayPercent, 1, 100, 1, 254);
    }

    // Send update on genuine change
    if (abs(targetBri - lastSentBri) >= BRI_DEADBAND && (now - lastSendTime >= SEND_INTERVAL_MS)) {
      lastSentBri = targetBri;
      lastSendTime = now;

      if (targetBri == 0) {
        sendHueCommand("{\"on\":false}");
      } else {
        sendHueCommand("{\"on\":true,\"bri\":" + String(targetBri) + ",\"transitiontime\":0}");
      }
      updateDisplay(displayPercent);
    }
  }

  delay(15);
}