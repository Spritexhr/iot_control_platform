#include <DHT.h>
#include <ESP8266WiFi.h>
#include <PubSubClient.h>

// DHT11传感器配置
#define DHTPIN D5  // WEMOS D1 上的 D5 引脚 (GPIO15)
#define DHTTYPE DHT11

// WiFi配置
// const char* ssid = "Xiaomi_soon";
// const char* password = "174222SUN";
// const char* ssid = "XHR_iPhone";
// const char* password = "12345678aA";
const char* ssid = "YOUR_WIFI_SSID";      // 部署前请修改
const char* password = "YOUR_WIFI_PASSWORD";

// MQTT配置
const char* mqtt_server = "YOUR_MQTT_BROKER_IP";  // 部署前请修改
const int mqtt_port = 1883;
const char* mqtt_topic = "sensors/data";  // MQTT主题

// 传感器标识信息
const char* sensor_name = "温湿度传感器";
const char* sensor_id = "DHT11-WEMOS-001";  // 唯一标识符，请为每个设备设置不同的ID

// 全局对象
WiFiClient espClient;
PubSubClient client(espClient);
DHT dht(DHTPIN, DHTTYPE);

// 温湿度传感器数据结构
struct SensorData {
  float temperature;
  float humidity;
  bool valid;  // 数据是否有效
};

// 读取传感器函数
SensorData readSensors() {
  SensorData data;
  data.valid = false;  // 默认无效
  
  float h = dht.readHumidity();
  float t = dht.readTemperature();
  
  if (isnan(h) || isnan(t)) {
    Serial.println(F("✗ DHT传感器读取失败！"));
    return data;  // 返回无效数据
  }

  // 修复：温度和湿度赋值正确
  data.temperature = t;  // 温度
  data.humidity = h;     // 湿度
  data.valid = true;
  
  return data;
}

// MQTT消息回调函数
void callback(char* topic, byte* payload, unsigned int length) {
  Serial.print(F("消息到达 ["));
  Serial.print(topic);
  Serial.print(F("]: "));
  for (int i = 0; i < length; i++) {
    Serial.print((char)payload[i]);
  }
  Serial.println();
}

// 重新连接MQTT
void reconnect() {
  while (!client.connected()) {
    Serial.print(F("连接 MQTT broker..."));
    
    // 尝试连接，使用唯一的客户端ID
    String clientId = "WemosD1-";
    clientId += String(random(0xffff), HEX);
    
    if (client.connect(clientId.c_str())) {
      Serial.println(F("已连接"));
      
      // 订阅主题（如果需要接收命令）
      client.subscribe("sensors/command");
      Serial.println(F("✓ 已订阅主题: sensors/command"));
    } else {
      Serial.print(F("失败, rc="));
      Serial.print(client.state());
      Serial.println(F(" 5秒后重试"));
      delay(5000);
    }
  }
}

// 构建JSON格式的传感器数据
String buildSensorJSON(float temperature, float humidity) {
  // 格式: {"sensor_name":"温湿度传感器","sensor_id":"DHT11-WEMOS-001","data":{"temperature":25.5,"humidity":60.0},"is_connected":true}
  String json = "{";
  json += "\"sensor_name\":\"" + String(sensor_name) + "\",";
  json += "\"sensor_id\":\"" + String(sensor_id) + "\",";
  json += "\"data\":{";
  json += "\"temperature\":" + String(temperature, 1) + ",";
  json += "\"humidity\":" + String(humidity, 1);
  json += "},";
  json += "\"is_connected\":true";
  json += "}";
  return json;
}

void setup() {
  Serial.begin(115200);
  delay(1000);  // 等待串口初始化
  
  Serial.println(F("\n=== WEMOS D1 温湿度传感器 (WiFi + MQTT) ==="));
  
  // 初始化DHT传感器
  dht.begin();
  Serial.println(F("✓ DHT传感器初始化完成"));
  delay(2000);  // 等待传感器稳定
  
  // 连接WiFi
  Serial.print(F("连接WiFi: "));
  Serial.println(ssid);
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  
  int wifiAttempts = 0;
  while (WiFi.status() != WL_CONNECTED && wifiAttempts < 20) {
    delay(500);
    Serial.print(F("."));
    wifiAttempts++;
  }
  Serial.println();
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println(F("✓ WiFi连接成功！"));
    Serial.print(F("IP地址: "));
    Serial.println(WiFi.localIP());
  } else {
    Serial.println(F("✗ WiFi连接失败！"));
    Serial.println(F("请检查WiFi名称和密码"));
  }
  
  // 配置MQTT
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
  
  Serial.println(F("=== 初始化完成 ==="));
}

void loop() {
  // 检查WiFi连接
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println(F("WiFi连接断开，尝试重连..."));
    WiFi.begin(ssid, password);
    delay(5000);
    return;
  }
  
  // 检查并连接MQTT
  if (!client.connected()) {
    reconnect();
  }
  client.loop();  // 处理MQTT消息
  
  // 读取传感器数据
  SensorData sensorData = readSensors();
  
  if (sensorData.valid) {
    // 显示读取的数据
    Serial.print(F("温度: "));
    Serial.print(sensorData.temperature, 1);
    Serial.print(F(" °C | 湿度: "));
    Serial.print(sensorData.humidity, 1);
    Serial.println(F(" %"));
    
    // 构建JSON消息
    String jsonMessage = buildSensorJSON(sensorData.temperature, sensorData.humidity);
    
    // 发布到MQTT
    if (client.publish(mqtt_topic, jsonMessage.c_str())) {
      Serial.print(F("✓ 数据已发送到MQTT: "));
      Serial.println(mqtt_topic);
      Serial.print(F("消息内容: "));
      Serial.println(jsonMessage);
    } else {
      Serial.println(F("✗ MQTT发布失败"));
    }
  } else {
    Serial.println(F("⚠ 传感器数据无效，跳过本次发送"));
  }
  
  // 等待5秒后再次读取（DHT11需要至少2秒间隔）
  delay(5000);
}

