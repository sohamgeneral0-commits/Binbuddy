/*
 * BinBuddy IoT Sensor - ESP8266 / ESP32
 * Smart Waste Level Sensor with MQTT + HTTP fallback
 *
 * Hardware:
 *   - ESP8266 (NodeMCU) or ESP32
 *   - HC-SR04 Ultrasonic Sensor
 *   - LED indicators (optional)
 *
 * Wiring:
 *   HC-SR04 TRIG  → D1 (GPIO5)
 *   HC-SR04 ECHO  → D2 (GPIO4)
 *   LED Green     → D5  (empty)
 *   LED Yellow    → D6  (half)
 *   LED Red       → D7  (full)
 *   VCC → 5V, GND → GND
 *
 * Install libraries (Arduino Library Manager):
 *   - PubSubClient (MQTT)
 *   - ArduinoJson
 *   - ESP8266WiFi (for ESP8266) or WiFi (for ESP32)
 */
/*
 * BinBuddy IoT Sensor
 * ESP8266 + HC-SR04 + LCD I2C
 * Sends fill level to your local PC via MQTT
 */

#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// ══════════════════════════════════════════════
//  ⚙️  EDIT THESE 3 LINES ONLY
// ══════════════════════════════════════════════
const char* WIFI_SSID     = "LAPTOP 1321";          // your WiFi name
const char* WIFI_PASSWORD = "123456789";     // your WiFi password
const char* MQTT_BROKER   = "192.168.137.162";  // ← UPDATED to match Flask backend IP

// const char* WIFI_SSID     = "ABCD";          // your WiFi name
// const char* WIFI_PASSWORD = "123456789";     // your WiFi password
// const char* MQTT_BROKER   = "10.216.26.166";  // ← your PC IP from Step 1
// ══════════════════════════════════════════════

// Bin settings — matches your database exactly
const char* BIN_CODE      = "BIN-W01-001";
const float BIN_HEIGHT    = 22.0;  // your bin is 22cm deep
const float BIN_LATITUDE  = 20.0059;   // set real latitude or wire GPS module
const float BIN_LONGITUDE = 73.7667;   // set real longitude or wire GPS module

// Pins — same as your existing wiring
#define TRIG_PIN D7
#define ECHO_PIN D8

// MQTT topic
const char* MQTT_TOPIC = "binbuddy/bins/BIN-W01-001/data";

// LCD — same as your existing setup
LiquidCrystal_I2C lcd(0x27, 16, 2);

// Objects
WiFiClient   wifiClient;
PubSubClient mqtt(wifiClient);

unsigned long lastSend = 0;
const long    INTERVAL = 1000;  // send every 1 seconds

// ══════════════════════════════════════════════
void setup() {
  Serial.begin(9600);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  // LCD startup
  lcd.init();
  lcd.backlight();
  lcd.setCursor(0, 0);
  lcd.print("BinBuddy v2.0");
  lcd.setCursor(0, 1);
  lcd.print("Connecting...");

  // Connect WiFi
  connectWiFi();

  // Setup MQTT
  mqtt.setServer(MQTT_BROKER, 1883);
}

// ══════════════════════════════════════════════
void loop() {
  // Keep MQTT alive
  if (!mqtt.connected()) {
    connectMQTT();
  }
  mqtt.loop();

  // Send data every 3 seconds
  if (millis() - lastSend >= INTERVAL) {
    lastSend = millis();

    // 1. Measure distance
    float distance   = measureDistance();
    
    // 2. Calculate fill percentage (your exact formula)
    float fillPercent = ((BIN_HEIGHT - distance) / BIN_HEIGHT) * 100.0;
    if (fillPercent < 0)   fillPercent = 0;
    if (fillPercent > 100) fillPercent = 100;

    // 3. Send to dashboard via MQTT
    sendMQTT(fillPercent, distance);

    // 4. Update LCD (same as before)
    lcd.setCursor(0, 0);
    lcd.print("Level:");
    lcd.print(fillPercent, 1);
    lcd.print("%   ");
    lcd.setCursor(0, 1);
    lcd.print("Dist:");
    lcd.print(distance, 1);
    lcd.print("cm   ");

    // 5. Serial monitor
    Serial.print("Fill: ");
    Serial.print(fillPercent, 1);
    Serial.print("%  |  Dist: ");
    Serial.print(distance, 1);
    Serial.println("cm");
  }
}

// ══════════════════════════════════════════════
//  MEASURE DISTANCE
// ══════════════════════════════════════════════
float measureDistance() {
  // Take 3 readings and average them for accuracy
  float total = 0;
  int   valid = 0;

  for (int i = 0; i < 3; i++) {
    digitalWrite(TRIG_PIN, LOW);
    delayMicroseconds(2);
    digitalWrite(TRIG_PIN, HIGH);
    delayMicroseconds(10);
    digitalWrite(TRIG_PIN, LOW);

    long duration = pulseIn(ECHO_PIN, HIGH, 25000); // 25ms timeout
    if (duration > 0) {
      total += duration * 0.034 / 2.0;
      valid++;
    }
    delay(30);
  }

  if (valid == 0) return BIN_HEIGHT; // sensor error → treat as empty
  return total / valid;
}

// ══════════════════════════════════════════════
//  SEND DATA VIA MQTT
// ══════════════════════════════════════════════
void sendMQTT(float fillPercent, float distance) {
  // Build JSON payload
  StaticJsonDocument<256> doc;
  doc["bin_code"]    = BIN_CODE;
  doc["fill_level"]  = round(fillPercent * 10) / 10.0;
  doc["distance_cm"] = round(distance * 10) / 10.0;
  doc["battery"]     = 100.0;  // no battery sensor, fixed value
  doc["latitude"]    = BIN_LATITUDE;
  doc["longitude"]   = BIN_LONGITUDE;

  char buffer[256];
  serializeJson(doc, buffer);

  // Publish to MQTT
  bool ok = mqtt.publish(MQTT_TOPIC, buffer);

  if (ok) {
    Serial.print("✅ MQTT sent: ");
    Serial.println(buffer);
  } else {
    Serial.println("❌ MQTT send failed — will retry");
  }
}

// ══════════════════════════════════════════════
//  WIFI CONNECTION
// ══════════════════════════════════════════════
void connectWiFi() {
  Serial.print("Connecting to WiFi: ");
  Serial.println(WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 40) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✅ WiFi Connected!");
    Serial.print("ESP IP: ");
    Serial.println(WiFi.localIP());
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("WiFi OK!");
    lcd.setCursor(0, 1);
    lcd.print(WiFi.localIP());
    delay(2000);
    lcd.clear();
  } else {
    Serial.println("\n❌ WiFi Failed!");
    lcd.clear();
    lcd.print("WiFi FAILED!");
    delay(2000);
  }
}

// ══════════════════════════════════════════════
//  MQTT CONNECTION
// ══════════════════════════════════════════════
void connectMQTT() {
  Serial.print("Connecting to MQTT...");
  lcd.setCursor(0, 1);
  lcd.print("MQTT connecting.");

  // Try up to 5 times
  int tries = 0;
  while (!mqtt.connected() && tries < 5) {
    if (mqtt.connect("BinBuddy-ESP-001")) {
      Serial.println(" ✅ MQTT Connected!");
      lcd.setCursor(0, 1);
      lcd.print("MQTT OK!        ");
      delay(1000);
    } else {
      Serial.print(" ❌ failed (rc=");
      Serial.print(mqtt.state());
      Serial.println("). Retry in 2s");
      delay(2000);
      tries++;
    }
  }
}
