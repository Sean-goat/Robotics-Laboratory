#include <Arduino.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

// Definer UUIDs for GATT Service og Characteristic
#define SERVICE_UUID        "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define CHARACTERISTIC_UUID "beb5483e-36e1-4688-b7f5-ea07361b26a8"

const int POT_PIN = 4;
BLECharacteristic *pCharacteristic = nullptr;
bool deviceConnected = false;

// Callbacks til overvågning af forbindelsesstatus
class MyServerCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer* pServer) override {
    deviceConnected = true;
  }

  void onDisconnect(BLEServer* pServer) override {
    deviceConnected = false;
    // Genstart advertising, så klienten kan genforbinde
    BLEDevice::startAdvertising();
  }
};

void setup() {
  Serial.begin(115200);
  delay(1500); // Giver USB CDC tid til at forbinde til PC

  // Initialiser BLE med enhedens navn
  BLEDevice::init("ESP32_BLE_Server");

  // Opret BLE Server
  BLEServer *pServer = BLEDevice::createServer();
  pServer->setCallbacks(new MyServerCallbacks());

  // Opret BLE Service
  BLEService *pService = pServer->createService(SERVICE_UUID);

  // Opret GATT Characteristic med læse- og notify-rettigheder
  pCharacteristic = pService->createCharacteristic(
                      CHARACTERISTIC_UUID,
                      BLECharacteristic::PROPERTY_READ |
                      BLECharacteristic::PROPERTY_NOTIFY
                    );

  pCharacteristic->addDescriptor(new BLE2902());

  // Start servicen og påbegynd advertising
  pService->start();
  BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pAdvertising->setScanResponse(true);
  pAdvertising->setMinPreferred(0x06);
  pAdvertising->setMinPreferred(0x12);
  BLEDevice::startAdvertising();

  Serial.println("BLE Server startet, afventer klientforbindelse...");
}

void loop() {
  // Læs potentiometer (spænding i volt med 3 decimaler)
  float voltage = analogReadMilliVolts(POT_PIN) / 1000.0f;
  String valStr = String(voltage, 3);

  // Opdater BLE Characteristic værdi
  pCharacteristic->setValue(valStr.c_str());
  
  if (deviceConnected) {
    pCharacteristic->notify();
  }

  // Print format iht. opgaveteksten
  Serial.print("værdi klar: ");
  Serial.println(valStr);

  delay(100); // 100 ms interval
}