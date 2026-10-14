#include <Arduino.h>
#include <SPI.h>
#include <MFRC522.h>

#define SS_PIN  53
#define RST_PIN 5

MFRC522 rfid(SS_PIN, RST_PIN);

void setup() {
  Serial.begin(115200);
  while (!Serial);

  SPI.begin();
  rfid.PCD_Init();

  Serial.println(F("RC522 Ready. Scan an RFID card/tag..."));
}

void loop() {
  // Look for a new card
  if (!rfid.PICC_IsNewCardPresent()) {
    return;
  }

  // Select the card and read its UID
  if (!rfid.PICC_ReadCardSerial()) {
    return;
  }

  // Print card UID in hexadecimal format
  Serial.print(F("Card detected! UID:"));
  for (byte i = 0; i < rfid.uid.size; i++) {
    Serial.print(rfid.uid.uidByte[i] < 0x10 ? " 0" : " ");
    Serial.print(rfid.uid.uidByte[i], HEX);
  }
  Serial.println();

  // Print PICC card type
  MFRC522::PICC_Type piccType = rfid.PICC_GetType(rfid.uid.sak);
  Serial.print(F("PICC type: "));
  Serial.println(rfid.PICC_GetTypeName(piccType));

  // Put card into halt state and stop encryption
  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();

  // Debounce delay to prevent repeated scans of the same card
  delay(1000);
}