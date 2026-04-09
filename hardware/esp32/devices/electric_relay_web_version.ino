/*
 * ESP32 继电器控制 - 物联网执行器设备 (Electric Relay Web Version)
 *
 * 功能特性：
 * - 符合 iot/devices/{device_id}/control 控制主题格式
 * - 符合 iot/devices/{device_id}/status 状态上报格式
 * - 支持 turn_on, turn_off, toggle 继电器控制命令
 * - 支持 current_status 查询当前状态 (ON/OFF)
 * - 支持 set_status_interval 设置状态上报间隔（心跳）
 * - 定期上报状态（心跳）证明设备在线
 * - 命令含 6 位 check_code，回传时原样返回以确认命令正确执行
 * - NTP 时间同步，提供准确的时间戳
 * - 自动重连机制
 *
 * 接线：继电器信号线 → GPIO 18 (可调)，VCC → 5V/3.3V，GND → GND
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <NTPClient.h>
#include <WiFiUdp.h>
#include <ArduinoJson.h>

// ============ 继电器配置 ============
#define RELAY_PIN 18         // 继电器信号线接 GPIO 18
#define RELAY_ACTIVE_LOW 1   // 1 表示低电平触发，0 表示高电平触发

// 设备标识（请为每个设备设置唯一ID，需与 Django Admin 中创建的设备一致）
const char* DEVICE_ID = "relay_001";

// ============ WiFi配置（部署前请修改为您的网络） ============
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// ============ MQTT配置（部署前请修改为您的 EMQX 地址） ============
const char* MQTT_SERVER = "YOUR_MQTT_BROKER_IP";
const int MQTT_PORT = 1883;
const char* MQTT_USERNAME = "";
const char* MQTT_PASSWORD = "";

// MQTT主题（符合 devices 应用设计）
String MQTT_TOPIC_CONTROL;
String MQTT_TOPIC_STATUS;

// ============ NTP配置 ============
const char* NTP_SERVER = "ntp.aliyun.com";
const long UTC_OFFSET = 0;  // UTC+0 (或根据需要修改为 8 * 3600 北京时间)
WiFiUDP ntpUDP;
NTPClient timeClient(ntpUDP, NTP_SERVER, UTC_OFFSET, 60000);

// ============ 全局对象 ============
WiFiClient espClient;
PubSubClient mqttClient(espClient);

// ============ 运行参数 ============
bool currentRelayState = false;      // false = OFF, true = ON
int statusReportInterval = 120;      // 状态上报间隔（秒），默认 120 秒
unsigned long lastStatusReportTime = 0;

// ============ 辅助函数 ============

void setRelay(bool state) {
  currentRelayState = state;
  if (RELAY_ACTIVE_LOW) {
    digitalWrite(RELAY_PIN, state ? LOW : HIGH);
  } else {
    digitalWrite(RELAY_PIN, state ? HIGH : LOW);
  }
}

// ============ 初始化函数 ============

void setupSerial() {
  Serial.begin(115200);
  delay(1000);
  Serial.println(F("\n========================================"));
  Serial.println(F("  ESP32 继电器控制 - 执行器设备"));
  Serial.println(F("========================================"));
  Serial.print(F("设备ID: "));
  Serial.println(DEVICE_ID);
  Serial.print(F("继电器引脚: GPIO "));
  Serial.println(RELAY_PIN);
}

void setupRelay() {
  pinMode(RELAY_PIN, OUTPUT);
  setRelay(false);  // 初始关闭
  Serial.println(F("✓ 继电器已初始化，初始状态：OFF"));
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
  MQTT_TOPIC_CONTROL = "iot/devices/" + String(DEVICE_ID) + "/control";
  MQTT_TOPIC_STATUS = "iot/devices/" + String(DEVICE_ID) + "/status";

  mqttClient.setServer(MQTT_SERVER, MQTT_PORT);
  mqttClient.setCallback(mqttCallback);
  mqttClient.setBufferSize(512);

  Serial.println(F("✓ MQTT配置完成"));
  Serial.print(F("控制主题: "));
  Serial.println(MQTT_TOPIC_CONTROL);
  Serial.print(F("状态主题: "));
  Serial.println(MQTT_TOPIC_STATUS);
}

void setupNTP() {
  timeClient.begin();
  timeClient.update();
  Serial.println(F("✓ NTP时间同步完成"));
}

// ============ 前向声明 ============
void sendStatusUpdate(const char* event, const char* checkCode = nullptr);

// ============ MQTT 控制命令处理 ============

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

  const char* command = doc["command"];
  if (!command) {
    Serial.println(F("✗ 缺少 command 字段"));
    return;
  }

  const char* checkCode = doc["check_code"].as<const char*>();
  if (checkCode == nullptr) checkCode = "";

  if (strcmp(command, "turn_on") == 0) {
    setRelay(true);
    Serial.println(F("✓ 继电器已开启 (ON)"));
    sendStatusUpdate("relay_on", checkCode);
  }
  else if (strcmp(command, "turn_off") == 0) {
    setRelay(false);
    Serial.println(F("✓ 继电器已关闭 (OFF)"));
    sendStatusUpdate("relay_off", checkCode);
  }
  else if (strcmp(command, "toggle") == 0) {
    setRelay(!currentRelayState);
    Serial.print(F("✓ 继电器已切换为: "));
    Serial.println(currentRelayState ? "ON" : "OFF");
    sendStatusUpdate("relay_toggled", checkCode);
  }
  else if (strcmp(command, "current_status") == 0) {
    Serial.println(F("✓ 响应 current_status 查询"));
    sendStatusUpdate("check_current_status", checkCode);
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
      Serial.print(F("✗ 间隔无效，需 10-600 秒，收到: "));
      Serial.println(newInterval);
    }
  }
  else {
    Serial.print(F("⚠ 未知命令: "));
    Serial.println(command);
  }
}

void mqttReconnect() {
  while (!mqttClient.connected() && WiFi.status() == WL_CONNECTED) {
    Serial.print(F("连接MQTT服务器..."));

    String clientId = "ESP32-" + String(DEVICE_ID);

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
      lastStatusReportTime = millis();
    } else {
      Serial.print(F("✗ 连接失败, rc="));
      Serial.println(mqttClient.state());
      Serial.println(F("5秒后重试..."));
      delay(5000);
    }
  }
}

// ============ 状态上报 ============

void sendStatusUpdate(const char* event, const char* checkCode) {
  timeClient.update();

  StaticJsonDocument<384> doc;

  doc["device_id"] = DEVICE_ID;
  doc["event"] = event;
  doc["timestamp"] = timeClient.getEpochTime();

  JsonObject status = doc.createNestedObject("status");
  status["state"] = currentRelayState ? "ON" : "OFF";
  status["statusReportInterval"] = statusReportInterval;

  if (checkCode != nullptr && checkCode[0] != '\0') {
    doc["check_code"] = checkCode;
  }

  String jsonString;
  serializeJson(doc, jsonString);

  if (mqttClient.publish(MQTT_TOPIC_STATUS.c_str(), jsonString.c_str())) {
    Serial.print(F("✓ 状态上报: event="));
    Serial.print(event);
    Serial.print(F(" state="));
    Serial.print(currentRelayState ? "ON" : "OFF");
    if (checkCode != nullptr && checkCode[0] != '\0') {
      Serial.print(F(" check_code="));
      Serial.print(checkCode);
    }
    Serial.println();
  } else {
    Serial.println(F("✗ 状态上报失败"));
  }
}

void setup() {
  setupSerial();
  setupRelay();
  setupWiFi();
  setupMQTT();
  setupNTP();

  Serial.println(F("========================================"));
  Serial.println(F("系统启动完成，等待控制命令..."));
  Serial.println(F("========================================\n"));
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

  delay(100);
}
