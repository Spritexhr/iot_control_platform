/*
 * BMP280 温压传感器
 *
 * 功能特性：
 * - 符合 iot/sensors/{sensor_id}/data 主题格式
 * - 支持控制命令订阅（采集间隔、状态上报间隔、启用/禁用等）
 * - 定期上报状态（心跳）证明传感器在线
 * - 命令含 6 位 check_code，回传时原样返回以确认命令正确执行
 * - NTP 时间同步，提供准确的时间戳
 * - 自动重连机制
 */

#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BMP280.h>
#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <NTPClient.h>
#include <WiFiUdp.h>
#include <ArduinoJson.h>

// ============ 传感器配置 ============
#define BMP280_SDA 4   // D2 = SDA
#define BMP280_SCL 5   // D1 = SCL
#define BMP280_ADDR 0x76

// 传感器标识（请为每个设备设置唯一ID）
const char* SENSOR_ID = "BMP280-WEMOS-001";

// ============ WiFi配置（部署前请修改为您的网络） ============
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// ============ MQTT配置（部署前请修改为您的 EMQX 地址） ============
const char* MQTT_SERVER = "YOUR_MQTT_BROKER_IP";
const int MQTT_PORT = 1883;
const char* MQTT_USERNAME = "";  // 如果需要认证
const char* MQTT_PASSWORD = "";  // 如果需要认证

// MQTT主题（符合Model设计）
String MQTT_TOPIC_DATA;      // iot/sensors/{sensor_id}/data
String MQTT_TOPIC_CONTROL;   // iot/sensors/{sensor_id}/control
String MQTT_TOPIC_STATUS;    // iot/sensors/{sensor_id}/status

// ============ NTP配置 ============
const char* NTP_SERVER = "ntp.aliyun.com";
const long UTC_OFFSET = 0;  // 0 获取标准 UTC 时间戳
WiFiUDP ntpUDP;
NTPClient timeClient(ntpUDP, NTP_SERVER, UTC_OFFSET, 60000);

// ============ 全局对象 ============
WiFiClient espClient;
PubSubClient mqttClient(espClient);
Adafruit_BMP280 bmp;

// ============ 运行参数 ============
int samplingInterval = 60;        // 数据采集间隔（秒），默认60秒
int statusReportInterval = 120;   // 状态上报间隔（秒），用于证明在线，默认120秒
bool isEnabled = true;            // 是否启用数据采集
unsigned long lastSampleTime = 0;
unsigned long lastStatusReportTime = 0;

// ============ 初始化函数 ============

void setupSerial() {
  Serial.begin(115200);
  delay(1000);
  Serial.println(F("\n========================================"));
  Serial.println(F("  BMP280 温压传感器"));
  Serial.println(F("========================================"));
  Serial.print(F("传感器ID: "));
  Serial.println(SENSOR_ID);
  Serial.println();
}

void setupBMP280() {
  Wire.begin(BMP280_SDA, BMP280_SCL);

  if (!bmp.begin(BMP280_ADDR)) {
    Serial.println(F("✗ 初始化 BMP280 失败，请检查连线！"));
    while (1) {
      delay(1000);
    }
  }

  Serial.println(F("✓ BMP280 传感器初始化完成"));
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

void setup() {
  setupSerial();
  setupBMP280();
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

// ============ MQTT处理函数 ============

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
    int newInterval = doc["interval"];
    if (newInterval >= 10 && newInterval <= 3600) {
      samplingInterval = newInterval;
      Serial.print(F("✓ 采集间隔已更新为: "));
      Serial.print(samplingInterval);
      Serial.println(F(" 秒"));
      sendStatusUpdate("interval_updated", checkCode);
    }
  }
  else if (strcmp(command, "set_status_interval") == 0) {
    int newInterval = doc["interval"];
    if (newInterval >= 30 && newInterval <= 600) {
      statusReportInterval = newInterval;
      Serial.print(F("✓ 状态上报间隔已更新为: "));
      Serial.print(statusReportInterval);
      Serial.println(F(" 秒"));
      sendStatusUpdate("status_interval_updated", checkCode);
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

// ============ 数据采集和发送 ============

bool readSensorData(float &temperature, float &pressure) {
  temperature = bmp.readTemperature();
  pressure = bmp.readPressure() / 100.0F;  // 转换为 hPa

  if (isnan(temperature) || isnan(pressure)) {
    Serial.println(F("✗ 传感器读取失败"));
    return false;
  }

  // 范围检查（BMP280 合理范围）
  if (temperature < -40 || temperature > 85 || pressure < 300 || pressure > 1100) {
    Serial.println(F("✗ 数据超出合理范围"));
    return false;
  }

  return true;
}

void sendSensorData(float temperature, float pressure) {
  timeClient.update();

  StaticJsonDocument<256> doc;

  doc["sensor_id"] = SENSOR_ID;

  JsonObject data = doc.createNestedObject("data");
  data["temperature"] = round(temperature * 10) / 10.0;
  data["pressure"] = round(pressure * 10) / 10.0;

  doc["timestamp"] = timeClient.getEpochTime();

  String jsonString;
  serializeJson(doc, jsonString);

  if (mqttClient.publish(MQTT_TOPIC_DATA.c_str(), jsonString.c_str())) {
    Serial.println(F("✓ 数据发送成功"));
    Serial.print(F("温度: "));
    Serial.print(temperature, 1);
    Serial.print(F("°C | 气压: "));
    Serial.print(pressure, 1);
    Serial.println(F(" hPa"));
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

  if (millis() - lastStatusReportTime >= statusReportInterval * 1000UL) {
    sendStatusUpdate("heartbeat");
    lastStatusReportTime = millis();
  }

  if (isEnabled && (millis() - lastSampleTime >= samplingInterval * 1000UL)) {
    float temperature, pressure;

    if (readSensorData(temperature, pressure)) {
      sendSensorData(temperature, pressure);
    } else {
      Serial.println(F("⚠ 跳过本次上报（数据无效）"));
    }

    lastSampleTime = millis();
  }

  delay(100);
}
