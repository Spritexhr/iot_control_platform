# DHT11 温湿度传感器 v2.0 - Model 版本

## 📋 概述

这是一个完全符合 Django Sensor Model 设计的 Arduino 固件，用于 Wemos D1 + DHT11 温湿度传感器。

## 🎯 主要特性

### 1. 完全符合 Model 设计
- ✅ MQTT 主题格式：`iot/sensors/{sensor_id}/data`
- ✅ 数据格式匹配 `SensorData` Model
- ✅ 支持所有 Model 定义的字段

### 2. 核心功能
- 🌡️ DHT11 温湿度数据采集
- 📡 MQTT 数据上报
- 🕐 NTP 时间同步（准确时间戳）
- 📊 数据质量评估
- 🎛️ 远程控制支持
- 📈 运行状态监控

## 🔧 硬件配置

### 接线说明
```
DHT11          Wemos D1
-----          --------
VCC      →     3.3V
GND      →     GND
DATA     →     D5 (GPIO14)
```

### 所需库文件
在 Arduino IDE 中安装以下库：
- `DHT sensor library` (by Adafruit)
- `Adafruit Unified Sensor`
- `PubSubClient` (by Nick O'Leary)
- `NTPClient` (by Fabrice Weinberg)
- `ArduinoJson` (by Benoit Blanchon) - 版本 6.x

## ⚙️ 配置说明

### 必须修改的配置

```cpp
// 1. WiFi 配置
const char* WIFI_SSID = "你的WiFi名称";
const char* WIFI_PASSWORD = "你的WiFi密码";

// 2. MQTT 服务器
const char* MQTT_SERVER = "你的MQTT服务器IP";
const int MQTT_PORT = 1883;

// 3. 传感器标识（每个设备必须唯一）
const char* SENSOR_ID = "DHT11-WEMOS-001";
const char* SENSOR_NAME = "客厅温湿度传感器";
const char* SENSOR_LOCATION = "客厅-东侧";
```

### 可选配置

```cpp
// NTP 服务器（默认：阿里云）
const char* NTP_SERVER = "ntp.aliyun.com";

// 时区偏移（默认：UTC+8）
const long UTC_OFFSET = 28800;

// 采集间隔（默认：60秒，可通过MQTT动态调整）
int samplingInterval = 60;
```

## 📤 数据上报格式

### 数据主题：`iot/sensors/{sensor_id}/data`

```json
{
  "sensor_id": "DHT11-WEMOS-001",
  "data": {
    "temperature": 25.5,
    "humidity": 60.0
  },
  "timestamp": 1706515200,
  "quality_score": 95,
  "is_valid": true,
  "mac_address": "AA:BB:CC:DD:EE:FF",
  "firmware_version": "1.0.0",
  "hardware_version": "WEMOS_D1_R2",
  "rssi": -45
}
```

### 状态主题：`iot/sensors/{sensor_id}/status`

```json
{
  "sensor_id": "DHT11-WEMOS-001",
  "event": "online",
  "timestamp": 1706515200,
  "status": "online",
  "is_enabled": true,
  "sampling_interval": 60,
  "statistics": {
    "total_readings": 100,
    "valid_readings": 98,
    "quality_score": 98,
    "consecutive_failures": 0
  },
  "system": {
    "uptime": 3600,
    "free_heap": 25000,
    "rssi": -45,
    "ip": "192.168.1.100"
  }
}
```

## 🎛️ 控制命令

### 控制主题：`iot/sensors/{sensor_id}/control`

### 1. 设置采集间隔
```json
{
  "command": "set_interval",
  "interval": 120
}
```
- `interval`: 10-3600 秒

### 2. 启用传感器
```json
{
  "command": "enable"
}
```

### 3. 禁用传感器
```json
{
  "command": "disable"
}
```

### 4. 获取状态
```json
{
  "command": "get_status"
}
```

### 5. 重置统计数据
```json
{
  "command": "reset_stats"
}
```

## 📊 数据质量评估

系统自动计算数据质量分数（0-100）：

- **基础分数**：基于数据采集成功率
- **惩罚机制**：连续失败次数 × 10
- **范围验证**：
  - 温度：-20°C ~ 60°C
  - 湿度：0% ~ 100%

## 🔄 与 Django Model 的对应关系

| Arduino 字段 | Django Model 字段 | 说明 |
|-------------|------------------|------|
| `sensor_id` | `Sensor.sensor_id` | 传感器唯一标识 |
| `data.temperature` | `SensorData.temperature` | 温度值 |
| `data.humidity` | `SensorData.humidity` | 湿度值 |
| `timestamp` | `SensorData.timestamp` | 数据时间戳 |
| `quality_score` | `SensorData.quality_score` | 数据质量分数 |
| `is_valid` | `SensorData.is_valid` | 数据有效性 |
| `mac_address` | `Sensor.mac_address` | MAC地址 |
| `firmware_version` | `Sensor.firmware_version` | 固件版本 |

## 📝 Django 后端配置

### 1. 创建 Sensor 记录

```python
from sensors.models import SensorType, Sensor

# 创建传感器类型
sensor_type = SensorType.objects.create(
    name="DHT11温湿度传感器",
    data_fields={
        'temperature': 'float',
        'humidity': 'float'
    },
    unit_info={
        'temperature': '°C',
        'humidity': '%'
    }
)

# 创建传感器
sensor = Sensor.objects.create(
    sensor_id="DHT11-WEMOS-001",
    name="客厅温湿度传感器",
    sensor_type=sensor_type,
    location="客厅-东侧",
    data_pin="D5",
    sampling_interval=60,
    hardware_version="WEMOS_D1_R2",
    firmware_version="1.0.0"
)
```

### 2. MQTT 消息处理

后端应该订阅 `iot/sensors/+/data` 主题，并按以下方式处理：

```python
def handle_sensor_data(sensor_id, payload):
    try:
        sensor = Sensor.objects.get(sensor_id=sensor_id)
        
        # 创建数据记录
        sensor_data = SensorData.objects.create(
            sensor=sensor,
            data=payload['data'],
            quality_score=payload.get('quality_score', 100),
            is_valid=payload.get('is_valid', True),
            timestamp=datetime.fromtimestamp(payload['timestamp'])
        )
        
        # Model 会自动更新 sensor.latest_data
        
    except Sensor.DoesNotExist:
        logger.warning(f"未知传感器: {sensor_id}")
```

## 🐛 调试信息

串口输出（115200波特率）包含：
- ✅ 初始化信息
- 📡 网络连接状态
- 📊 数据读取和发送日志
- ⚠️ 错误和警告信息
- 📈 质量统计信息

## 🔍 常见问题

### 1. 传感器读取失败
- 检查接线是否正确
- 确认 DHT11 供电正常
- 增加延迟时间（DHT11 最小间隔 2 秒）

### 2. MQTT 连接失败
- 检查网络连接
- 确认 MQTT 服务器地址和端口
- 查看是否需要用户名/密码认证

### 3. 时间戳不准确
- 检查 NTP 服务器是否可访问
- 确认时区设置正确
- 等待 NTP 同步完成（初次启动需要几秒钟）

### 4. 数据质量分数低
- 检查传感器连接稳定性
- 改善供电质量
- 远离电磁干扰源

## 📚 版本更新

### v2.0.0 (2024-01)
- ✨ 完全重构，符合 Django Model 设计
- ✨ 添加 NTP 时间同步
- ✨ 实现数据质量评估
- ✨ 支持远程控制命令
- ✨ 添加状态上报功能
- 🐛 修复数据验证问题

### v1.0.0
- 基础版本（参考 temp_humi_upload.ino）

## 📄 许可证

本项目用于毕业设计学习使用。

## 👤 作者

毕业设计项目 - IoT 控制平台

---

**注意**：首次使用前请确保在 Django 后端创建对应的 Sensor 记录，否则数据将无法正确入库。
