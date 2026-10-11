#include <Arduino.h>
#include <SPI.h>
#include <MFRC522.h>

#define SS_PIN  53
#define RST_PIN 5

MFRC522 rfid(SS_PIN, RST_PIN);

// Desired UID from your original card
byte newUid[] = {0xEB, 0x42, 0x40, 0x43};

void setup() {
  Serial.begin(115200);
  while (!Serial);

  SPI.begin();
  rfid.PCD_Init();

  Serial.println(F("RC522 Ready. Place a rewritable (Gen1a) UID card on the reader..."));
}

void loop() {
  // Look for card
  if (!rfid.PICC_IsNewCardPresent()) {
    return;
  }

  // Select card
  if (!rfid.PICC_ReadCardSerial()) {
    return;
  }

  Serial.println(F("Card detected! Attempting to write UID..."));

  // Attempt to write the 4-byte UID using backdoor commands
  if (rfid.MIFARE_SetUid(newUid, (byte)4, true)) {
    Serial.println(F("Success: UID successfully changed to EB 42 40 43!"));
  } else {
    Serial.println(F("Failed: Card rejected Block 0 write (not a Gen1a magic card)."));
  }

  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();

  // Pause to avoid repeated execution
  delay(3000);
}