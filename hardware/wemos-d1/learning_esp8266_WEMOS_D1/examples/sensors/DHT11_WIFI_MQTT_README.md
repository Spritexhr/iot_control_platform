# DHT11 WiFi + MQTT 完整示例

## 📋 功能说明

这是一个完整的 WEMOS D1 温湿度传感器示例，包含以下功能：

- ✅ DHT11 温湿度传感器读取
- ✅ WiFi 连接和自动重连
- ✅ MQTT 数据发布
- ✅ JSON 格式数据（符合平台数据格式）
- ✅ 错误处理和调试信息

---

## 🔧 硬件连接

### DHT11 传感器连接

```
DHT11 传感器          WEMOS D1
─────────────────────────────────
VCC (红色)    →       3.3V 或 5V
GND (黑色)    →       GND
DATA (黄色)   →       D8 (GPIO15)
```

**⚠️ 重要提示：**
- **必须在 DATA 引脚和 VCC 之间连接 4.7KΩ - 10KΩ 上拉电阻！**
- D8 (GPIO15) 不是最佳选择，如果遇到问题，建议使用：
  - D2 (GPIO4) - 推荐
  - D5 (GPIO14) - 推荐
  - D6 (GPIO12)
  - D7 (GPIO13)

### 上拉电阻连接

```
VCC ──┬── 4.7KΩ ──┬── DATA (D8)
      │           │
      └───────────┘
```

---

## ⚙️ 配置步骤

### 1. 修改 WiFi 配置

在代码中找到以下部分并修改：

```cpp
const char* ssid = "你的WiFi名称";
const char* password = "你的WiFi密码";
```

### 2. 修改 MQTT 服务器

```cpp
const char* mqtt_server = "YOUR_MQTT_BROKER_IP";  // 部署前请修改
const int mqtt_port = 1883;
const char* mqtt_topic = "sensors/data";  // MQTT主题
```

### 3. 设置传感器标识（重要！）

为每个设备设置唯一的传感器ID：

```cpp
const char* sensor_name = "温湿度传感器";
const char* sensor_id = "DHT11-WEMOS-001";  // 改为你的唯一ID
```

**命名建议：**
- `DHT11-WEMOS-001` - 第一个设备
- `DHT11-WEMOS-002` - 第二个设备
- `DHT11-WEMOS-003` - 第三个设备

### 4. 修改传感器引脚（可选）

如果 D8 不工作，可以改为其他引脚：

```cpp
#define DHTPIN D2   // 改为 D2, D5, D6, D7 等
```

---

## 📦 所需库

在 Arduino IDE 中安装以下库：

1. **DHT sensor library**
   - 工具 → 管理库 → 搜索 "DHT sensor library"
   - 作者：Adafruit

2. **ESP8266WiFi**（内置）
   - ESP8266 开发板自带

3. **PubSubClient**
   - 工具 → 管理库 → 搜索 "PubSubClient"
   - 作者：Nick O'Leary

---

## 📤 数据格式

### 发送的 JSON 格式

```json
{
  "sensor_name": "温湿度传感器",
  "sensor_id": "DHT11-WEMOS-001",
  "data": {
    "temperature": 25.5,
    "humidity": 60.0
  },
  "is_connected": true
}
```

### 数据字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `sensor_name` | String | 传感器名称 |
| `sensor_id` | String | 传感器唯一ID |
| `data` | Object | 传感器数据对象 |
| `data.temperature` | Float | 温度值（°C） |
| `data.humidity` | Float | 湿度值（%） |
| `is_connected` | Boolean | 连接状态 |

---

## 🚀 使用步骤

### 1. 上传代码

1. 打开 Arduino IDE
2. 选择开发板：**工具** → **开发板** → **ESP8266 Boards** → **LOLIN(WEMOS) D1 R2 & mini**
3. 选择端口：**工具** → **端口** → 选择对应的 COM 端口
4. 点击 **上传**（→）

### 2. 查看串口输出

打开串口监视器（波特率：115200），您应该看到：

```
=== WEMOS D1 温湿度传感器 (WiFi + MQTT) ===
✓ DHT传感器初始化完成
连接WiFi: Xiaomi_soon
..........
✓ WiFi连接成功！
IP地址: 192.168.1.100
=== 初始化完成 ===
温度: 25.5 °C | 湿度: 60.0 %
✓ 数据已发送到MQTT: sensors/data
消息内容: {"sensor_name":"温湿度传感器","sensor_id":"DHT11-WEMOS-001","data":{"temperature":25.5,"humidity":60.0},"is_connected":true}
```

### 3. 验证数据接收

在 Django 服务器端运行：

```bash
cd platform/mqtt_platform
python manage.py mqtt_client
```

您应该看到类似输出：

```
收到消息 [sensors/data]: {"sensor_name":"温湿度传感器","sensor_id":"DHT11-WEMOS-001","data":{"temperature":25.5,"humidity":60.0},"is_connected":true}
  • 温湿度传感器[DHT11-WEMOS-001]:
    - temperature: 25.5
    - humidity: 60.0
✓ 已保存传感器数据（2 个变量） @ 2025-01-XX XX:XX:XX
```

---

## 🔍 代码改进说明

### 修复的问题

1. **修复了 `readSensors()` 函数**
   - 添加了 `valid` 标志来指示数据是否有效
   - 修复了温度和湿度赋值错误（之前赋值反了）
   - 正确处理读取失败的情况

2. **完善了 `loop()` 函数**
   - 实际读取并发送传感器数据
   - 添加了 WiFi 连接检查
   - 添加了错误处理

3. **添加了 JSON 数据构建**
   - 符合平台数据格式要求
   - 包含传感器标识信息

4. **改进了错误处理**
   - WiFi 自动重连
   - MQTT 自动重连
   - 传感器读取失败时的处理

5. **添加了调试信息**
   - 详细的串口输出
   - 状态指示（✓ 成功，✗ 失败，⚠ 警告）

---

## ⚠️ 常见问题

### Q1: DHT传感器读取失败

**解决方案：**
1. 检查上拉电阻是否连接（4.7KΩ - 10KΩ）
2. 检查硬件连接是否正确
3. 尝试更换引脚（D2, D5, D6, D7）
4. 查看 [DHT11 故障排除指南](DHT11_TROUBLESHOOTING.md)

### Q2: WiFi连接失败

**解决方案：**
1. 检查 WiFi 名称和密码是否正确
2. 确认 WiFi 是 2.4GHz（ESP8266 不支持 5GHz）
3. 检查 WiFi 信号强度
4. 查看串口输出的错误信息

### Q3: MQTT连接失败

**解决方案：**
1. 检查 MQTT 服务器地址和端口是否正确
2. 确认服务器防火墙允许 1883 端口
3. 检查网络连接
4. 查看串口输出的错误代码

### Q4: 数据发送成功但服务器没有收到

**解决方案：**
1. 确认服务器端 MQTT 客户端正在运行
2. 确认订阅的主题是 `sensors/data`
3. 检查 JSON 格式是否正确
4. 查看服务器端日志

---

## 📊 性能优化

### 调整发送频率

修改 `loop()` 函数中的延迟：

```cpp
delay(5000);   // 5秒发送一次（默认）
delay(10000);  // 10秒发送一次
delay(30000);  // 30秒发送一次
```

**注意：** DHT11 需要至少 2 秒的读取间隔。

### 添加数据验证

在发送前验证数据范围：

```cpp
if (sensorData.temperature < -40 || sensorData.temperature > 80) {
  Serial.println(F("⚠ 温度值异常，跳过发送"));
  return;
}
```

---

## 🔄 下一步

1. ✅ 上传代码到 WEMOS D1
2. ✅ 验证串口输出
3. ✅ 启动 Django MQTT 客户端
4. ✅ 在 Admin 后台查看数据
5. 📊 创建数据可视化界面（可选）

---

## 📚 相关文档

- [DHT11 基础示例](dht11_basic.ino) - 仅串口输出的简单版本
- [DHT11 故障排除指南](DHT11_TROUBLESHOOTING.md) - 硬件问题排查
- [WEMOS D1 学习指南](../README.md) - 完整的学习文档
- [Arduino 配置说明](../../ARDUINO_SETUP.md) - Arduino UNO + ESP-01 配置

---

**祝您使用愉快！** 🚀

