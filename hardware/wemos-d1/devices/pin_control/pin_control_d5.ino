/*
 * D5 引脚高低电平控制 - 执行器设备
 * 
 * 参考 temp_humi_sensor_v3.ino 结构设计
 * 
 * 功能特性：
 * - 符合 iot/devices/{device_id}/control 控制主题格式
 * - 符合 iot/devices/{device_id}/status 状态上报格式
 * - 支持 high(高电平) / low(低电平) / current_status 控制命令
 * - 支持 set_status_interval 设置状态上报间隔（心跳）
 * - 定期上报状态（心跳）证明设备在线
 * - 命令含 6 位 check_code，回传时原样返回以确认命令正确执行
 * - NTP 时间同步，提供准确的时间戳
 * - 自动重连机制
 */

#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <NTPClient.h>
#include <WiFiUdp.h>
#include <ArduinoJson.h>

// ============ 引脚配置 ============
#define OUTPUT_PIN D5    // 控制引脚 D5 (GPIO14)

// 设备标识（请为每个设备设置唯一ID，需与 Django Admin 中创建的设备一致）
const char* DEVICE_ID = "potential_controler_001";

// ============ WiFi配置（部署前请修改为您的网络） ============
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// ============ MQTT配置（部署前请修改为您的 EMQX 地址） ============
const char* MQTT_SERVER = "YOUR_MQTT_BROKER_IP";
const int MQTT_PORT = 1883;
const char* MQTT_USERNAME = "";
const char* MQTT_PASSWORD = "";

// MQTT主题（符合 devices 应用设计）
String MQTT_TOPIC_CONTROL;   // iot/devices/{device_id}/control
String MQTT_TOPIC_STATUS;   // iot/devices/{device_id}/status

// ============ NTP配置 ============
const char* NTP_SERVER = "ntp.aliyun.com";
const long UTC_OFFSET = 0;  // UTC 时间戳
WiFiUDP ntpUDP;
NTPClient timeClient(ntpUDP, NTP_SERVER, UTC_OFFSET, 60000);

// ============ 全局对象 ============
WiFiClient espClient;
PubSubClient mqttClient(espClient);

// ============ 运行参数 ============
bool powerState = false;              // 当前输出状态：false=低电平(low), true=高电平(high)
int statusReportInterval = 120;       // 状态上报间隔（秒），用于心跳证明在线，默认120秒
unsigned long lastStatusReportTime = 0;

// ============ 初始化函数 ============

void setupSerial() {
  Serial.begin(115200);
  delay(1000);
  Serial.println(F("\n========================================"));
  Serial.println(F("  D5 引脚高低电平控制 - 执行器设备"));
  Serial.println(F("========================================"));
  Serial.print(F("设备ID: "));
  Serial.println(DEVICE_ID);
  Serial.print(F("控制引脚: D5 (GPIO14)"));
  Serial.println();
}

void setupPin() {
  pinMode(OUTPUT_PIN, OUTPUT);
  digitalWrite(OUTPUT_PIN, LOW);  // 默认输出低电平
  Serial.println(F("✓ 引脚 D5 已配置为输出模式，初始为低电平"));
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

void setup() {
  setupSerial();
  setupPin();
  setupWiFi();
  setupMQTT();
  setupNTP();
  
  Serial.println(F("========================================"));
  Serial.println(F("系统启动完成，等待控制命令..."));
  Serial.println(F("========================================\n"));
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

  // 提取 check_code（6位数字），命令响应时需回传以确认
  const char* checkCode = doc["check_code"].as<const char*>();
  if (checkCode == nullptr) checkCode = "";

  if (strcmp(command, "high") == 0) {
    // 高电平 - 符合 mqtt_command_form: command "high", check_code
    digitalWrite(OUTPUT_PIN, HIGH);
    powerState = true;
    Serial.println(F("✓ 引脚已设为高电平 (high)"));
    sendStatusUpdate("level_updated", checkCode);
  } 
  else if (strcmp(command, "low") == 0) {
    // 低电平 - 符合 mqtt_command_form: command "low", check_code
    digitalWrite(OUTPUT_PIN, LOW);
    powerState = false;
    Serial.println(F("✓ 引脚已设为低电平 (low)"));
    sendStatusUpdate("level_updated", checkCode);
  }
  else if (strcmp(command, "current_status") == 0) {
    // 获取当前状态 - 符合 mqtt_command_form: command "current_status", check_code
    Serial.println(F("✓ 响应 current_status 查询"));
    sendStatusUpdate("check_current_level", checkCode);
  }
  else if (strcmp(command, "set_status_interval") == 0) {
    // 设置状态上报间隔（用于心跳证明在线）
    int newInterval = doc["interval"];
    if (newInterval >= 30 && newInterval <= 600) {
      statusReportInterval = newInterval;
      Serial.print(F("✓ 状态上报间隔已更新为: "));
      Serial.print(statusReportInterval);
      Serial.println(F(" 秒"));
      sendStatusUpdate("status_interval_updated", checkCode);
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
    
    String clientId = "WemosD1-" + String(DEVICE_ID);
    
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
      // 发送上线状态，并重置心跳计时
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
// 符合 mqtt_status_form.txt 格式:
// {"device_id":"xxx","event":"...","status":{"level":"high"|"low","statusReportInterval":n},"check_code":"6位数字","timestamp":xxx}
// 命令响应时需回传 check_code 以确认命令正确执行

void sendStatusUpdate(const char* event, const char* checkCode) {
  timeClient.update();
  
  StaticJsonDocument<384> doc;
  
  doc["device_id"] = DEVICE_ID;
  doc["event"] = event;  // "level_updated" | "check_current_level" | "heartbeat" | "online" | "status_interval_updated"
  doc["timestamp"] = timeClient.getEpochTime();
  
  JsonObject status = doc.createNestedObject("status");
  status["level"] = powerState ? "high" : "low";
  status["statusReportInterval"] = statusReportInterval;

  // 命令响应时回传 check_code
  if (checkCode != nullptr && checkCode[0] != '\0') {
    doc["check_code"] = checkCode;
  }
  
  String jsonString;
  serializeJson(doc, jsonString);
  
  if (mqttClient.publish(MQTT_TOPIC_STATUS.c_str(), jsonString.c_str())) {
    Serial.print(F("✓ 状态上报: event="));
    Serial.print(event);
    Serial.print(F(" level="));
    Serial.print(powerState ? "high" : "low");
    if (checkCode != nullptr && checkCode[0] != '\0') {
      Serial.print(F(" check_code="));
      Serial.print(checkCode);
    }
    Serial.println();
  } else {
    Serial.println(F("✗ 状态上报失败"));
  }
}

// ============ 主循环 ============

void loop() {
  // WiFi 重连
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println(F("⚠ WiFi断开，尝试重连..."));
    setupWiFi();
    delay(1000);
    return;
  }
  
  // MQTT 重连
  if (!mqttClient.connected()) {
    mqttReconnect();
  }
  mqttClient.loop();
  
  // 定期上报状态以证明设备在线（心跳）
  if (millis() - lastStatusReportTime >= statusReportInterval * 1000UL) {
    sendStatusUpdate("heartbeat");
    lastStatusReportTime = millis();
  }
  
  delay(100);
}
