/*
 * H2010 光电开关
 *
 * 功能特性：
 * - 仅三引脚：OUT（信号）、GND、VCC
 * - 符合 iot/sensors/{sensor_id}/data 主题格式
 * - 支持控制命令订阅（状态上报间隔、启用/禁用等）
 * - 计数器增加时上报数据，无定时采集
 * - 定期上报状态（心跳）证明传感器在线
 * - 命令含 6 位 check_code，回传时原样返回以确认命令正确执行
 * - NTP 时间同步，提供准确的时间戳
 * - 自动重连机制
 * - 对 OUT 引脚脉冲进行计数（上升沿计数）
 */

 #include <ESP8266WiFi.h>
 #include <PubSubClient.h>
 #include <NTPClient.h>
 #include <WiFiUdp.h>
 #include <ArduinoJson.h>
 
 // ============ 传感器配置 ============
 #define OUT_PIN D5   // 信号引脚 OUT 接 GPIO14 (D5)，仅三引脚：OUT / GND / VCC
 
 // 传感器标识（请为每个设备设置唯一ID）
 const char* SENSOR_ID = "Switch-H2010-001";
 
 // ============ WiFi配置 ============
 const char* WIFI_SSID = "YOUR_WIFI_SSID";      // 部署前请修改
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
 
 // ============ 计数相关 ============
 volatile unsigned long pulseCount = 0;   // 用于触发上报
 bool lastOutState = false;               // 用于边沿检测
 bool switchState = false;                // 检测到脉冲则翻转 true<->false
 
 // ============ 运行参数 ============
 int statusReportInterval = 120;
 bool isEnabled = true;
 unsigned long lastStatusReportTime = 0;
 
 // ============ 初始化函数 ============
 
 void setupSerial() {
   Serial.begin(115200);
   delay(1000);
   Serial.println(F("\n========================================"));
   Serial.println(F("  H2010 光电开关"));
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
   pinMode(OUT_PIN, INPUT);
   lastOutState = (digitalRead(OUT_PIN) == HIGH);
   pulseCount = 0;
   Serial.println(F("✓ H2010光电开关初始化完成 (OUT=D5, GND, VCC)"));
 }
 
 void setup() {
   setupSerial();
   setupSensor();
   delay(500);
 
   setupWiFi();
   setupMQTT();
   setupNTP();
 
   Serial.println(F("========================================"));
   Serial.println(F("系统启动完成，开始计数..."));
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
 
   if (strcmp(command, "set_status_interval") == 0) {
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
 
 // ============ 计数与数据上报 ============
 
 void pollPulseCount() {
   bool currentState = (digitalRead(OUT_PIN) == HIGH);
   if (currentState && !lastOutState) {
     pulseCount++;
     switchState = !switchState;
   }
   lastOutState = currentState;
 }
 
 void sendSensorData() {
   timeClient.update();
 
   StaticJsonDocument<256> doc;
   doc["sensor_id"] = SENSOR_ID;
 
   JsonObject data = doc.createNestedObject("data");
   data["switch"] = switchState;
 
   doc["timestamp"] = timeClient.getEpochTime();
 
   String jsonString;
   serializeJson(doc, jsonString);
 
   if (mqttClient.publish(MQTT_TOPIC_DATA.c_str(), jsonString.c_str())) {
     Serial.println(F("✓ 数据发送成功"));
     Serial.print(F("switch: "));
     Serial.println(switchState ? "true" : "false");
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
   status["statusReportInterval"] = statusReportInterval;
   status["switch"] = switchState;
 
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
 
   // 持续对 OUT 引脚轮询计数（上升沿）
   pollPulseCount();
 
   if (millis() - lastStatusReportTime >= statusReportInterval * 1000UL) {
     sendStatusUpdate("heartbeat");
     lastStatusReportTime = millis();
   }
 
   // 检测到脉冲时上报数据
   if (isEnabled && pulseCount > 0) {
     sendSensorData();
     pulseCount = 0;
   }
 
   delay(10);
 }
 