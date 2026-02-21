# 🚀 快速开始指南 - DHT11 传感器 V2

## 📦 准备工作

### 1. 硬件清单
- [ ] Wemos D1 开发板 × 1
- [ ] DHT11 温湿度传感器 × 1
- [ ] USB 数据线 × 1
- [ ] 杜邦线若干（如果传感器不是模块）

### 2. 软件准备
- [ ] Arduino IDE（推荐 1.8.19 或更高版本）
- [ ] ESP8266 开发板支持包
- [ ] 所需库文件（见下文）

## 🔧 安装步骤

### 步骤 1：安装 Arduino IDE

1. 下载 Arduino IDE：https://www.arduino.cc/en/software
2. 安装并打开 Arduino IDE

### 步骤 2：添加 ESP8266 开发板支持

1. 打开：`文件` → `首选项`
2. 在"附加开发板管理器网址"中添加：
   ```
   http://arduino.esp8266.com/stable/package_esp8266com_index.json
   ```
3. 打开：`工具` → `开发板` → `开发板管理器`
4. 搜索"ESP8266"，安装"esp8266 by ESP8266 Community"

### 步骤 3：安装必需的库

打开：`工具` → `管理库`，搜索并安装以下库：

```
✅ DHT sensor library        (by Adafruit)
✅ Adafruit Unified Sensor   (by Adafruit)
✅ PubSubClient              (by Nick O'Leary)
✅ NTPClient                 (by Fabrice Weinberg)
✅ ArduinoJson               (by Benoit Blanchon) - 选择 6.x 版本
```

### 步骤 4：硬件连接

```
DHT11 传感器    →    Wemos D1
────────────────────────────
VCC (电源)      →    3.3V
GND (地线)      →    GND
DATA (数据)     →    D5
```

**注意**：
- DHT11 有 4 个引脚的和 3 个引脚的两种
- 3 引脚模块版自带上拉电阻，直接连接
- 4 引脚裸芯片需要在 DATA 和 VCC 之间加 4.7K-10K 上拉电阻

### 步骤 5：配置固件

1. 打开 `temp_humi_sensor_v2.ino`
2. 修改以下配置：

```cpp
// ============ 必须修改 ============

// WiFi 配置
const char* WIFI_SSID = "你的WiFi名称";         // ← 修改这里
const char* WIFI_PASSWORD = "你的WiFi密码";     // ← 修改这里

// MQTT 服务器
const char* MQTT_SERVER = "你的MQTT服务器IP";   // ← 修改这里
const int MQTT_PORT = 1883;

// 传感器标识（每个设备必须唯一）
const char* SENSOR_ID = "DHT11-WEMOS-001";      // ← 修改这里
const char* SENSOR_NAME = "客厅温湿度传感器";   // ← 修改这里
const char* SENSOR_LOCATION = "客厅-东侧";      // ← 修改这里
```

### 步骤 6：上传固件

1. 选择开发板：`工具` → `开发板` → `LOLIN(WEMOS) D1 R2 & mini`
2. 选择端口：`工具` → `端口` → 选择对应的 COM 口
3. 点击"上传"按钮（→）

上传成功后，会显示：
```
Leaving...
Hard resetting via RTS pin...
```

### 步骤 7：查看运行日志

1. 打开串口监视器：`工具` → `串口监视器`
2. 设置波特率为 `115200`
3. 查看设备启动和运行日志

## 📋 Django 后端配置

### 在 Django Admin 中创建传感器

```python
# 1. 创建传感器类型
传感器类型名称: DHT11温湿度传感器
数据字段定义: {"temperature": "float", "humidity": "float"}
单位信息: {"temperature": "°C", "humidity": "%"}

# 2. 创建传感器
传感器ID: DHT11-WEMOS-001  # 与固件中的 SENSOR_ID 一致
传感器名称: 客厅温湿度传感器
传感器类型: DHT11温湿度传感器
位置: 客厅-东侧
数据引脚: D5
采集间隔: 60
```

### 或使用 Django Shell

```python
python manage.py shell

from sensors.models import SensorType, Sensor

# 创建传感器类型
sensor_type, created = SensorType.objects.get_or_create(
    name="DHT11温湿度传感器",
    defaults={
        'data_fields': {'temperature': 'float', 'humidity': 'float'},
        'unit_info': {'temperature': '°C', 'humidity': '%'},
        'description': 'DHT11数字温湿度传感器'
    }
)

# 创建传感器
sensor = Sensor.objects.create(
    sensor_id="DHT11-WEMOS-001",  # 与固件保持一致
    name="客厅温湿度传感器",
    sensor_type=sensor_type,
    location="客厅-东侧",
    data_pin="D5",
    sampling_interval=60,
    hardware_version="WEMOS_D1_R2",
    firmware_version="1.0.0"
)

print(f"传感器创建成功: {sensor}")
print(f"数据主题: {sensor.mqtt_topic_data}")
print(f"控制主题: {sensor.mqtt_topic_control}")
```

## ✅ 验证测试

### 1. 检查串口输出

应该看到类似以下内容：

```
========================================
  DHT11 温湿度传感器 - Model版本 v2
========================================
传感器ID: DHT11-WEMOS-001
固件版本: 1.0.0
硬件版本: WEMOS_D1_R2

连接WiFi: YOUR_WIFI_SSID
..........
✓ WiFi连接成功
IP地址: 192.168.1.100
MAC地址: AA:BB:CC:DD:EE:FF
✓ MQTT配置完成
数据主题: iot/sensors/DHT11-WEMOS-001/data
控制主题: iot/sensors/DHT11-WEMOS-001/control
✓ NTP时间同步完成
当前时间: 14:30:25
========================================
系统启动完成，开始数据采集...
========================================

连接MQTT服务器...✓ MQTT连接成功
✓ 已订阅: iot/sensors/DHT11-WEMOS-001/control
✓ 状态更新: online
✓ 数据发送成功
温度: 25.5°C | 湿度: 60.0% | 质量分数: 100
发送内容: {"sensor_id":"DHT11-WEMOS-001","data":{"temperature":25.5,"humidity":60.0},...}
```

### 2. 检查 MQTT 消息

使用 MQTT 客户端（如 MQTT Explorer）订阅主题：
```
iot/sensors/DHT11-WEMOS-001/data
iot/sensors/DHT11-WEMOS-001/status
```

应该能看到定期的数据消息。

### 3. 测试控制命令

发送以下消息到控制主题 `iot/sensors/DHT11-WEMOS-001/control`：

```json
{"command": "get_status"}
```

应该立即收到状态上报消息。

### 4. 检查 Django 数据库

在 Django Admin 中查看：
- 传感器状态应该显示"在线"
- 应该能看到传感器数据记录
- 最新数据应该有值

## 🔧 测试控制功能

### 调整采集间隔为 120 秒

发送消息到 `iot/sensors/DHT11-WEMOS-001/control`：

```json
{
  "command": "set_interval",
  "interval": 120
}
```

串口应该输出：
```
收到控制命令 [iot/sensors/DHT11-WEMOS-001/control]: ...
✓ 采集间隔已更新为: 120 秒
✓ 状态更新: interval_updated
```

### 禁用传感器

```json
{"command": "disable"}
```

传感器将停止数据采集，但仍保持在线。

### 重新启用

```json
{"command": "enable"}
```

## 🐛 常见问题排查

### 问题 1：无法连接 WiFi

**症状**：串口显示 "WiFi连接失败"

**解决方法**：
1. 检查 WiFi 名称和密码是否正确
2. 确认 WiFi 是 2.4GHz（ESP8266 不支持 5GHz）
3. 检查 WiFi 信号强度
4. 尝试靠近路由器

### 问题 2：MQTT 连接失败

**症状**：串口显示 "连接失败, rc=-2"

**解决方法**：
1. 检查 MQTT 服务器地址和端口
2. 确认服务器在运行
3. 检查防火墙设置
4. 如果需要认证，填写用户名密码

### 问题 3：传感器读取失败

**症状**：串口显示 "DHT传感器读取失败"

**解决方法**：
1. 检查接线是否正确
2. 确认传感器供电正常（3.3V）
3. 检查数据引脚是否正确（D5）
4. 尝试更换传感器（可能损坏）

### 问题 4：时间戳不准确

**症状**：数据的时间戳错误

**解决方法**：
1. 检查 NTP 服务器是否可访问
2. 等待 NTP 同步（启动后需要几秒）
3. 确认时区设置正确（UTC_OFFSET = 28800 for UTC+8）
4. 尝试更换 NTP 服务器

### 问题 5：数据质量分数低

**症状**：quality_score 低于 80

**解决方法**：
1. 检查传感器连接稳定性
2. 改善供电质量（使用电源适配器而非电脑 USB）
3. 远离电磁干扰源
4. 增加采集间隔（DHT11 最小 2 秒）

## 📊 查看完整日志

如果遇到问题，完整的串口日志能帮助诊断：

1. 打开串口监视器（波特率 115200）
2. 记录启动过程的所有输出
3. 包括错误码（如 rc=-2）
4. 记录失败前的最后几条消息

## 🎯 下一步

设备正常运行后，可以：

1. **批量部署**：为多个设备设置不同的 sensor_id
2. **配置告警**：在 Django 后端设置温湿度告警阈值
3. **数据可视化**：查看历史数据曲线
4. **远程运维**：使用控制命令调整设备参数

## 📚 更多文档

- 📖 [详细功能说明](README_V2.md)
- 🔄 [版本对比](VERSION_COMPARISON.md)
- 🎓 [Django Model 文档](../models.py)

## 💡 技术支持

遇到问题？检查以下资源：

1. 查看串口日志（115200 波特率）
2. 阅读完整文档（README_V2.md）
3. 检查硬件连接
4. 验证网络连接
5. 确认后端配置

---

**祝你使用愉快！** 🎉

如果成功运行，你应该能在 Django Admin 中看到实时的温湿度数据了！
