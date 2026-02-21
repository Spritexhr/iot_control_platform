/*
 * SG90 舵机控制 - 执行器设备
 *
 * 参考 pin_control 结构设计
 *
 * 功能特性：
 * - 符合 iot/devices/{device_id}/control 控制主题格式
 * - 符合 iot/devices/{device_id}/status 状态上报格式
 * - 支持 set_angle(0-180°) 角度控制命令
 * - 支持 current_status 查询当前角度
 * - 支持 set_status_interval 设置状态上报间隔（心跳）
 * - 定期上报状态（心跳）证明设备在线
 * - 命令含 6 位 check_code，回传时原样返回以确认命令正确执行
 * - NTP 时间同步，提供准确的时间戳
 * - 自动重连机制
 *
 * 接线：舵机信号线 → D4，VCC → 5V/3.3V，GND → GND
 */

#include <Servo.h>
#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <NTPClient.h>
#include <WiFiUdp.h>
#include <ArduinoJson.h>

// ============ 舵机配置 ============
#define SERVO_PIN D5   // 舵机信号线接 D5 

// 设备标识（请为每个设备设置唯一ID，需与 Django Admin 中创建的设备一致）
const char* DEVICE_ID = "sg90_001";

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
const long UTC_OFFSET = 0;
WiFiUDP ntpUDP;
NTPClient timeClient(ntpUDP, NTP_SERVER, UTC_OFFSET, 60000);

// ============ 全局对象 ============
WiFiClient espClient;
PubSubClient mqttClient(espClient);
Servo myServo;

// ============ 运行参数 ============
int currentAngle = 90;              // 当前舵机角度 0-180，默认 90°
int statusReportInterval = 120;      // 状态上报间隔（秒），默认 120 秒
unsigned long lastStatusReportTime = 0;

// ============ 初始化函数 ============

void setupSerial() {
  Serial.begin(115200);
  delay(1000);
  Serial.println(F("\n========================================"));
  Serial.println(F("  SG90 舵机控制 - 执行器设备"));
  Serial.println(F("========================================"));
  Serial.print(F("设备ID: "));
  Serial.println(DEVICE_ID);
  Serial.print(F("舵机引脚: D4 (GPIO2)"));
  Serial.println();
}

void setupServo() {
  myServo.attach(SERVO_PIN);
  myServo.write(currentAngle);  // 初始角度 90°
  Serial.println(F("✓ SG90 舵机已初始化，初始角度 90°"));
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
  setupServo();
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

  const char* checkCode = doc["check_code"].as<const char*>();
  if (checkCode == nullptr) checkCode = "";

  if (strcmp(command, "set_angle") == 0) {
    int angle = doc["angle"].as<int>();
    if (angle >= 0 && angle <= 180) {
      currentAngle = angle;
      myServo.write(currentAngle);
      Serial.print(F("✓ 舵机角度已设为: "));
      Serial.print(currentAngle);
      Serial.println(F("°"));
      sendStatusUpdate("angle_updated", checkCode);
    } else {
      Serial.print(F("✗ 角度无效，需 0-180，收到: "));
      Serial.println(angle);
    }
  }
  else if (strcmp(command, "current_status") == 0) {
    Serial.println(F("✓ 响应 current_status 查询"));
    sendStatusUpdate("check_current_angle", checkCode);
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
  status["angle"] = currentAngle;
  status["statusReportInterval"] = statusReportInterval;

  if (checkCode != nullptr && checkCode[0] != '\0') {
    doc["check_code"] = checkCode;
  }

  String jsonString;
  serializeJson(doc, jsonString);

  if (mqttClient.publish(MQTT_TOPIC_STATUS.c_str(), jsonString.c_str())) {
    Serial.print(F("✓ 状态上报: event="));
    Serial.print(event);
    Serial.print(F(" angle="));
    Serial.print(currentAngle);
    Serial.print(F("°"));
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
