#include <Arduino.h>
#include <Wire.h>

// Default I2C pins for ESP32-C3
#define I2C_SDA 8
#define I2C_SCL 9

void setup() {
  Serial.begin(115200);
  while (!Serial) {
    delay(10);
  }
  
  Serial.println("\nI2C Scanner");
  Serial.println("===========");
  
  // Initialize I2C with custom pins
  Wire.begin(I2C_SDA, I2C_SCL);
  
  Serial.printf("SDA Pin: %d\n", I2C_SDA);
  Serial.printf("SCL Pin: %d\n", I2C_SCL);
  Serial.println("\nScanning I2C bus...\n");
}

void loop() {
  byte error, address;
  int deviceCount = 0;

  Serial.println("     0  1  2  3  4  5  6  7  8  9  A  B  C  D  E  F");
  Serial.println("00:         ");
  
  for (address = 1; address < 127; address++) {
    // Print address row header
    if (address % 16 == 0) {
      Serial.printf("%02X: ", address);
    }
    
    Wire.beginTransmission(address);
    error = Wire.endTransmission();

    if (error == 0) {
      // Device found
      Serial.printf("%02X ", address);
      deviceCount++;
    } else if (error == 4) {
      // Unknown error
      Serial.print("?? ");
    } else {
      // No device at this address
      Serial.print("-- ");
    }

    // New line after every 16 addresses
    if ((address + 1) % 16 == 0) {
      Serial.println();
    }
  }

  Serial.println("\n");
  
  if (deviceCount == 0) {
    Serial.println("No I2C devices found!\n");
  } else {
    Serial.printf("Found %d I2C device(s)\n\n", deviceCount);
    
    // Print list of found devices with common device names
    Serial.println("Device addresses:");
    for (address = 1; address < 127; address++) {
      Wire.beginTransmission(address);
      error = Wire.endTransmission();
      
      if (error == 0) {
        Serial.printf("  0x%02X (%d)", address, address);
        
        // Identify common devices
        switch (address) {
          case 0x68: Serial.print(" - MPU6050/MPU9250 IMU or DS1307 RTC"); break;
          case 0x76: Serial.print(" - BMP280/BME280"); break;
          case 0x77: Serial.print(" - BMP280/BME280/BMP180"); break;
          case 0x3C: Serial.print(" - OLED Display (128x64)"); break;
          case 0x3D: Serial.print(" - OLED Display"); break;
          case 0x27: Serial.print(" - LCD Display (PCF8574)"); break;
          case 0x57: Serial.print(" - EEPROM (AT24C32)"); break;
          case 0x5A: Serial.print(" - MLX90614 IR Temperature"); break;
          case 0x48: Serial.print(" - ADS1115 ADC or PCF8591"); break;
          case 0x40: Serial.print(" - PCA9685 PWM Driver or Si7021"); break;
          case 0x1E: Serial.print(" - HMC5883L Magnetometer"); break;
          case 0x0C: Serial.print(" - AK8963 Magnetometer (in MPU9250)"); break;
          default: Serial.print(" - Unknown device");
        }
        Serial.println();
      }
    }
  }
  
  Serial.println("\n=====================================");
  Serial.println("Scan complete. Rescanning in 5 seconds...\n");
  delay(5000);
}