#include <Arduino.h>
#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEScan.h>
#include <BLEAdvertisedDevice.h>

// Samme UUIDs som i serveren
static BLEUUID serviceUUID("4fafc201-1fb5-459e-8fcc-c5c9c331914b");
static BLEUUID charUUID("beb5483e-36e1-4688-b7f5-ea07361b26a8");

static boolean doConnect = false;
static boolean connected = false;
static boolean doScan = false;
static BLERemoteCharacteristic* pRemoteCharacteristic = nullptr;
static BLEAdvertisedDevice* myDevice = nullptr;

// Scanner-callback der søger efter serveren
class MyAdvertisedDeviceCallbacks : public BLEAdvertisedDeviceCallbacks {
  void onResult(BLEAdvertisedDevice advertisedDevice) override {
    if (advertisedDevice.haveServiceUUID() && advertisedDevice.isAdvertisingService(serviceUUID)) {
      BLEDevice::getScan()->stop();
      myDevice = new BLEAdvertisedDevice(advertisedDevice);
      doConnect = true;
      doScan = false;
    }
  }
};

bool connectToServer() {
  Serial.print("Forbinder til server: ");
  Serial.println(myDevice->getAddress().toString().c_str());

  BLEClient* pClient = BLEDevice::createClient();

  if (!pClient->connect(myDevice)) {
    return false;
  }

  // Hent servicen fra serveren
  BLERemoteService* pRemoteService = pClient->getService(serviceUUID);
  if (pRemoteService == nullptr) {
    pClient->disconnect();
    return false;
  }

  // Hent characteristic
  pRemoteCharacteristic = pRemoteService->getCharacteristic(charUUID);
  if (pRemoteCharacteristic == nullptr) {
    pClient->disconnect();
    return false;
  }

  connected = true;
  return true;
}

void setup() {
  Serial.begin(115200);
  delay(1500);

  Serial.println("Starter BLE Klient...");
  BLEDevice::init("ESP32_BLE_Client");

  // Opsæt scanning
  BLEScan* pBLEScan = BLEDevice::getScan();
  pBLEScan->setAdvertisedDeviceCallbacks(new MyAdvertisedDeviceCallbacks());
  pBLEScan->setInterval(1349);
  pBLEScan->setWindow(449);
  pBLEScan->setActiveScan(true);
  pBLEScan->start(5, false);
}

void loop() {
  if (doConnect) {
    if (connectToServer()) {
      Serial.println("Forbundet til BLE server.");
    } else {
      Serial.println("Forbindelse mislykkedes, prøver igen...");
    }
    doConnect = false;
  }

  if (connected && pRemoteCharacteristic != nullptr) {
    // Læs data direkte som Arduino String
    String valStr = pRemoteCharacteristic->readValue();

    // Udskriv format iht. opgaveteksten
    Serial.print("værdi læst: ");
    Serial.println(valStr);
  } else if (!connected && !doScan) {
    // Hvis forbindelsen mistes, start scanning igen
    BLEDevice::getScan()->start(0);
    doScan = true;
  }

  delay(100); // 100 ms samplingsrate
}