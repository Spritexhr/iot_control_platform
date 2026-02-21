/*
 * 旋转传感器（模拟型）(Rotation Sensor - Analog)
 *
 * 功能特性（参考温湿度传感器设计 + rotation_sensor_test 数据格式）：
 * - 三引脚：OUT → A0，GND，VCC（Wemos D1 仅 A0 为模拟输入，0~1V）
 * - 符合 iot/sensors/{sensor_id}/data 主题格式
 * - 数据格式：raw(0-1023)、position(0-100%)、angle(0-180°)，与 test 一致
 * - 支持控制命令订阅（采集间隔、状态上报间隔、启用/禁用等）
 * - 定时采集：按 samplingInterval 定期上报
 * - 定期上报状态（心跳）证明传感器在线
 * - 命令含 6 位 check_code，回传时原样返回
 * - NTP 时间同步、自动重连
 */

#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <NTPClient.h>
#include <WiFiUdp.h>
#include <ArduinoJson.h>

// ============ 传感器配置 ============
const int sensorPin = A0;  // 模拟输入 OUT → A0，三引脚：OUT / GND / VCC

// 传感器标识（请为每个设备设置唯一ID）
const char* SENSOR_ID = "Rotation-001";

// ============ WiFi配置 ============
// 部署前请修改为您的网络
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// ============ MQTT配置 ============
const char* MQTT_SERVER = "YOUR_MQTT_BROKER_IP";  // 部署前请修改
const int MQTT_PORT = 1883;
const char* MQTT_USERNAME = "";
const char* MQTT_PASSWORD = "";

// MQTT主题（符合 Model 设计）
String MQTT_TOPIC_DATA;
String MQTT_TOPIC_CONTROL;
String MQTT_TOPIC_STATUS;

// ============ NTP配置 ============
const char* NTP_SERVER = "ntp.aliyun.com";
const long UTC_OFFSET = 0;
WiFiUDP ntpUDP;
NTPClient timeClient(ntpUDP, NTP_SERVER, UTC_OFFSET, 60000);

// ============ 全局对象 ============
WiFiClient espClient;
PubSubClient mqttClient(espClient);

// ============ 采集相关 ============
int sensorValue = 0;      // 原始值 0-1023
int positionPercent = 0;  // 旋转位置 0-100%
int angle = 0;           // 角度 0-180°

// ============ 运行参数 ============
float samplingInterval = 1.0f;     // 数据采集间隔（秒），默认 1s，最短 0.1s
int statusReportInterval = 120;    // 状态上报间隔（秒），用于证明在线，默认 120 秒
bool isEnabled = true;
unsigned long lastSampleTime = 0;
unsigned long lastStatusReportTime = 0;

// ============ 初始化函数 ============

void setupSerial() {
  Serial.begin(115200);
  delay(1000);
  Serial.println(F("\n========================================"));
  Serial.println(F("  旋转传感器"));
  Serial.println(F("========================================"));
  Serial.print(F("传感器ID: "));
  Serial.println(SENSOR_ID);
  Serial.println();
}

void setupWiFi() {
  Serial.print(F("连接WiFi: "));
  Serial.println(WIFI_SSID);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println(F("✓ WiFi连接成功"));
    Serial.print(F("IP地址: "));
    Serial.println(WiFi.localIP());
  } else {
    Serial.println(F("✗ WiFi连接失败"));
  }
}

void setupMQTT() {
  MQTT_TOPIC_DATA = "iot/sensors/" + String(SENSOR_ID) + "/data";
  MQTT_TOPIC_CONTROL = "iot/sensors/" + String(SENSOR_ID) + "/control";
  MQTT_TOPIC_STATUS = "iot/sensors/" + String(SENSOR_ID) + "/status";

  mqttClient.setServer(MQTT_SERVER, MQTT_PORT);
  mqttClient.setCallback(mqttCallback);
  mqttClient.setBufferSize(512);

  Serial.println(F("✓ MQTT配置完成"));
  Serial.print(F("数据主题: "));
  Serial.println(MQTT_TOPIC_DATA);
  Serial.print(F("控制主题: "));
  Serial.println(MQTT_TOPIC_CONTROL);
}

void setupNTP() {
  timeClient.begin();
  timeClient.update();
  Serial.println(F("✓ NTP时间同步完成"));
  Serial.print(F("当前时间: "));
  Serial.println(timeClient.getFormattedTime());
}

void setupSensor() {
  Serial.println(F("✓ 旋转传感器（模拟型）初始化完成 (OUT=A0, GND, VCC)"));
}

void setup() {
  setupSerial();
  setupSensor();
  delay(500);

  setupWiFi();
  setupMQTT();
  setupNTP();

  Serial.println(F("========================================"));
  Serial.println(F("系统启动完成，开始数据采集..."));
  Serial.println(F("========================================\n"));
}

// ============ 前向声明 ============
void sendStatusUpdate(const char* event, const char* checkCode = nullptr);

// ============ MQTT 处理函数 ============

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  Serial.print(F("收到控制命令 ["));
  Serial.print(topic);
  Serial.print(F("]: "));

  StaticJsonDocument<256> doc;
  DeserializationError error = deserializeJson(doc, payload, length);

  if (error) {
    Serial.println(F("✗ JSON解析失败"));
    return;
  }

  serializeJson(doc, Serial);
  Serial.println();

  const char* checkCode = doc["check_code"].as<const char*>();
  if (checkCode == nullptr) checkCode = "";

  const char* command = doc["command"];

  if (strcmp(command, "set_interval") == 0 || strcmp(command, "set_data_interval") == 0) {
    float newInterval = doc["interval"].as<float>();
    if (newInterval >= 0.1f && newInterval <= 3600.0f) {
      samplingInterval = newInterval;
      Serial.print(F("✓ 采集间隔已更新为: "));
      Serial.print(samplingInterval);
      Serial.println(F(" 秒"));
      sendStatusUpdate("interval_updated", checkCode);
    } else {
      Serial.print(F("✗ 采集间隔无效，需 0.1–3600 秒，收到: "));
      Serial.println(newInterval);
    }
  }
  else if (strcmp(command, "set_status_interval") == 0) {
    int newInterval = doc["interval"].as<int>();
    if (newInterval >= 10 && newInterval <= 600) {
      statusReportInterval = newInterval;
      lastStatusReportTime = millis();
      Serial.print(F("✓ 状态上报间隔已更新为: "));
      Serial.print(statusReportInterval);
      Serial.println(F(" 秒"));
      sendStatusUpdate("status_interval_updated", checkCode);
    } else {
      Serial.print(F("✗ 间隔无效，需 10–600 秒，收到: "));
      Serial.println(newInterval);
    }
  }
  else if (strcmp(command, "enable") == 0) {
    isEnabled = true;
    Serial.println(F("✓ 传感器已启用"));
    sendStatusUpdate("sensor_enabled", checkCode);
  }
  else if (strcmp(command, "disable") == 0) {
    isEnabled = false;
    Serial.println(F("✓ 传感器已禁用"));
    sendStatusUpdate("sensor_disabled", checkCode);
  }
}

void mqttReconnect() {
  while (!mqttClient.connected() && WiFi.status() == WL_CONNECTED) {
    Serial.print(F("连接MQTT服务器..."));

    String clientId = "WemosD1-" + String(SENSOR_ID);
    bool connected;
    if (strlen(MQTT_USERNAME) > 0) {
      connected = mqttClient.connect(clientId.c_str(), MQTT_USERNAME, MQTT_PASSWORD);
    } else {
      connected = mqttClient.connect(clientId.c_str());
    }

    if (connected) {
      Serial.println(F("✓ MQTT连接成功"));
      mqttClient.subscribe(MQTT_TOPIC_CONTROL.c_str());
      Serial.print(F("✓ 已订阅: "));
      Serial.println(MQTT_TOPIC_CONTROL);
      sendStatusUpdate("online");
    } else {
      Serial.print(F("✗ 连接失败, rc="));
      Serial.println(mqttClient.state());
      Serial.println(F("5秒后重试..."));
      delay(5000);
    }
  }
}

// ============ 采集与数据上报（格式参考 rotation_sensor_test）============

void readSensorData() {
  sensorValue = analogRead(sensorPin);
  positionPercent = map(sensorValue, 0, 1023, 0, 100);
  angle = map(sensorValue, 0, 1023, 0, 180);
}

void sendSensorData() {
  timeClient.update();
  readSensorData();

  StaticJsonDocument<256> doc;
  doc["sensor_id"] = SENSOR_ID;

  JsonObject data = doc.createNestedObject("data");
  data["raw"] = sensorValue;           // 原始值 0-1023
  data["position"] = positionPercent;  // 旋转位置 0-100%
  data["angle"] = angle;               // 角度 0-180°

  doc["timestamp"] = timeClient.getEpochTime();

  String jsonString;
  serializeJson(doc, jsonString);

  if (mqttClient.publish(MQTT_TOPIC_DATA.c_str(), jsonString.c_str())) {
    Serial.println(F("✓ 数据发送成功"));
    Serial.print(F("raw: "));
    Serial.print(sensorValue);
    Serial.print(F(" | position: "));
    Serial.print(positionPercent);
    Serial.print(F("% | angle: "));
    Serial.print(angle);
    Serial.println(F("°"));
    Serial.print(F("发送内容: "));
    Serial.println(jsonString);
  } else {
    Serial.println(F("✗ 数据发送失败"));
  }
}

void sendStatusUpdate(const char* event, const char* checkCode) {
  StaticJsonDocument<384> doc;

  doc["sensor_id"] = SENSOR_ID;
  doc["event"] = event;
  doc["timestamp"] = timeClient.getEpochTime();

  JsonObject status = doc.createNestedObject("status");
  status["is_enabled"] = isEnabled;
  status["samplingInterval"] = samplingInterval;
  status["statusReportInterval"] = statusReportInterval;
  status["raw"] = sensorValue;
  status["position"] = positionPercent;
  status["angle"] = angle;

  if (checkCode != nullptr && checkCode[0] != '\0') {
    doc["check_code"] = checkCode;
  }

  String jsonString;
  serializeJson(doc, jsonString);

  if (mqttClient.publish(MQTT_TOPIC_STATUS.c_str(), jsonString.c_str())) {
    Serial.print(F("✓ 状态更新成功: "));
    Serial.print(event);
    if (checkCode != nullptr && checkCode[0] != '\0') {
      Serial.print(F(" check_code="));
      Serial.print(checkCode);
    }
    Serial.println();
  } else {
    Serial.println(F("✗ MQTT 发布失败"));
  }
}

// ============ 主循环 ============

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println(F("⚠ WiFi断开，尝试重连..."));
    setupWiFi();
    delay(1000);
    return;
  }

  if (!mqttClient.connected()) {
    mqttReconnect();
  }
  mqttClient.loop();

  // 定期上报状态（心跳），需先读取最新数据
  readSensorData();

  // 定期上报状态（心跳）
  if (millis() - lastStatusReportTime >= statusReportInterval * 1000UL) {
    sendStatusUpdate("heartbeat");
    lastStatusReportTime = millis();
  }

  // 定时采集并上报数据（与温湿度传感器逻辑一致）
  if (isEnabled && (millis() - lastSampleTime >= (unsigned long)(samplingInterval * 1000.0f))) {
    sendSensorData();
    lastSampleTime = millis();
  }

  delay(100);  // 避免 CPU 满载，与温湿度传感器一致
}
