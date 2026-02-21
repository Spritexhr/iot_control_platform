/*
 * DHT11 温湿度传感器 - 简化版
 * 
 * 功能特性：
 * - 符合 iot/sensors/{sensor_id}/data 主题格式
 * - 支持控制命令订阅（采集间隔调整、启用/禁用等）
 * - NTP 时间同步，提供准确的时间戳
 * - 自动重连机制
 */

#include <DHT.h>
#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <NTPClient.h>
#include <WiFiUdp.h>
#include <ArduinoJson.h>

// ============ 传感器配置 ============
#define DHTPIN D5              // 数据引脚 (GPIO14)
#define DHTTYPE DHT11          // 传感器类型

// 传感器标识（请为每个设备设置唯一ID）
const char* SENSOR_ID = "DHT11-WEMOS-001";

// ============ WiFi配置 ============
const char* WIFI_SSID = "YOUR_WIFI_SSID";      // 部署前请修改
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// ============ MQTT配置（部署前请修改） ============
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
const long UTC_OFFSET = 28800;  // UTC+8 (中国时区，单位：秒)
WiFiUDP ntpUDP;
NTPClient timeClient(ntpUDP, NTP_SERVER, UTC_OFFSET, 60000);

// ============ 全局对象 ============
WiFiClient espClient;
PubSubClient mqttClient(espClient);
DHT dht(DHTPIN, DHTTYPE);

// ============ 运行参数 ============
int samplingInterval = 60;     // 采集间隔（秒），默认60秒
bool isEnabled = true;          // 是否启用数据采集
unsigned long lastSampleTime = 0;

// ============ 初始化函数 ============

void setupSerial() {
  Serial.begin(115200);
  delay(1000);
  Serial.println(F("\n========================================"));
  Serial.println(F("  DHT11 温湿度传感器 - 简化版"));
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
  // 初始化MQTT主题
  MQTT_TOPIC_DATA = "iot/sensors/" + String(SENSOR_ID) + "/data";
  MQTT_TOPIC_CONTROL = "iot/sensors/" + String(SENSOR_ID) + "/control";
  MQTT_TOPIC_STATUS = "iot/sensors/" + String(SENSOR_ID) + "/status";
  
  mqttClient.setServer(MQTT_SERVER, MQTT_PORT);
  mqttClient.setCallback(mqttCallback);
  mqttClient.setBufferSize(512);  // 增加缓冲区大小
  
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
  
  // 初始化DHT传感器
  dht.begin();
  Serial.println(F("✓ DHT传感器初始化完成"));
  delay(2000);  // 等待传感器稳定
  
  setupWiFi();
  setupMQTT();
  setupNTP();
  
  Serial.println(F("========================================"));
  Serial.println(F("系统启动完成，开始数据采集..."));
  Serial.println(F("========================================\n"));
}

// ============ MQTT处理函数 ============

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  Serial.print(F("收到控制命令 ["));
  Serial.print(topic);
  Serial.print(F("]: "));
  
  // 解析JSON命令
  StaticJsonDocument<256> doc;
  DeserializationError error = deserializeJson(doc, payload, length);
  
  if (error) {
    Serial.println(F("✗ JSON解析失败"));
    return;
  }
  
  // 打印收到的命令
  serializeJson(doc, Serial);
  Serial.println();
  
  // 处理不同的控制命令
  const char* command = doc["command"];
  
  if (strcmp(command, "set_interval") == 0) {
    // 设置采集间隔
    int newInterval = doc["interval"];
    if (newInterval >= 10 && newInterval <= 3600) {
      samplingInterval = newInterval;
      Serial.print(F("✓ 采集间隔已更新为: "));
      Serial.print(samplingInterval);
      Serial.println(F(" 秒"));
      sendStatusUpdate("interval_updated");
    }
  } 
  else if (strcmp(command, "enable") == 0) {
    // 启用传感器
    isEnabled = true;
    Serial.println(F("✓ 传感器已启用"));
    sendStatusUpdate("sensor_enabled");
  } 
  else if (strcmp(command, "disable") == 0) {
    // 禁用传感器
    isEnabled = false;
    Serial.println(F("✓ 传感器已禁用"));
    sendStatusUpdate("sensor_disabled");
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
      
      // 订阅控制主题
      mqttClient.subscribe(MQTT_TOPIC_CONTROL.c_str());
      Serial.print(F("✓ 已订阅: "));
      Serial.println(MQTT_TOPIC_CONTROL);
      
      // 发送上线状态
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

bool readSensorData(float &temperature, float &humidity) {
  temperature = dht.readTemperature();
  humidity = dht.readHumidity();
  
  // 检查数据有效性
  if (isnan(temperature) || isnan(humidity)) {
    Serial.println(F("✗ 传感器读取失败"));
    return false;
  }
  
  // 范围检查（DHT11合理范围）
  if (temperature < -20 || temperature > 60 || humidity < 0 || humidity > 100) {
    Serial.println(F("✗ 数据超出合理范围"));
    return false;
  }
  
  return true;
}

void sendSensorData(float temperature, float humidity) {
  // 更新NTP时间
  timeClient.update();
  
  // 构建JSON数据（只包含必需字段）
  StaticJsonDocument<256> doc;
  
  // 传感器ID
  doc["sensor_id"] = SENSOR_ID;
  
  // 数据内容
  JsonObject data = doc.createNestedObject("data");
  data["temperature"] = round(temperature * 10) / 10.0;  // 保留1位小数
  data["humidity"] = round(humidity * 10) / 10.0;
  
  // 时间戳
  doc["timestamp"] = timeClient.getEpochTime();
  
  // 序列化JSON
  String jsonString;
  serializeJson(doc, jsonString);
  
  // 发布到MQTT
  if (mqttClient.publish(MQTT_TOPIC_DATA.c_str(), jsonString.c_str())) {
    Serial.println(F("✓ 数据发送成功"));
    Serial.print(F("温度: "));
    Serial.print(temperature, 1);
    Serial.print(F("°C | 湿度: "));
    Serial.print(humidity, 1);
    Serial.println(F("%"));
    Serial.print(F("发送内容: "));
    Serial.println(jsonString);
  } else {
    Serial.println(F("✗ 数据发送失败"));
  }
}

void sendStatusUpdate(const char* event) {
  // 构建JSON状态（只包含必需字段）
  StaticJsonDocument<256> doc;
  
  doc["sensor_id"] = SENSOR_ID;
  doc["event"] = event;
  doc["timestamp"] = timeClient.getEpochTime();
  doc["is_enabled"] = isEnabled;
  doc["samplingInterval"] = samplingInterval;
  
  String jsonString;
  serializeJson(doc, jsonString);
  
  mqttClient.publish(MQTT_TOPIC_STATUS.c_str(), jsonString.c_str());
  Serial.print(F("✓ 状态更新: "));
  Serial.println(event);
}

// ============ 主循环 ============

void loop() {
  // 检查WiFi连接
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println(F("⚠ WiFi断开，尝试重连..."));
    setupWiFi();
    delay(1000);
    return;
  }
  
  // 检查MQTT连接
  if (!mqttClient.connected()) {
    mqttReconnect();
  }
  mqttClient.loop();
  
  // 数据采集和上报
  if (isEnabled && (millis() - lastSampleTime >= samplingInterval * 1000UL)) {
    float temperature, humidity;
    
    if (readSensorData(temperature, humidity)) {
      sendSensorData(temperature, humidity);
    } else {
      Serial.println(F("⚠ 跳过本次上报（数据无效）"));
    }
    
    lastSampleTime = millis();
  }
  
  // 短暂延迟，避免CPU满载
  delay(100);
}
