#include <Arduino.h>

/*
 ESP32-C3 Potentiometer Plotter - Exercise
 Board: ESP32-C3-DevKitC-02
 Sensor: Pot wiper
*/

// === Constants ===
#define POT_PIN 4        // ADC pin
#define BAUD_RATE 115200 // Baud rate for Serial
#define SAMPLE_MS 10     // Sample delay (ms)

void setup() {
  Serial.begin(BAUD_RATE);
  // Optional: ensures full ADC attenuation range is active
  analogSetAttenuation(ADC_11db);

  while (!Serial && millis() < 3000) {
    delay(10);
  }
  Serial.println("Starting ADC readings...");
}

void loop() {
  // 1) Read raw ADC counts (0 - 4095)
  int raw = analogRead(POT_PIN);

  // 2) Read calibrated millivolts directly and convert to volts
  float volts = analogReadMilliVolts(POT_PIN) / 1000.0f;

  // 3) Print values for Serial Plotter (Curve 1: raw, Curve 2: volts)
  Serial.print(raw);
  Serial.print('\t');
  Serial.println(volts);

  delay(SAMPLE_MS);
}