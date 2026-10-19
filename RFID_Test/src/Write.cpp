#include <Arduino.h>
#include <SPI.h>
#include <MFRC522.h>

#define SS_PIN  53
#define RST_PIN 5

MFRC522 rfid(SS_PIN, RST_PIN);
MFRC522::MIFARE_Key key;

// Target UID to clone
const byte newUid[4] = {_x__, _x__, _x__, _x__};

void setup() {
  Serial.begin(115200);
  while (!Serial);

  SPI.begin();
  rfid.PCD_Init();

  // Set default transport key: FF FF FF FF FF FF
  for (byte i = 0; i < 6; i++) {
    key.keyByte[i] = 0xFF;
  }

  Serial.println(F("CUID Writer ready. Place your tag on the reader..."));
}

void loop() {
  if (!rfid.PICC_IsNewCardPresent() || !rfid.PICC_ReadCardSerial()) {
    return;
  }

  Serial.print(F("Found tag with UID:"));
  for (byte i = 0; i < rfid.uid.size; i++) {
    Serial.print(rfid.uid.uidByte[i] < 0x10 ? " 0" : " ");
    Serial.print(rfid.uid.uidByte[i], HEX);
  }
  Serial.println();

  byte blockAddr = 0;
  byte trailerBlock = 3;

  // Authenticate Sector 0 using default Key A
  MFRC522::StatusCode status = (MFRC522::StatusCode) rfid.PCD_Authenticate(
    MFRC522::PICC_CMD_MF_AUTH_KEY_A, trailerBlock, &key, &(rfid.uid)
  );

  if (status != MFRC522::STATUS_OK) {
    Serial.print(F("Authentication failed: "));
    Serial.println(rfid.GetStatusCodeName(status));
    rfid.PICC_HaltA();
    rfid.PCD_StopCrypto1();
    delay(2000);
    return;
  }

  // Read current Block 0 to preserve manufacturer bytes
  byte buffer[18];
  byte size = sizeof(buffer);
  status = (MFRC522::StatusCode) rfid.MIFARE_Read(blockAddr, buffer, &size);
  if (status != MFRC522::STATUS_OK) {
    Serial.print(F("Read Block 0 failed: "));
    Serial.println(rfid.GetStatusCodeName(status));
    rfid.PICC_HaltA();
    rfid.PCD_StopCrypto1();
    delay(2000);
    return;
  }

  // Construct updated 16-byte Block 0
  byte newBlock0[16];
  for (byte i = 0; i < 16; i++) {
    newBlock0[i] = buffer[i];
  }

  // Insert the 4-byte UID
  newBlock0[0] = newUid[0];
  newBlock0[1] = newUid[1];
  newBlock0[2] = newUid[2];
  newBlock0[3] = newUid[3];
  
  // Calculate Block 0 BCC checksum: byte0 ^ byte1 ^ byte2 ^ byte3
  newBlock0[4] = newUid[0] ^ newUid[1] ^ newUid[2] ^ newUid[3];

  // Write new data into Block 0
  Serial.println(F("Writing new UID to Block 0..."));
  status = (MFRC522::StatusCode) rfid.MIFARE_Write(blockAddr, newBlock0, 16);

  if (status == MFRC522::STATUS_OK) {
    Serial.println(F("SUCCESS! Block 0 updated. UID changed to EB 42 40 43."));
  } else {
    Serial.print(F("Write rejected: "));
    Serial.println(rfid.GetStatusCodeName(status));
    Serial.println(F("Notice: Tag rejected Block 0 write (locked factory chip)."));
  }

  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();
  delay(3000);
}