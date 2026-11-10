#include <Arduino.h>

#include <WiFi.h>
#include <WiFiUdp.h>

/*
ESP32 UDP-client, der forbinder til et Access Point og modtager analoge sensor
værdier via UDP.
Author: Simon Bøgh
Year: 2025
*/

// WiFi Access Point credentials to connect to
const char* ssid = "ADEM_ESP32_Sean";
const char* password = "12345678";

// UDP instance for communication
WiFiUDP udp;
const int udpPort = 4210;

// Buffer for incoming UDP packets
char incomingPacket[255];

void setup() {
  // Initialize serial communication
  Serial.begin(115200);
  
  // Connect to WiFi Access Point
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnected to Wi-Fi");
  
  // Start UDP listener on specified port
  udp.begin(udpPort);
}

void loop() {
  // Check if UDP packet is available
  int packetSize = udp.parsePacket();
  if (packetSize) {
    // Read incoming packet into buffer
    int len = udp.read(incomingPacket, 255);
    if (len > 0) {
      // Null-terminate the string and print received data
      incomingPacket[len] = 0;
      Serial.println("Received: " + String(incomingPacket));
    }
  }
}