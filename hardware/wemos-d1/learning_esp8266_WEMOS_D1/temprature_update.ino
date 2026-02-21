#include <SoftwareSerial.h>
#include <DHT.h>

#define ESP_RX 8
#define ESP_TX 9
#define DHTPIN 2
#define DHTTYPE DHT11

DHT dht(DHTPIN, DHTTYPE);
SoftwareSerial espSerial(ESP_RX, ESP_TX);

// Connection status variables
bool mqttConnected = false;
bool wifiConnected = false;
String response = "";

// Timing constants
const unsigned long RECONNECT_INTERVAL = 15000;
const unsigned long HEARTBEAT_INTERVAL = 30000;  // Check connection every 30s
const unsigned long JSON_TIMEOUT = 1000;
const unsigned long SETUP_TIMEOUT = 30000;       // Max time for setup

// Timing variables
unsigned long lastConnectAttempt = 0;
unsigned long lastHeartbeat = 0;

// Connection parameters - easier to modify
const char* MQTT_CLIENT_ID = "esp01";
const char* MQTT_USERNAME = "esp01";
const char* MQTT_PASSWORD = "";  // 若 EMQX 需要认证请填写
const char* MQTT_BROKER = "YOUR_MQTT_BROKER_IP";  // 部署前请修改
const int MQTT_PORT = 1883;
const char* MQTT_TOPIC = "LED_TEST";
const char* sensor_name = "th_sensor";
const int sensor_id = 1;

// WiFi credentials (add your own)
// 部署前请修改为您的 WiFi 信息
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

void setup() {
  Serial.begin(9600);
  espSerial.begin(9600);
  dht.begin();

  Serial.println("=== ESP01 MQTT Setup ===");
  
  // Clear any existing data
  espSerial.flush();
  delay(2000);
  
  // Initialize connection with timeout
  unsigned long setupStart = millis();
  while (!mqttConnected && (millis() - setupStart < SETUP_TIMEOUT)) {
    if (initializeConnection()) {
      Serial.println("✓ MQTT connection established!");
      break;
    }
    Serial.println("Setup failed, retrying in 5 seconds...");
    delay(5000);
  }
  
  if (!mqttConnected) {
    Serial.println("✗ Setup timeout - will retry in loop");
  }
  
  Serial.println("=== Setup Complete ===");
}

void loop() {
  processMQTTMessages();
  
  // Heartbeat check
  if (millis() - lastHeartbeat >= HEARTBEAT_INTERVAL) {
    checkConnectionStatus();
    lastHeartbeat = millis();
  }
  
  // Reconnect if needed
  if (!mqttConnected && millis() - lastConnectAttempt >= RECONNECT_INTERVAL) {
    Serial.println("Attempting reconnection...");
    if (initializeConnection()) {
      Serial.println("✓ Reconnection successful!");
    }
    lastConnectAttempt = millis();
  }
  
  delay(10); // Small delay to prevent watchdog issues
}

bool initializeConnection() {
  Serial.println("Initializing ESP01...");
  
  // Step 1: Basic AT test
  if (!sendATCommand("AT", 2000)) {
    Serial.println("✗ ESP01 not responding");
    return false;
  }
  
  // Step 3: Set WiFi mode
  if (!sendATCommand("AT+CWMODE=1", 2000)) {
    Serial.println("✗ Failed to set WiFi mode");
    return false;
  }
  
  // Step 4: Connect to WiFi (if not already connected)
  if (!checkWiFiConnection()) {
    String wifiCmd = "AT+CWJAP=\"" + String(WIFI_SSID) + "\",\"" + String(WIFI_PASSWORD) + "\"";
    if (!sendATCommand(wifiCmd, 15000)) {
      Serial.println("✗ WiFi connection failed");
      return false;
    }
    wifiConnected = true;
    Serial.println("✓ WiFi connected");
  }
  
  // Step 5: Configure MQTT user
  String mqttUserCmd = "AT+MQTTUSERCFG=0,1,\"" + String(MQTT_CLIENT_ID) + 
                       "\",\"" + String(MQTT_USERNAME) + 
                       "\",\"" + String(MQTT_PASSWORD) + "\",0,0,\"\"";
  if (!sendATCommand(mqttUserCmd, 3000)) {
    Serial.println("✗ MQTT user config failed");
    return false;
  }
  
  // Step 6: Connect to MQTT broker
  String mqttConnCmd = "AT+MQTTCONN=0,\"" + String(MQTT_BROKER) + 
                       "\"," + String(MQTT_PORT) + ",1";
  if (!sendATCommand(mqttConnCmd, 10000)) {
    Serial.println("✗ MQTT connection failed");
    return false;
  }
  
  // Step 7: Subscribe to topic
  String subCmd = "AT+MQTTSUB=0,\"" + String(MQTT_TOPIC) + "\",0";
  if (!sendATCommand(subCmd, 3000)) {
    Serial.println("✗ MQTT subscription failed");
    return false;
  }
  
  mqttConnected = true;
  Serial.println("✓ MQTT fully initialized");
  return true;
}

// 上传温度和湿度到MQTT
void processMQTTMessages() {
  float h = dht.readHumidity();
  float t = dht.readTemperature();
  
  if (isnan(h) || isnan(t)) {
    Serial.println("Failed to read from DHT sensor!");
    return;
  }
  
  Serial.print("Humidity: ");
  Serial.print(h);
  Serial.print(" %\t");
  Serial.print("Temperature: ");
  Serial.print(t);
  Serial.println(" *C");
  
  // 构建简洁的JSON消息（限制小数位数以减少长度）
  // 格式: {"sensor_name":"th_sensor","sensor_id":1,"data":{"temp":25.5,"humi":60.0}}
  String message = "{\"sensor_name\":\"" + String(sensor_name) + 
                   "\",\"sensor_id\":" + String(sensor_id) + 
                   ",\"data\":{\"temp\":" + String(t, 1) + ",\"humi\":" + String(h, 1) + "}}";
  
  // 打印调试信息
  Serial.print("Sending message: ");
  Serial.println(message);
  
  // 计算消息长度
  int msgLen = message.length();
  Serial.print("Message length: ");
  Serial.println(msgLen);
  
  // 使用AT+MQTTPUBRAW命令发送（更适合较长消息）
  String mqttCommand = "AT+MQTTPUBRAW=0,\"temperature\"," + String(msgLen) + ",0,0";
  
  // 发送MQTTPUBRAW命令
  espSerial.println(mqttCommand);
  Serial.print(">> ");
  Serial.println(mqttCommand);
  
  // 等待">"提示符
  unsigned long startTime = millis();
  bool gotPrompt = false;
  while (millis() - startTime < 3000) {
    if (espSerial.available()) {
      char c = espSerial.read();
      Serial.print(c);
      if (c == '>') {
        gotPrompt = true;
        break;
      }
    }
  }
  
  if (gotPrompt) {
    // 发送实际的JSON数据
    espSerial.print(message);
    Serial.print(">> Sending data: ");
    Serial.println(message);
    
    // 等待响应
    startTime = millis();
    while (millis() - startTime < 5000) {
      if (espSerial.available()) {
        char c = espSerial.read();
        Serial.print(c);
      }
    }
    Serial.println();
  } else {
    Serial.println("✗ No prompt received, publish failed");
  }
  
  delay(5000); // 适当延迟，避免频繁发送
}



bool sendATCommand(String cmd, unsigned long timeout) {
  espSerial.flush();
  response = "";
  
  espSerial.println(cmd);
  Serial.print(">> ");
  Serial.println(cmd);
  
  unsigned long startTime = millis();
  while (millis() - startTime < timeout) {
    while (espSerial.available()) {
      char c = espSerial.read();
      response += c;
      
      if (response.indexOf("OK") != -1 || response.indexOf("CONNECT") != -1) {
        Serial.println("<< OK");
        return true;
      } else if (response.indexOf("ERROR") != -1 || 
                 response.indexOf("FAIL") != -1 ||
                 response.indexOf("TIMEOUT") != -1) {
        Serial.println("<< ERROR/FAIL");
        return false;
      }
    }
    delay(10); // Small delay to prevent blocking
  }
  
  Serial.println("<< TIMEOUT");
  return false;
}

void checkConnectionStatus() {
  if (mqttConnected) {
    // 使用专用MQTT状态查询指令 (推荐)
    if (!sendATCommand("AT+MQTTCONN?", 2000)) {
      Serial.println("✗ MQTT connection lost");
      mqttConnected = false;
    } 
    // 或者使用MQTT心跳指令 (替代方案)
    else {
      // 发送MQTT PINGREQ
      Serial.println("Sending MQTT PINGREQ...");
      sendATCommand("AT+MQTTPUB=0,\"ping_topic\",\"ping\",0,0", 2000);
    }
  }
}

bool checkWiFiConnection() {
  if (sendATCommand("AT+CWJAP?", 3000)) {
    if (response.indexOf("No AP") == -1 && response.indexOf("+CWJAP:") != -1) {
      Serial.println("✓ WiFi already connected");
      wifiConnected = true;
      return true;
    }
  }
  wifiConnected = false;
  return false;
}