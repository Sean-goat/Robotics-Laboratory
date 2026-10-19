#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <TFT_eSPI.h>
#include <ArduinoJson.h>
#include <time.h>

// === Wi-Fi Credentials ===
const char* ssid     = "Nuh uhh";
const char* password = "Nuh uhh";

// === Philips Hue Bridge Settings ===
const char* hueBridgeIP = "xxx.xxx.x.xxx";
const char* hueUsername = "vPADFQtPb5GarFNcyjuReSGZNFJLG-y3f88PS0BQ";
const int groupId       = 5; // "Sean værelse"

// === NTP Time Configuration (Denmark / Central European Time with DST) ===
const char* ntpServer = "dk.pool.ntp.org";
const char* tzInfo    = "CET-1CEST,M3.5.0,M10.5.0/3";

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

// === Wake-Up Alarm State ===
bool wakeUpTriggeredToday = false;
unsigned long lastClockTick = 0;
String lastDrawnTime = "";

// UI State Cache
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
    tft.fillCircle(222, 20, 10, TFT_BLACK);

    if (isLightOn) {
      tft.fillCircle(222, 20, 8, TFT_YELLOW);
    } else {
      tft.drawCircle(222, 20, 8, TFT_WHITE);
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

    tft.fillRect(10, 82, 130, 20, TFT_BLACK);
    tft.setTextColor(TFT_CYAN, TFT_BLACK);
    tft.drawString("Bri: " + String(percent) + "%", 10, 82, 2);
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

void drawClockTime(const String& timeStr) {
  if (timeStr != lastDrawnTime) {
    lastDrawnTime = timeStr;
    tft.fillRect(150, 82, 80, 20, TFT_BLACK);
    tft.setTextColor(TFT_LIGHTGREY, TFT_BLACK);
    tft.drawString(timeStr, 160, 82, 2);
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

  tft.init();
  tft.setRotation(1);
  tft.fillScreen(TFT_BLACK);
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.drawString("Connecting Wi-Fi...", 10, 50, 4);

  pinMode(SWITCH_PIN, INPUT_PULLUP);
  pinMode(BTN_NEXT_PIN, INPUT);
  pinMode(BTN_PREV_PIN, INPUT_PULLUP);

  lastStableSwitchVal = digitalRead(SWITCH_PIN);
  isLightOn = (lastStableSwitchVal == LOW);

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWi-Fi connected!");

  // Sync internal clock via NTP with Denmark daylight savings
  configTzTime(tzInfo, ntpServer);

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
  // 1. Clock Check & 06:30 Wake-Up Alarm Routine
  // -------------------------------------------------------------
  if (now - lastClockTick >= 1000) {
    lastClockTick = now;
    struct tm timeinfo;
    if (getLocalTime(&timeinfo)) {
      char timeBuffer[10];
      strftime(timeBuffer, sizeof(timeBuffer), "%H:%M", &timeinfo);
      drawClockTime(String(timeBuffer));

      // Trigger 15-minute sunrise fade at 06:30 AM
      if (timeinfo.tm_hour == 6 && timeinfo.tm_min == 30 && !wakeUpTriggeredToday) {
        wakeUpTriggeredToday = true;
        Serial.println("Wake-up routine triggered: Fading to 80% over 15 minutes");

        // 80% brightness = 203 (out of 254)
        // 15 minutes = 900 seconds = 9000 deciseconds
        // First set to minimum brightness, then begin the 15-minute fade
        sendHueCommand("{\"on\":true,\"bri\":1,\"transitiontime\":0}");
        delay(100);
        sendHueCommand("{\"on\":true,\"bri\":203,\"transitiontime\":9000}");

        isLightOn = true;
        lastSentBri = 203;
        updateDisplay(80);
      }

      // Reset trigger flag at midnight
      if (timeinfo.tm_hour == 0 && timeinfo.tm_min == 0) {
        wakeUpTriggeredToday = false;
      }
    }
  }

  // -------------------------------------------------------------
  // 2. Toggle Switch
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
  // 3. Scene Buttons (GPIO 35 = Next, GPIO 0 = Prev)
  // -------------------------------------------------------------
  int btnNextVal = digitalRead(BTN_NEXT_PIN);
  if (btnNextVal == LOW && lastBtnNextVal == HIGH && (now - lastBtnNextPress > 350)) {
    lastBtnNextPress = now;
    if (totalScenes > 0 && isLightOn) {
      currentSceneIdx = (currentSceneIdx + 1) % totalScenes;
      recallScene(roomScenes[currentSceneIdx].id);
      int currentPercent = map(constrain(lastSentBri, 1, 254), 1, 254, 0, 100);
      updateDisplay(currentPercent);
    }
  }
  lastBtnNextVal = btnNextVal;

  int btnPrevVal = digitalRead(BTN_PREV_PIN);
  if (btnPrevVal == LOW && lastBtnPrevVal == HIGH && (now - lastBtnPrevPress > 350)) {
    lastBtnPrevPress = now;
    if (totalScenes > 0 && isLightOn) {
      currentSceneIdx = (currentSceneIdx - 1 + totalScenes) % totalScenes;
      recallScene(roomScenes[currentSceneIdx].id);
      int currentPercent = map(constrain(lastSentBri, 1, 254), 1, 254, 0, 100);
      updateDisplay(currentPercent);
    }
  }
  lastBtnPrevVal = btnPrevVal;

  // -------------------------------------------------------------
  // 4. Potentiometer Dimming & Snapping
  // -------------------------------------------------------------
  if (isLightOn) {
    float rawVolts = constrain(analogReadMilliVolts(POT_PIN) / 1000.0f, 0.15f, 3.15f);
    smoothedVolts = (EMA_ALPHA * rawVolts) + ((1.0f - EMA_ALPHA) * smoothedVolts);

    float rawPercent = ((smoothedVolts - 0.15f) / (3.15f - 0.15f)) * 100.0f;
    int displayPercent = 0;
    int targetBri = 0;

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