#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_BMP085.h>

#define MPU_ADDR     0x68
#define PWR_MGMT_1   0x6B
#define ACCEL_XOUT_H 0x3B

Adafruit_BMP085 bmp;

int16_t accelX, accelY, accelZ;
int16_t gyroX, gyroY, gyroZ;

void writeMPU(uint8_t reg, uint8_t data) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(reg);
  Wire.write(data);
  Wire.endTransmission();
}

void readMPU() {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(ACCEL_XOUT_H);
  Wire.endTransmission(false);
  Wire.requestFrom(MPU_ADDR, 14);

  accelX = (Wire.read() << 8) | Wire.read();
  accelY = (Wire.read() << 8) | Wire.read();
  accelZ = (Wire.read() << 8) | Wire.read();
  Wire.read(); Wire.read(); // Skip temperature
  gyroX = (Wire.read() << 8) | Wire.read();
  gyroY = (Wire.read() << 8) | Wire.read();
  gyroZ = (Wire.read() << 8) | Wire.read();
}

void setup() {
  Serial.begin(115200);
  delay(2000);

  Serial.println("MPU + BMP180 Sensor Test");

  Wire.begin(6, 7); // SDA = GPIO 6, SCL = GPIO 7
  Wire.setClock(100000);
  delay(100);

  // Wake up MPU
  writeMPU(PWR_MGMT_1, 0x00);
  delay(100);

  // Initialize BMP180 (hardcoded to 0x77)
  if (!bmp.begin()) {
    Serial.println("BMP180 not found!");
    while (1);
  }

  Serial.println("Sensors initialized!\n");
}

void loop() {
  readMPU();

  float accelX_g = accelX / 16384.0;
  float accelY_g = accelY / 16384.0;
  float accelZ_g = accelZ / 16384.0;

  float gyroX_dps = gyroX / 131.0;
  float gyroY_dps = gyroY / 131.0;
  float gyroZ_dps = gyroZ / 131.0;

  float temperature = bmp.readTemperature();
  float pressure = bmp.readPressure() / 100.0;
  float altitude = bmp.readAltitude(101325); // Sea-level pressure in Pa

  Serial.println("=== Sensor Data ===");
  Serial.print("Accel X: "); Serial.print(accelX_g, 2); Serial.print(" g, ");
  Serial.print("Y: "); Serial.print(accelY_g, 2); Serial.print(" g, ");
  Serial.print("Z: "); Serial.print(accelZ_g, 2); Serial.println(" g");

  Serial.print("Gyro  X: "); Serial.print(gyroX_dps, 2); Serial.print(" deg/s, ");
  Serial.print("Y: "); Serial.print(gyroY_dps, 2); Serial.print(" deg/s, ");
  Serial.print("Z: "); Serial.print(gyroZ_dps, 2); Serial.println(" deg/s");

  Serial.print("Temperature: "); Serial.print(temperature, 2); Serial.println(" °C");
  Serial.print("Pressure: "); Serial.print(pressure, 1); Serial.println(" hPa");
  Serial.print("Altitude: "); Serial.print(altitude, 1); Serial.println(" m");
  Serial.println();

  delay(1000);
}