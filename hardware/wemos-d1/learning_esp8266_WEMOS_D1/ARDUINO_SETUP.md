# Arduino ESP01 传感器上传配置说明

## 硬件配置

- **主控**: Arduino UNO/Nano
- **WiFi模块**: ESP-01 (ESP8266)
- **传感器**: DHT11 温湿度传感器
- **连接**:
  - DHT11 数据引脚 → Arduino D2
  - ESP-01 RX → Arduino D8
  - ESP-01 TX → Arduino D9

## 代码修改说明

### ✅ 已完成的修改

#### 1. 更新MQTT主题

```cpp
const char* MQTT_TOPIC = "sensors/data";  // 从 "LED_TEST" 改为 "sensors/data"
```

#### 2. 添加传感器信息

```cpp
// 传感器标识信息
const char* SENSOR_NAME = "温湿度传感器";
const char* SENSOR_ID = "DHT11-ESP01-001";  // 唯一标识符
```

**注意**: 如果您有多个传感器设备，请为每个设备设置不同的 `SENSOR_ID`，例如：
- `DHT11-ESP01-001`
- `DHT11-ESP01-002`
- `DHT11-ESP01-003`

#### 3. 更新数据格式为JSON

**旧格式：**
```cpp
String message = "temperature:" + String(t) + "  humidity:" + String(h);
```

**新格式（JSON）：**
```cpp
String jsonMessage = "{";
jsonMessage += "\"sensor_name\":\"温湿度传感器\",";
jsonMessage += "\"sensor_id\":\"DHT11-ESP01-001\",";
jsonMessage += "\"data\":{";
jsonMessage += "\"temperature\":25.5,";
jsonMessage += "\"humidity\":60.5";
jsonMessage += "},";
jsonMessage += "\"is_connected\":true";
jsonMessage += "}";
```

**发送的实际数据示例：**
```json
{
  "sensor_name": "温湿度传感器",
  "sensor_id": "DHT11-ESP01-001",
  "data": {
    "temperature": 25.5,
    "humidity": 60.5
  },
  "is_connected": true
}
```

## 配置步骤

### 1. 修改WiFi连接信息

在代码中找到以下部分并修改为您的WiFi信息：

```cpp
const char* WIFI_SSID = "你的WiFi名称";
const char* WIFI_PASSWORD = "你的WiFi密码";
```

### 2. 修改MQTT服务器信息

```cpp
const char* MQTT_BROKER = "YOUR_MQTT_BROKER_IP";  // 部署前请修改
const int MQTT_PORT = 1883;                // MQTT端口
const char* MQTT_USERNAME = "esp01";       // MQTT用户名
const char* MQTT_PASSWORD = "";      // 若 EMQX 需要认证请填写
```

### 3. 修改传感器标识（重要！）

如果您有多个传感器，必须为每个设备设置唯一的ID：

```cpp
const char* SENSOR_ID = "DHT11-ESP01-001";  // 改为您的设备唯一ID
```

建议命名规则：`传感器型号-设备类型-编号`
- `DHT11-ESP01-001` - 第一个DHT11传感器
- `DHT11-ESP01-002` - 第二个DHT11传感器
- `DHT22-ESP01-001` - DHT22传感器
- `BMP280-ESP01-001` - 气压传感器

## 上传和测试

### 1. 上传代码到Arduino

1. 打开Arduino IDE
2. 选择正确的板型（Arduino UNO/Nano）
3. 选择正确的串口
4. 点击上传

### 2. 查看串口监视器

打开串口监视器（波特率：9600），您应该看到：

```
=== ESP01 MQTT Setup ===
Initializing ESP01...
>> AT
<< OK
>> AT+CWMODE=1
<< OK
✓ WiFi already connected
>> AT+MQTTUSERCFG=0,1,"username","password","clientid",0,0,""
<< OK
>> AT+MQTTCONN=0,"YOUR_MQTT_BROKER_IP",1883,1
<< OK
>> AT+MQTTSUB=0,"sensors/data",0
<< OK
✓ MQTT fully initialized
=== Setup Complete ===

Humidity: 60.5 %	Temperature: 25.5 *C
Sending JSON: {"sensor_name":"温湿度传感器","sensor_id":"DHT11-ESP01-001","data":{"temperature":25.5,"humidity":60.5},"is_connected":true}
>> AT+MQTTPUB=0,"sensors/data","...",0,0
<< OK
✓ Data sent successfully!
```

### 3. 验证数据接收

在Django服务器端运行：

```bash
cd d:\learning\graduation_thesis\platform\mqtt_platform
python manage.py mqtt_client
```

您应该看到类似的输出：

```
正在连接到MQTT Broker: localhost:1883
订阅主题: sensors/data
✓ 成功连接到MQTT Broker
✓ 已订阅主题: sensors/data
MQTT客户端已启动，等待消息...

收到消息 [sensors/data]: {"sensor_name":"温湿度传感器","sensor_id":"DHT11-ESP01-001","data":{"temperature":25.5,"humidity":60.5},"is_connected":true}
  • 温湿度传感器[DHT11-ESP01-001]:
    - temperature: 25.5
    - humidity: 60.5
✓ 已保存传感器数据（2 个变量） @ 2025-11-29 10:30:15
```

## 数据格式说明

### 必需字段

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `sensor_name` | String | 传感器名称 | "温湿度传感器" |
| `sensor_id` | String | 传感器唯一ID | "DHT11-ESP01-001" |
| `data` | Object | 传感器数据对象 | `{"temperature": 25.5, "humidity": 60.5}` |

### 可选字段

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `is_connected` | Boolean | true | 传感器连接状态 |
| `timestamp` | String | 服务器时间 | ISO 8601格式时间戳 |

### data对象支持的变量

可以包含任意数量的变量名-值对：

```json
{
  "data": {
    "temperature": 25.5,    // 温度
    "humidity": 60.5,       // 湿度
    "pressure": 1013.25,    // 气压（如果有）
    "light": 850.5,         // 光照（如果有）
    "pm25": 35              // PM2.5（如果有）
  }
}
```

## 常见问题

### Q1: 串口显示 "ESP01 not responding"

**解决方案：**
1. 检查ESP-01连接是否正确
2. 确认ESP-01供电充足（需要3.3V，至少300mA）
3. 检查RX、TX连接是否正确
4. 尝试重新上电

### Q2: WiFi连接失败

**解决方案：**
1. 确认WiFi名称和密码正确
2. 确认WiFi是2.4GHz（ESP-01不支持5GHz）
3. 检查WiFi信号强度
4. 尝试连接其他WiFi网络测试

### Q3: MQTT连接失败

**解决方案：**
1. 确认MQTT服务器地址和端口正确
2. 检查用户名和密码
3. 确认服务器防火墙允许1883端口
4. 检查网络连接

### Q4: 数据发送成功但服务器没有收到

**解决方案：**
1. 确认服务器端MQTT客户端正在运行
2. 确认订阅的主题是 `sensors/data`
3. 检查JSON格式是否正确（使用在线JSON验证工具）
4. 查看服务器端日志

### Q5: DHT传感器读取失败（返回NaN）

**解决方案：**
1. 检查传感器连接
2. 确认使用正确的传感器类型（DHT11 vs DHT22）
3. 检查供电是否稳定
4. 在传感器数据引脚和VCC之间添加4.7K上拉电阻

## 扩展功能

### 添加更多传感器

如果您想添加更多传感器（如光照、气压等），只需修改 `data` 对象：

```cpp
String jsonMessage = "{";
jsonMessage += "\"sensor_name\":\"环境监测站\",";
jsonMessage += "\"sensor_id\":\"ENV-STATION-001\",";
jsonMessage += "\"data\":{";
jsonMessage += "\"temperature\":" + String(t, 1) + ",";
jsonMessage += "\"humidity\":" + String(h, 1) + ",";
jsonMessage += "\"light\":" + String(lightValue) + ",";      // 添加光照
jsonMessage += "\"pressure\":" + String(pressure, 2);         // 添加气压
jsonMessage += "},";
jsonMessage += "\"is_connected\":true";
jsonMessage += "}";
```

### 调整发送频率

修改 `delay()` 值来改变数据发送频率：

```cpp
delay(5000);   // 5秒发送一次
delay(30000);  // 30秒发送一次
delay(60000);  // 1分钟发送一次
```

### 添加数据验证

在发送前验证数据范围：

```cpp
// 验证温度范围
if (t < -40 || t > 80) {
  Serial.println("✗ Temperature out of range!");
  return;
}

// 验证湿度范围
if (h < 0 || h > 100) {
  Serial.println("✗ Humidity out of range!");
  return;
}
```

## 性能优化

### 1. 减少字符串拼接

如果内存紧张，可以使用静态缓冲区：

```cpp
char jsonBuffer[256];
snprintf(jsonBuffer, sizeof(jsonBuffer),
  "{\"sensor_name\":\"温湿度传感器\",\"sensor_id\":\"DHT11-ESP01-001\",\"data\":{\"temperature\":%.1f,\"humidity\":%.1f},\"is_connected\":true}",
  t, h);
String jsonMessage = String(jsonBuffer);
```

### 2. 批量发送

如果需要节省网络流量，可以缓存多个读数后一起发送。

### 3. 休眠模式

如果使用电池供电，可以考虑使用深度睡眠模式。

## 下一步

1. ✅ 上传代码到Arduino
2. ✅ 验证串口输出
3. ✅ 启动Django MQTT客户端
4. ✅ 在Admin后台查看数据
5. 📊 创建数据可视化界面（可选）

## 参考文档

- [MQTT_README.md](platform/mqtt_platform/MQTT_README.md) - MQTT配置说明
- [DATA_FORMAT.md](platform/mqtt_platform/DATA_FORMAT.md) - 数据格式详细说明
- [JSONFIELD_GUIDE.md](platform/mqtt_platform/JSONFIELD_GUIDE.md) - JSONField使用指南

