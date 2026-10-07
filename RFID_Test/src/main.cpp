#include <Arduino.h>
#include <SPI.h>
#include <MFRC522.h>

// Define SPI SS and Reset pins for Arduino Mega
#define SS_PIN  53
#define RST_PIN 5

MFRC522 rfid(SS_PIN, RST_PIN);

void setup() {
  Serial.begin(115200);
  while (!Serial); // Wait for serial port to open

  SPI.begin();     // Initialize SPI bus
  rfid.PCD_Init(); // Initialize MFRC522 reader

  Serial.println(F("RC522 RFID Reader Initialized"));
  Serial.println(F("Hold an RFID tag or card near the reader..."));
}

void loop() {
  // Check if a new card is placed near the antenna
  if (!rfid.PICC_IsNewCardPresent()) {
    return;
  }

  // Read card serial number / UID
  if (!rfid.PICC_ReadCardSerial()) {
    return;
  }

  // Print the Card Type
  MFRC522::PICC_Type piccType = rfid.PICC_GetType(rfid.uid.sak);
  Serial.print(F("Tag Type: "));
  Serial.println(rfid.PICC_GetTypeName(piccType));

  // Print UID in Hexadecimal format
  Serial.print(F("UID Tag: "));
  for (byte i = 0; i < rfid.uid.size; i++) {
    if (rfid.uid.uidByte[i] < 0x10) {
      Serial.print(F(" 0"));
    } else {
      Serial.print(F(" "));
    }
    Serial.print(rfid.uid.uidByte[i], HEX);
  }
  Serial.println();

  // Halt PICC to stop reading the same card continuously
  rfid.PICC_HaltA();
  // Stop encryption on PCD
  rfid.PCD_StopCrypto1();

  delay(500);
}