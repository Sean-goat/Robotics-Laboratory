#include <Arduino.h>

#define POT_PIN 4        // ADC pin
#define BAUD_RATE 115200 // Baud rate for Serial
#define SAMPLE_MS 100    // Start with 100ms for clear readability

void setup() {
  Serial.begin(BAUD_RATE);
  delay(2000); // Give native USB CDC time to attach to the PC
  Serial.println("Starting ADC readings...");
}

void loop() {
  int raw = analogRead(POT_PIN);
  float volts = analogReadMilliVolts(POT_PIN) / 1000.0f;

  Serial.print(raw);
  Serial.print('\t');
  Serial.println(volts);

  delay(SAMPLE_MS);
}