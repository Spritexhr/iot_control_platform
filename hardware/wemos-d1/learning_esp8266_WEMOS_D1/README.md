# Wemos D1 学习指南

## 📚 目录

1. [硬件介绍](#硬件介绍)
2. [开发环境搭建](#开发环境搭建)
3. [快速开始](#快速开始)
4. [基础示例](#基础示例)
5. [常用功能](#常用功能)
6. [进阶主题](#进阶主题)
7. [常见问题](#常见问题)
8. [资源链接](#资源链接)

---

## 硬件介绍

### Wemos D1 是什么？

Wemos D1 是一款基于 ESP8266 的开发板，兼容 Arduino 开发环境，具有 WiFi 功能，非常适合 IoT 项目开发。

### 主要规格

- **微控制器**: ESP8266
- **工作电压**: 3.3V（注意：不是 5V！）
- **数字 I/O 引脚**: 11 个
- **模拟输入引脚**: 1 个（A0）
- **Flash 存储**: 4MB
- **WiFi**: 802.11 b/g/n (2.4GHz)
- **USB 接口**: Micro USB
- **尺寸**: 34.2mm × 25.6mm

### 引脚映射

Wemos D1 的引脚编号与 ESP8266 的 GPIO 编号对应：

| Wemos D1 引脚 | ESP8266 GPIO | 功能说明 |
|--------------|--------------|----------|
| D0 | GPIO16 | 内置 LED（低电平点亮） |
| D1 | GPIO5 | SCL (I2C) |
| D2 | GPIO4 | SDA (I2C) |
| D3 | GPIO0 | 带内部上拉，启动模式选择 |
| D4 | GPIO2 | 带内部上拉，内置 LED |
| D5 | GPIO14 | SPI CLK |
| D6 | GPIO12 | SPI MISO |
| D7 | GPIO13 | SPI MOSI |
| D8 | GPIO15 | 带内部下拉，SPI CS |
| RX | GPIO3 | UART RX |
| TX | GPIO1 | UART TX |
| A0 | ADC | 模拟输入 (0-3.3V) |

**重要提示**：
- GPIO16 不能用于中断或 I2C/SPI
- GPIO0、GPIO2、GPIO15 在启动时用于确定启动模式，使用时要小心

---

## 开发环境搭建

### 步骤 1: 安装 Arduino IDE

1. 从 [Arduino 官网](https://www.arduino.cc/en/software) 下载并安装 Arduino IDE
2. 推荐版本：Arduino IDE 1.8.x 或 2.x

### 步骤 2: 添加 ESP8266 开发板支持

1. 打开 Arduino IDE
2. 进入 **文件** → **首选项**
3. 在"附加开发板管理器网址"中添加：
   ```
   http://arduino.esp8266.com/stable/package_esp8266com_index.json
   ```
4. 点击 **工具** → **开发板** → **开发板管理器**
5. 搜索 "esp8266"，安装 "esp8266 by ESP8266 Community"（推荐版本 3.0.0 或更高）

### 步骤 3: 选择开发板

1. 连接 Wemos D1 到电脑（通过 USB 线）
2. 在 Arduino IDE 中：
   - **工具** → **开发板** → **ESP8266 Boards** → **LOLIN(WEMOS) D1 R2 & mini**
   - **端口**: 选择对应的 COM 端口（Windows）或 /dev/ttyUSB*（Linux）

### 步骤 4: 安装驱动（Windows）

如果电脑无法识别开发板，需要安装 USB 转串口驱动（通常使用 CH340 或 CP2102 芯片）：
- CH340 驱动下载：[这里](http://www.wch.cn/download/CH341SER_EXE.html)
- CP2102 驱动下载：[这里](https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers)

---

## 快速开始

### Hello World - 闪烁 LED

这是最简单的示例，让板载 LED 闪烁：

```cpp
// Wemos D1 板载 LED 连接到 GPIO2 (D4)
#define LED_PIN 2  // 或使用 D4

void setup() {
  pinMode(LED_PIN, OUTPUT);
  Serial.begin(115200);
  Serial.println("Wemos D1 LED Blink Started!");
}

void loop() {
  digitalWrite(LED_PIN, LOW);   // LED 点亮（低电平有效）
  delay(1000);
  digitalWrite(LED_PIN, HIGH);  // LED 熄灭
  delay(1000);
}
```

**上传步骤**：
1. 将代码复制到 Arduino IDE
2. 点击 **验证**（✓）检查代码
3. 点击 **上传**（→）上传到开发板
4. 打开串口监视器（波特率 115200）查看输出

---

## 基础示例

### 示例 1: 读取模拟输入

```cpp
// 读取 A0 引脚模拟值（0-1024 对应 0-3.3V）
void setup() {
  Serial.begin(115200);
  pinMode(A0, INPUT);
}

void loop() {
  int sensorValue = analogRead(A0);
  float voltage = sensorValue * (3.3 / 1024.0);
  
  Serial.print("ADC Value: ");
  Serial.print(sensorValue);
  Serial.print(" | Voltage: ");
  Serial.print(voltage);
  Serial.println("V");
  
  delay(500);
}
```

### 示例 2: 数字输入输出

```cpp
// D5 作为输入，D4 作为输出
#define INPUT_PIN 14   // D5 = GPIO14
#define OUTPUT_PIN 2   // D4 = GPIO2

void setup() {
  Serial.begin(115200);
  pinMode(INPUT_PIN, INPUT_PULLUP);  // 启用内部上拉电阻
  pinMode(OUTPUT_PIN, OUTPUT);
}

void loop() {
  int buttonState = digitalRead(INPUT_PIN);
  
  if (buttonState == LOW) {  // 按下按钮（连接 GND）
    digitalWrite(OUTPUT_PIN, LOW);  // LED 点亮
    Serial.println("Button Pressed!");
  } else {
    digitalWrite(OUTPUT_PIN, HIGH);  // LED 熄灭
  }
  
  delay(50);
}
```

### 示例 3: PWM 输出（调光）

```cpp
// 使用 PWM 控制 LED 亮度
#define LED_PIN 2  // D4

void setup() {
  pinMode(LED_PIN, OUTPUT);
  Serial.begin(115200);
}

void loop() {
  // 渐亮
  for (int brightness = 0; brightness <= 255; brightness++) {
    analogWrite(LED_PIN, brightness);
    delay(10);
  }
  
  // 渐暗
  for (int brightness = 255; brightness >= 0; brightness--) {
    analogWrite(LED_PIN, brightness);
    delay(10);
  }
}
```

**注意**：ESP8266 的 PWM 分辨率是 10 位（0-1023），但 `analogWrite()` 使用 8 位（0-255）。

### 示例 4: DHT11 温湿度传感器

读取 DHT11 温湿度传感器数据：

```cpp
#include <DHT.h>

#define DHTPIN D2  // D2 引脚 (GPIO4)
#define DHTTYPE DHT11

DHT dht(DHTPIN, DHTTYPE);

void setup() {
  Serial.begin(115200);
  delay(1000);
  dht.begin();
  Serial.println(F("\n=== DHT11 温湿度传感器 ==="));
}

void loop() {
  float h = dht.readHumidity();
  float t = dht.readTemperature();
  
  if (isnan(h) || isnan(t)) {
    Serial.println(F("✗ DHT传感器读取失败！"));
    delay(2000);
    return;
  }
  
  Serial.print(F("湿度: "));
  Serial.print(h, 1);
  Serial.print(F(" %\t温度: "));
  Serial.print(t, 1);
  Serial.println(F(" °C"));

  delay(2000);
}
```

**重要提示**：
- 需要安装 DHT sensor library：**工具** → **管理库** → 搜索 "DHT sensor library"
- **必须在 DATA 引脚和 VCC 之间连接 4.7KΩ - 10KΩ 上拉电阻！**
- 如果读取失败，请查看 [DHT11 故障排除指南](examples/sensors/DHT11_TROUBLESHOOTING.md)

**完整示例代码**：参见 [examples/sensors/dht11_basic.ino](examples/sensors/dht11_basic.ino)

---

## 常用功能

### WiFi 连接

```cpp
#include <ESP8266WiFi.h>

const char* ssid = "你的WiFi名称";
const char* password = "你的WiFi密码";

void setup() {
  Serial.begin(115200);
  delay(100);
  
  // 连接 WiFi
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  
  Serial.print("正在连接 WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println();
  Serial.println("WiFi 连接成功！");
  Serial.print("IP 地址: ");
  Serial.println(WiFi.localIP());
}

void loop() {
  // 你的代码
}
```

### HTTP 客户端请求

```cpp
#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>

const char* ssid = "你的WiFi名称";
const char* password = "你的WiFi密码";

void setup() {
  Serial.begin(115200);
  WiFi.begin(ssid, password);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println("\nWiFi 已连接");
}

void loop() {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    WiFiClient client;
    
    http.begin(client, "http://httpbin.org/get");
    int httpCode = http.GET();
    
    if (httpCode > 0) {
      String payload = http.getString();
      Serial.println(httpCode);
      Serial.println(payload);
    }
    
    http.end();
  }
  
  delay(10000);  // 每 10 秒请求一次
}
```

### WiFi Web 服务器

```cpp
#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>

const char* ssid = "你的WiFi名称";
const char* password = "你的WiFi密码";

ESP8266WebServer server(80);

void handleRoot() {
  String html = "<html><body>";
  html += "<h1>Wemos D1 Web Server</h1>";
  html += "<p>这是一个简单的 Web 服务器</p>";
  html += "<a href=\"/led/on\">打开 LED</a><br>";
  html += "<a href=\"/led/off\">关闭 LED</a>";
  html += "</body></html>";
  
  server.send(200, "text/html", html);
}

void handleLEDOn() {
  digitalWrite(2, LOW);  // LED 点亮
  server.send(200, "text/plain", "LED 已打开");
}

void handleLEDOff() {
  digitalWrite(2, HIGH);  // LED 熄灭
  server.send(200, "text/plain", "LED 已关闭");
}

void setup() {
  Serial.begin(115200);
  pinMode(2, OUTPUT);
  
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println("\nWiFi 已连接");
  Serial.print("IP 地址: ");
  Serial.println(WiFi.localIP());
  
  server.on("/", handleRoot);
  server.on("/led/on", handleLEDOn);
  server.on("/led/off", handleLEDOff);
  server.begin();
}

void loop() {
  server.handleClient();
}
```

### I2C 通信（连接传感器）

```cpp
#include <Wire.h>

void setup() {
  Wire.begin();  // SDA=D2 (GPIO4), SCL=D1 (GPIO5)
  Serial.begin(115200);
  
  Serial.println("\nI2C 扫描器");
  byte error, address;
  int nDevices = 0;
  
  for (address = 1; address < 127; address++) {
    Wire.beginTransmission(address);
    error = Wire.endTransmission();
    
    if (error == 0) {
      Serial.print("在地址 0x");
      if (address < 16) Serial.print("0");
      Serial.print(address, HEX);
      Serial.println(" 发现设备");
      nDevices++;
    }
  }
  
  if (nDevices == 0) {
    Serial.println("未发现 I2C 设备");
  }
}

void loop() {
  // 你的代码
}
```

---

## 进阶主题

### 1. OTA 更新（无线更新）

允许通过 WiFi 上传新固件，无需 USB 线：

```cpp
#include <ESP8266WiFi.h>
#include <ESP8266mDNS.h>
#include <WiFiUdp.h>
#include <ArduinoOTA.h>

const char* ssid = "你的WiFi名称";
const char* password = "你的WiFi密码";

void setup() {
  Serial.begin(115200);
  WiFi.begin(ssid, password);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  ArduinoOTA.setHostname("wemos-d1");
  ArduinoOTA.begin();
  
  Serial.println("OTA 准备就绪");
}

void loop() {
  ArduinoOTA.handle();
  // 你的代码
}
```

上传时，在 Arduino IDE 中选择 **工具** → **端口** → **网络端口**，选择你的设备。

### 2. 深度睡眠模式（省电）

```cpp
#define SLEEP_TIME 30e6  // 30 秒（微秒）

void setup() {
  Serial.begin(115200);
  Serial.println("设备启动");
  
  // 你的代码
  
  Serial.println("进入深度睡眠...");
  ESP.deepSleep(SLEEP_TIME);
}

void loop() {
  // 深度睡眠模式下不会执行
}
```

**注意**：深度睡眠后，设备会重启，所以代码从 `setup()` 开始执行。

### 3. 使用 SPIFFS 文件系统

存储配置文件、网页文件等：

```cpp
#include <FS.h>

void setup() {
  Serial.begin(115200);
  
  if (SPIFFS.begin()) {
    Serial.println("SPIFFS 初始化成功");
    
    // 写入文件
    File file = SPIFFS.open("/test.txt", "w");
    if (file) {
      file.println("Hello, SPIFFS!");
      file.close();
      Serial.println("文件写入成功");
    }
    
    // 读取文件
    file = SPIFFS.open("/test.txt", "r");
    if (file) {
      Serial.println("文件内容:");
      while (file.available()) {
        Serial.write(file.read());
      }
      file.close();
    }
  } else {
    Serial.println("SPIFFS 初始化失败");
  }
}

void loop() {
  // 你的代码
}
```

### 4. MQTT 通信

用于 IoT 设备间通信：

```cpp
#include <ESP8266WiFi.h>
#include <PubSubClient.h>

const char* ssid = "你的WiFi名称";
const char* password = "你的WiFi密码";
const char* mqtt_server = "broker.hivemq.com";  // 公共 MQTT broker

WiFiClient espClient;
PubSubClient client(espClient);

void callback(char* topic, byte* payload, unsigned int length) {
  Serial.print("消息到达 [");
  Serial.print(topic);
  Serial.print("]: ");
  for (int i = 0; i < length; i++) {
    Serial.print((char)payload[i]);
  }
  Serial.println();
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("连接 MQTT broker...");
    if (client.connect("WemosClient")) {
      Serial.println("已连接");
      client.subscribe("test/topic");
    } else {
      Serial.print("失败, rc=");
      Serial.print(client.state());
      Serial.println(" 5秒后重试");
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();
  
  // 发布消息
  client.publish("test/topic", "Hello from Wemos D1");
  delay(5000);
}
```

需要安装库：**工具** → **管理库** → 搜索 "PubSubClient"

---

## 常见问题

### Q1: 上传失败 "Timed out waiting for packet header"

**解决方案**：
- 按住开发板上的 RESET 按钮
- 在上传过程中松开 RESET 按钮
- 或尝试降低上传速度：**工具** → **Upload Speed** → **115200**

### Q2: 串口监视器显示乱码

**解决方案**：
- 检查波特率设置（通常为 115200）
- 确保代码中的 `Serial.begin()` 波特率与监视器一致

### Q3: WiFi 连接失败

**解决方案**：
- 检查 SSID 和密码是否正确
- 确保路由器支持 2.4GHz（ESP8266 不支持 5GHz）
- 检查信号强度

### Q4: GPIO 不能正常工作

**解决方案**：
- 确认引脚编号正确（使用 GPIO 编号而非 D 编号）
- 检查是否需要上拉/下拉电阻
- 注意某些引脚在启动时有特殊功能

### Q5: 供电问题

**解决方案**：
- 使用稳定的 USB 电源（推荐 1A 或更高）
- 避免同时使用过多高功耗外设
- 如需外部供电，使用 3.3V（不是 5V！）

### Q6: DHT11 传感器读取失败

**解决方案**：
1. **检查上拉电阻**（最常见原因！）
   - 必须在 DATA 引脚和 VCC 之间连接 4.7KΩ - 10KΩ 上拉电阻
   - 没有上拉电阻，传感器无法正常工作

2. **检查连接**
   - VCC → 3.3V 或 5V
   - GND → GND
   - DATA → D2（或其他可用引脚）

3. **尝试更换引脚**
   - 如果 D2 不工作，尝试 D5 (GPIO14)、D6 (GPIO12)、D7 (GPIO13)

4. **检查传感器类型**
   - 确认代码中设置的是 DHT11 还是 DHT22

5. **增加延迟时间**
   - DHT11 需要至少 2 秒的读取间隔

**详细故障排除**：请查看 [DHT11 故障排除指南](examples/sensors/DHT11_TROUBLESHOOTING.md)

---

## 资源链接

### 官方资源
- [ESP8266 Arduino Core 文档](https://arduino-esp8266.readthedocs.io/)
- [ESP8266 GitHub](https://github.com/esp8266/Arduino)
- [Wemos 官网](https://www.wemos.cc/en/latest/d1/d1_mini.html)

### 常用库
- **WiFi**: ESP8266WiFi（内置）
- **Web Server**: ESP8266WebServer（内置）
- **HTTP Client**: ESP8266HTTPClient（内置）
- **MQTT**: PubSubClient
- **JSON**: ArduinoJson
- **NTP**: NTPClient

### 学习资源
- [ESP8266 社区论坛](https://www.esp8266.com/)
- [Arduino 官方文档](https://www.arduino.cc/reference/en/)

### 推荐项目
1. **智能家居控制器**：控制灯光、风扇等
2. **环境监测站**：温度、湿度传感器 + WiFi 上传
3. **物联网开关**：远程控制电器
4. **天气预报显示器**：获取并显示天气信息

---

## 项目结构建议

```
learning_esp8266_WEMOS_D1/
├── examples/              # 示例代码
│   ├── basic/            # 基础示例
│   ├── wifi/             # WiFi 相关
│   ├── sensors/          # 传感器示例
│   └── advanced/         # 进阶示例
├── libraries/            # 自定义库（如需要）
├── data/                 # SPIFFS 文件
└── README.md            # 本文件
```

---

## 下一步学习建议

1. ✅ 完成基础示例，熟悉 GPIO 操作
2. ✅ 学习 WiFi 连接和 HTTP 通信
3. ✅ 尝试连接常见传感器（DHT22、DS18B20 等）
4. ✅ 学习 MQTT 协议进行 IoT 通信
5. ✅ 实现一个完整的 IoT 项目

**祝学习愉快！🚀**

