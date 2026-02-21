# Django 数据模型设计文档

本文档描述物联网控制平台（IoT Control Platform）的 Django 数据模型设计，涵盖设备管理、传感器管理和自动化规则三大模块。

---

## 一、架构概览

| 应用 (App) | 职责 | 核心模型 |
|-----------|------|---------|
| `devices` | 输出器/执行器（如 LED、舵机、继电器）管理 | DeviceType, Device, DeviceData |
| `sensors` | 输入器/传感器（如 DHT11、DHT22）管理 | SensorType, Sensor, SensorStatusCollection, SensorData |
| `automation` | 自动化规则与脚本执行 | AutomationRule |

三个模块通过 `device_id` 在 `AutomationRule.device_list` 中与 `devices.Device`、`sensors.Sensor` 进行逻辑关联。

---

## 二、设备管理模块 (devices)

### 2.1 DeviceType（设备类型）

定义不同类型的输出器（LED、舵机、继电器等），存储类型级别的固定参数和配置。

| 字段 | 类型 | 约束 | 说明 |
|-----|------|-----|------|
| `DeviceType_id` | CharField(50) | unique, db_index | 设备类型唯一ID，如 LED-01、FAN-01 |
| `name` | CharField(50) | unique | 设备类型名称，如 LED灯、智能风扇 |
| `description` | TextField | blank | 类型描述 |
| `state_fields` | JSONField | default=list | 设备上报状态需提取的字段，如 `["power_state","brightness"]` |
| `config_parameters` | JSONField | default=list | 可配置参数名称，如 `["heartbeat_interval"]` |
| `commands` | JSONField | default=dict | 可用命令定义，含 `mqtt_message`、`description`、`params` |
| `created_at` | DateTimeField | auto_now_add | 创建时间 |

**commands 示例：**
```json
{
  "turn_on": {"mqtt_message": {"command": "power_on"}, "description": "打开设备", "params": []},
  "set_brightness": {"mqtt_message": {"command": "set_brightness", "value": "{val}"}, "description": "设置亮度", "params": ["val"]}
}
```

---

### 2.2 Device（设备实例）

输出器/执行器的实例，通过外键关联 `DeviceType`。

| 字段 | 类型 | 约束 | 说明 |
|-----|------|-----|------|
| `device_id` | CharField(50) | unique, db_index | 设备唯一ID |
| `name` | CharField(100) | - | 设备名称 |
| `description` | TextField | blank | 设备描述 |
| `location` | CharField(200) | blank | 设备位置 |
| `mqtt_topic_data` | CharField(200) | blank | 状态主题，默认 `iot/devices/{device_id}/status` |
| `mqtt_topic_control` | CharField(200) | blank | 控制主题，默认 `iot/devices/{device_id}/control` |
| `is_online` | BooleanField | default=False, db_index | 是否在线 |
| `last_seen` | DateTimeField | null, blank | 最后上报时间 |
| `created_at` | DateTimeField | auto_now_add | 创建时间 |
| `updated_at` | DateTimeField | auto_now | 更新时间 |
| `device_type` | ForeignKey | DeviceType, PROTECT | 设备类型 |

**常用方法：**
- `check_online_status()`：基于心跳间隔 3 倍超时判断离线
- `update_heartbeat()`：更新心跳时间并置为在线
- `get_data_count(hours)`：获取指定时间内的数据记录数

---

### 2.3 DeviceData（设备数据记录）

存储设备上报的状态、命令执行及操作日志。

| 字段 | 类型 | 约束 | 说明 |
|-----|------|-----|------|
| `device` | ForeignKey | Device, CASCADE | 设备 |
| `data` | JSONField | - | 数据内容，如 `{"power_state": true, "brightness": 80}` |
| `timestamp` | DateTimeField | db_index | 数据时间 |
| `received_at` | DateTimeField | auto_now_add | 接收时间 |

**索引：** `(device, -timestamp)`、`(timestamp)`

保存时会自动更新设备的 `last_seen` 和 `is_online`。

---

## 三、传感器管理模块 (sensors)

### 3.1 SensorType（传感器类型）

定义不同类型传感器（如 DHT11、DHT22、BMP180），存储类型级参数和配置。

| 字段 | 类型 | 约束 | 说明 |
|-----|------|-----|------|
| `SensorType_id` | CharField(50) | unique, db_index | 传感器类型唯一ID |
| `name` | CharField(50) | unique | 传感器类型名称 |
| `description` | TextField | blank | 类型描述 |
| `data_fields` | JSONField | default=list | 数据字段列表，如 `["temperature","humidity"]` |
| `config_parameters` | JSONField | default=list | 配置参数，如 `["samplingInterval","is_enabled"]` |
| `commands` | JSONField | default=list | 可用命令列表，结构同 DeviceType.commands |
| `created_at` | DateTimeField | auto_now_add | 创建时间 |

---

### 3.2 Sensor（传感器实例）

输入器实例，关联 `SensorType`，结构与 `Device` 类似。

| 字段 | 类型 | 约束 | 说明 |
|-----|------|-----|------|
| `sensor_id` | CharField(50) | unique, db_index | 传感器唯一ID |
| `name` | CharField(100) | - | 传感器名称 |
| `description` | TextField | blank | 传感器描述 |
| `location` | CharField(200) | blank | 传感器位置 |
| `mqtt_topic_data` | CharField(200) | blank | 数据主题，默认 `iot/sensors/{sensor_id}/data` |
| `mqtt_topic_control` | CharField(200) | blank | 控制主题，默认 `iot/sensors/{sensor_id}/control` |
| `is_online` | BooleanField | default=False, db_index | 是否在线 |
| `last_seen` | DateTimeField | null, blank | 最后上报时间 |
| `created_at` | DateTimeField | auto_now_add | 创建时间 |
| `updated_at` | DateTimeField | auto_now | 更新时间 |
| `sensor_type` | ForeignKey | SensorType, PROTECT | 传感器类型 |

**特性：**
- `computed_is_online`：3 分钟内有过上报视为在线
- `update_last_seen(timestamp)`：更新最后上报时间

---

### 3.3 SensorStatusCollection（传感器状态采集记录）

存储传感器上报的状态类数据（如在线/离线、参数变更）。

| 字段 | 类型 | 约束 | 说明 |
|-----|------|-----|------|
| `sensor` | ForeignKey | Sensor, CASCADE | 传感器 |
| `data` | JSONField | - | 状态数据，如 `{"is_enabled": true, "samplingInterval": 120}` |
| `timestamp` | DateTimeField | db_index | 数据时间 |
| `event_name` | CharField(100) | blank | 事件名称，如 online、offline、interval_updated |
| `received_at` | DateTimeField | auto_now_add | 接收时间 |

**索引：** `(sensor, -timestamp)`、`(timestamp)`

---

### 3.4 SensorData（传感器数据记录）

存储传感器上报的采集数据（如温湿度、气压）。

| 字段 | 类型 | 约束 | 说明 |
|-----|------|-----|------|
| `sensor` | ForeignKey | Sensor, CASCADE | 传感器 |
| `data` | JSONField | - | 原始数据，如 `{"temperature": 25.5, "humidity": 60.0}` |
| `timestamp` | DateTimeField | db_index | 数据时间 |
| `received_at` | DateTimeField | auto_now_add | 接收时间 |

**索引：** `(sensor, -timestamp)`、`(timestamp)`

`SensorStatusCollection` 与 `SensorData` 保存时都会调用 `sensor.update_last_seen()`。

---

## 四、自动化模块 (automation)

### 4.1 AutomationRule（自动化规则）

通过 Python 脚本实现自动化逻辑，可访问关联的 Sensor 和 Device 数据。

| 字段 | 类型 | 约束 | 说明 |
|-----|------|-----|------|
| `name` | CharField(100) | - | 规则名称 |
| `description` | TextField | blank | 规则描述 |
| `script_id` | CharField(50) | blank, unique | 脚本唯一ID，用于 `execute_by_script_id()` 调用 |
| `script` | TextField | blank | Python 脚本，使用 `from engine import sensors, devices` 风格 |
| `device_list` | JSONField | default=list | 关联设备与传感器列表 |
| `is_launched` | BooleanField | default=False | 是否启动轮询 |
| `poll_interval` | PositiveIntegerField | default=30 | 轮询间隔（秒） |
| `process_status` | CharField(20) | choices | 进程状态 |
| `error_message` | TextField | blank | 错误信息（error_stopped 时） |
| `created_at` | DateTimeField | auto_now_add | 创建时间 |
| `updated_at` | DateTimeField | auto_now | 更新时间 |

**process_status 取值：**

| 值 | 说明 |
|----|------|
| idle | 未启动 |
| running | 正在运行 |
| stopped_by_user | 由用户停止 |
| error_stopped | 由错误停止 |

**device_list 示例：**
```json
[
  {"device_id": "DHT11-WEMOS-001", "device_type": "Sensor", "name": "温湿度传感器"},
  {"device_id": "SG_80_01", "device_type": "Device", "name": "LED灯"}
]
```

**数据来源：**
- Sensor：`sensor.data_records`（SensorData）最新一条 `data`
- Device：`device.data_records`（DeviceData）最新一条 `data`
- 设备控制通过 `DeviceType.commands` 定义的命令发送

**常用方法：**
- `execute()`：执行脚本
- `execute_by_script_id(script_id)`：按脚本 ID 执行规则
- `get_device_count()`：关联设备数量

---

## 五、模型关系图（文字版）

```
┌─────────────────┐
│   DeviceType    │
│ (设备类型)       │
└────────┬────────┘
         │ 1:N
         ▼
┌─────────────────┐    1:N    ┌─────────────────┐
│     Device      │──────────►│   DeviceData    │
│ (输出器/执行器)   │           │ (设备数据记录)   │
└─────────────────┘           └─────────────────┘

┌─────────────────┐
│   SensorType    │
│ (传感器类型)     │
└────────┬────────┘
         │ 1:N
         ▼
┌─────────────────┐    1:N    ┌──────────────────────┐
│     Sensor      │──────────►│ SensorStatusCollection│
│ (输入器/传感器)   │           │ (传感器状态记录)       │
└─────────────────┘           └──────────────────────┘
         │
         │ 1:N
         ▼
┌─────────────────┐
│   SensorData    │
│ (传感器数据记录)  │
└─────────────────┘

┌─────────────────┐
│ AutomationRule  │  device_list (JSON) 逻辑引用 device_id
│ (自动化规则)     │  ← 对应 devices.Device 或 sensors.Sensor
└─────────────────┘
```

---

## 六、设计要点

1. **类型-实例分层**：`DeviceType`/`SensorType` 定义类型，`Device`/`Sensor` 为实例，类型删除用 `PROTECT` 防止误删。
2. **MQTT 主题约定**：设备 `iot/devices/{device_id}/*`，传感器 `iot/sensors/{sensor_id}/*`。
3. **在线判定**：基于 `last_seen`，设备按心跳 3 倍超时，传感器按 3 分钟内有过上报。
4. **JSON 存储**：`data`、`commands`、`device_list` 等使用 JSONField，便于扩展字段。
5. **自动化与设备解耦**：`AutomationRule` 通过 `device_list` 中的 `device_id` 与 `Device`/`Sensor` 关联，无外键，方便跨模块引用。
