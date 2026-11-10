#include <Arduino.h>

#include <WiFi.h>
#include <WiFiUdp.h>

/*
ESP32 UDP-server, der fungerer som et Access Point og sender analoge sensorværdier til en klient via UDP.
Author: Simon Bøgh
Year: 2025
*/

// WiFi Access Point credentials
const char* ssid = "ADEM_ESP32_Sean";
const char* password = "12345678";

// UDP instance for communication
WiFiUDP udp;
const int udpPort = 4210;

// You can either set a specific client IP here, or enable broadcast below.
// If your laptop is the client and gets 192.168.4.3, either change clientIP
// to that address, or enable useBroadcast=true so packets go to 192.168.4.255.
IPAddress clientIP(192, 168, 4, 2); // fallback explicit client IP (editable)
const bool useBroadcast = true;      // set to true to send to 192.168.4.255
IPAddress broadcastIP(192, 168, 4, 255);

// Analog sensor pin
const int sensorPin = 4;

void setup() {
  // Initialize serial communication
  Serial.begin(115200);
  
  // Start WiFi Access Point
  WiFi.softAP(ssid, password);
  delay(1000);
  Serial.println("Access Point started");
  // Print AP IP and chosen target
  IPAddress ap = WiFi.softAPIP();
  Serial.print("AP IP: "); Serial.println(ap);
  if (useBroadcast) {
    Serial.print("Sending UDP to broadcast: "); Serial.print(broadcastIP); Serial.print(":"); Serial.println(udpPort);
  } else {
    Serial.print("Sending UDP to client: "); Serial.print(clientIP); Serial.print(":"); Serial.println(udpPort);
  }
  
  // Start UDP listener on specified port
  udp.begin(udpPort);
}

void loop() {
  // Read analog sensor value
  float sensorValue = analogReadMilliVolts(sensorPin) / 1000.0f;
  
  // Convert sensor value to string
  String message = String(sensorValue, 3);
  
  // Send UDP packet to client
  if (useBroadcast) {
    udp.beginPacket(broadcastIP, udpPort);
  } else {
    udp.beginPacket(clientIP, udpPort);
  }
  udp.print(message);
  udp.endPacket();
  
  // Log the sent value
  Serial.println("Sent: " + message);
  
  // Wait 100ms before next transmission
  delay(100);
}