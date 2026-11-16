/*
 * GY-91 Sensor (MPU9250 + BMP280) with ESP32-C3
 * The ESP32 C3 devkitc-02 is used in this example.
 * It does not have dedicated I2C pins, so GPIO4 and GPIO5 are used.
 * 
 * Wiring:
 * -------
 * GY-91 VCC -> ESP32-C3 3.3V
 * GY-91 GND -> ESP32-C3 GND
 * GY-91 SCL -> ESP32-C3 GPIO5
 * GY-91 SDA -> ESP32-C3 GPIO4
 */

#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_BMP085.h>

// MPU9250 I2C address and registers
#define MPU_ADDR 0x68
#define ACCEL_XOUT_H 0x3B

Adafruit_BMP085 bmp;

int16_t accelX, accelY, accelZ;
int16_t gyroX, gyroY, gyroZ;

// Write a byte to MPU register
void writeMPU(uint8_t reg, uint8_t data) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(reg);
  Wire.write(data);
  Wire.endTransmission();
}

// Read all sensor data from MPU
void readMPU() {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(ACCEL_XOUT_H);
  Wire.endTransmission(false);
  Wire.requestFrom(MPU_ADDR, 14);
  
  accelX = (Wire.read() << 8) | Wire.read();
  accelY = (Wire.read() << 8) | Wire.read();
  accelZ = (Wire.read() << 8) | Wire.read();
  Wire.read(); Wire.read();  // Skip temperature
  gyroX = (Wire.read() << 8) | Wire.read();
  gyroY = (Wire.read() << 8) | Wire.read();
  gyroZ = (Wire.read() << 8) | Wire.read();
}

void setup() {
  Serial.begin(115200);
  delay(2000);
  
  Serial.println("GY-91 Sensor Test");
  
  // Initialize I2C on GPIO4 (SDA) and GPIO5 (SCL)
  Wire.begin(6, 7);
  Wire.setClock(100000);
  writeMPU(0x6B, 0x00);  // Wake up MPU (clear SLEEP bit in PWR_MGMT_1)
  delay(100);
  delay(100);
  
  // Initialize BMP280 (try address 0x76, then 0x77)
  if (!bmp.begin(0x68) && !bmp.begin(0x77)) {
    Serial.println("BMP280 not found!");
    while (1);
  }
  
  Serial.println("Sensors initialized!");
  
  // Print CSV header
  Serial.println("accel_x,accel_y,accel_z,gyro_x,gyro_y,gyro_z,pressure,altitude");
}

void loop() {
  // Read sensor data
  readMPU();
  
  // Convert to real units
  float accelX_g = accelX / 16384.0;
  float accelY_g = accelY / 16384.0;
  float accelZ_g = accelZ / 16384.0;
  
  float gyroX_dps = gyroX / 131.0;
  float gyroY_dps = gyroY / 131.0;
  float gyroZ_dps = gyroZ / 131.0;
  
  float temperature = bmp.readTemperature();
  float pressure = bmp.readPressure() / 100.0;
  float altitude = bmp.readAltitude(1013.25);
  
  // Print data in CSV format: accel_x,accel_y,accel_z,gyro_x,gyro_y,gyro_z,pressure,altitude
  Serial.print(accelX_g, 4); Serial.print(",");
  Serial.print(accelY_g, 4); Serial.print(",");
  Serial.print(accelZ_g, 4); Serial.print(",");
  Serial.print(gyroX_dps, 4); Serial.print(",");
  Serial.print(gyroY_dps, 4); Serial.print(",");
  Serial.print(gyroZ_dps, 4); Serial.print(",");
  Serial.print(pressure, 2); Serial.print(",");
  Serial.println(altitude, 2);
  
  delay(40);  // 25 Hz sampling rate (1000ms / 25 = 40ms)
}