#include <WiFi.h>
#include <PubSubClient.h>

// Заполните перед загрузкой в реальную плату.
const char* WIFI_NAME = "YOUR_WIFI_NAME";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* MQTT_SERVER = "192.168.1.100";  // IPv4 компьютера с Docker
const int MQTT_PORT = 1883;

const char* DEVICE_ID = "ESP32-S3-URALS-001";
const char* TOPIC_DATA = "lighting/sensor/data";
const char* TOPIC_STATUS = "lighting/device/status";
const char* TOPIC_LIGHT = "lighting/control/light";
const char* TOPIC_MODE = "lighting/control/mode";

const int RELAY_PIN = 4;
const int LIGHT_SENSOR_PIN = 1;
const bool USE_REAL_SENSORS = false;

WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);

bool lightingOn = true;
String controlMode = "conventional";
unsigned long lastTelemetry = 0;


void applyOutput() {
  digitalWrite(RELAY_PIN, lightingOn ? HIGH : LOW);
}


void onMqttMessage(char* topic, byte* payload, unsigned int length) {
  String value;
  for (unsigned int i = 0; i < length; i++) {
    value += static_cast<char>(payload[i]);
  }

  if (String(topic) == TOPIC_LIGHT) {
    lightingOn = value == "on";
    applyOutput();
  }

  if (String(topic) == TOPIC_MODE &&
      (value == "conventional" || value == "adaptive")) {
    controlMode = value;
  }
}


void connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_NAME, WIFI_PASSWORD);
  Serial.print("Connecting to Wi-Fi");

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.print("Wi-Fi connected. ESP32 IP: ");
  Serial.println(WiFi.localIP());
}


void connectMqtt() {
  while (!mqttClient.connected()) {
    Serial.print("Connecting to MQTT...");

    if (mqttClient.connect(
          DEVICE_ID,
          TOPIC_STATUS,
          1,
          true,
          "offline"
        )) {
      Serial.println("connected");
      mqttClient.subscribe(TOPIC_LIGHT);
      mqttClient.subscribe(TOPIC_MODE);
      mqttClient.publish(TOPIC_STATUS, "online", true);
    } else {
      Serial.print("failed, code=");
      Serial.println(mqttClient.state());
      delay(3000);
    }
  }
}


float readLux() {
  if (USE_REAL_SENSORS) {
    int rawValue = analogRead(LIGHT_SENSOR_PIN);
    return map(rawValue, 0, 4095, 0, 100);
  }
  return random(200, 701) / 10.0;
}


void createMeasurements(
  float lux,
  float& voltage,
  float& current,
  float& power
) {
  voltage = random(2180, 2231) / 10.0;

  if (!lightingOn) {
    current = 0;
  } else if (controlMode == "conventional") {
    current = random(300, 341) / 100.0;
  } else if (lux < 30) {
    current = random(240, 261) / 100.0;
  } else if (lux < 50) {
    current = random(200, 231) / 100.0;
  } else {
    current = random(170, 191) / 100.0;
  }

  power = voltage * current;
}


void publishTelemetry() {
  float lux = readLux();
  float voltage;
  float current;
  float power;
  createMeasurements(lux, voltage, current, power);

  char payload[320];
  snprintf(
    payload,
    sizeof(payload),
    "{\"device_id\":\"%s\",\"voltage\":%.1f,\"current\":%.2f,"
    "\"power\":%.1f,\"lux\":%.1f,\"lighting_on\":%s,"
    "\"control_mode\":\"%s\"}",
    DEVICE_ID,
    voltage,
    current,
    power,
    lux,
    lightingOn ? "true" : "false",
    controlMode.c_str()
  );

  mqttClient.publish(TOPIC_DATA, payload);
  Serial.println(payload);
}


void setup() {
  Serial.begin(115200);
  pinMode(RELAY_PIN, OUTPUT);
  applyOutput();
  randomSeed(micros());

  connectWiFi();
  mqttClient.setServer(MQTT_SERVER, MQTT_PORT);
  mqttClient.setCallback(onMqttMessage);
  mqttClient.setBufferSize(512);
}


void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
  }

  if (!mqttClient.connected()) {
    connectMqtt();
  }

  mqttClient.loop();

  if (millis() - lastTelemetry >= 5000) {
    lastTelemetry = millis();
    publishTelemetry();
  }
}
