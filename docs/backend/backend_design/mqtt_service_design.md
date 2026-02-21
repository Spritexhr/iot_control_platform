# MQTT 服务设计文档

本文档描述物联网控制平台的 MQTT 服务架构，涵盖 `mqtt_service`、各 `send_service`（命令下发）与 `handler`（消息接收处理）之间的关系与协作方式。

---

## 一、架构概览

| 层级 | 组件 | 职责 |
|-----|------|------|
| **传输核心** | `mqtt_service` | MQTT 连接管理、主题订阅、消息收发、消息路由 |
| **上行（接收）** | `*_handlers` | 解析 MQTT 消息、写入数据库、可选校验 check_code |
| **下行（发送）** | `*_command_send_service` | 按模型定义构造并下发控制命令，可选等待确认 |

```
                    ┌─────────────────────────────────────────────────────────────┐
                    │                     MQTT Broker                              │
                    └─────────────────────────────────────────────────────────────┘
                                          ▲   │
                         publish()        │   │  on_message
                                          │   ▼
┌──────────────────────┐         ┌──────────────────────┐         ┌──────────────────────┐
│ send_service         │────────►│   mqtt_service       │◄────────│ handler              │
│ (命令下发)            │ 调用     │   (传输与路由)        │ 调用     │ (消息接收与处理)       │
│                      │ publish  │                      │ handler │                      │
│ - SensorCommandSend  │         │ - 主题匹配与分发       │         │ - sensor_upload_data  │
│ - DeviceCommandSend  │         │ - handlers 注册表      │         │ - sensor_upload_status│
└──────────────────────┘         └──────────────────────┘         │ - device_upload_status │
         │                                    │                    └──────────────────────┘
         │ 可选：等待确认                      │ 校验 check_code 时
         │ send_xxx_with_make_sure            │ 回调 verify_xxx_check_code
         └────────────────────────────────────┘
```

---

## 二、mqtt_service（MQTT 传输核心）

### 2.1 职责

- **连接管理**：连接/断开 MQTT Broker，维护 `is_connected` 状态
- **主题订阅**：支持通配符 `+`、`#`，连接前订阅请求缓存至 `pending_subscriptions`，连接成功后自动执行
- **消息发布**：`publish(topic, payload, qos)`，payload 自动序列化为 JSON
- **消息路由**：收到消息后根据主题模式匹配 `handlers` 中的处理器并调用

### 2.2 处理器注册机制

```python
# 主题模式 -> 处理函数
handlers: Dict[str, Callable]  # 如 'iot/sensors/+/data' -> handle_mqtt_data_message
```

- `register_handler(topic_pattern, handler)`：注册处理器，`handler(topic, payload)`
- `setup_sensor_data_handler()` / `setup_sensor_status_handler()` / `setup_device_status_handler()`：快速注册并订阅对应主题

### 2.3 主题与处理器对应关系

| 主题模式 | 处理器 | 说明 |
|---------|--------|------|
| `iot/sensors/+/data` | `handle_mqtt_data_message` | 传感器数据上报 → SensorData |
| `iot/sensors/+/status` | `handle_mqtt_status_message` | 传感器状态上报 → SensorStatusCollection |
| `iot/devices/+/status` | `handle_mqtt_device_status_message` | 设备状态上报 → DeviceData |

### 2.4 消息路由流程

```
_on_message(topic, payload)
    → JSON 解析
    → _find_handler(topic)  # 按通配符匹配
    → handler(topic, payload)
```

---

## 三、Handler（消息接收与处理）

### 3.1 设计理念

- Handler 只负责**解析与持久化**，不持有 MQTT 客户端
- 由 mqtt_service 统一调用，接口统一为 `handler(topic: str, payload: dict) -> bool`
- 与模型一一对应：data → SensorData，status → SensorStatusCollection / DeviceData

### 3.2 传感器数据 Handler：`sensor_upload_data_handlers`

| 项目 | 说明 |
|-----|------|
| 主题 | `iot/sensors/+/data` |
| 消息格式 | `{sensor_id, data, timestamp}` |
| 目标模型 | `SensorData` |
| 逻辑 | 校验 → 查 Sensor → 提取 data → 保存 |

### 3.3 传感器状态 Handler：`sensor_upload_status_handlers`

| 项目 | 说明 |
|-----|------|
| 主题 | `iot/sensors/+/status` |
| 消息格式 | `{sensor_id, event, status, check_code?, timestamp}` |
| 目标模型 | `SensorStatusCollection` |
| 特殊逻辑 | 若 payload 含 `check_code`，调用 `verify_sensor_status_check_code` 供 send_service 确认命令是否被执行 |

### 3.4 设备状态 Handler：`device_upload_status_handlers`

| 项目 | 说明 |
|-----|------|
| 主题 | `iot/devices/+/status` |
| 消息格式 | `{device_id, event, status, check_code?, timestamp}` |
| 目标模型 | `DeviceData` |
| 特殊逻辑 | 若含 `check_code`，调用 `verify_device_status_check_code` |

---

## 四、Send Service（命令下发）

### 4.1 设计理念

- Send Service 持有 `mqtt_service` 引用，通过 `publish` 下发命令
- 命令内容来自 `SensorType.commands` / `DeviceType.commands` 中的 `mqtt_message` 模板
- 支持占位符替换（如 `{val}`）和可选 `check_code` 确认流程

### 4.2 SensorCommandSendService / DeviceCommandSendService

| 方法 | 说明 |
|-----|------|
| `send_command(id, payload)` | 直接发布原始 payload 到控制主题 |
| `send_custom_command(id, command_name, params)` | 按类型定义构造 mqtt_message 并发送 |
| `send_custom_command_with_make_sure(...)` | 注入 check_code，发送后等待对应 status handler 回传确认 |

### 4.3 依赖关系

```
send_service 构造 mqtt_message
    → mqtt_service.publish(topic_control, payload)
    → 设备/传感器执行后上报 status（含 check_code）
    → mqtt_service 路由到 status handler
    → handler 调用 verify_xxx_check_code
    → send_service 中 Event.set()，wait 返回
```

**前提**：使用 `send_custom_command_with_make_sure` 前需已调用 `mqtt_service.setup_sensor_status_handler()` 或 `mqtt_service.setup_device_status_handler()`。

---

## 五、三者关系总结

### 5.1 调用方向

```
mqtt_service ◄──── send_service     (send_service 调用 mqtt_service.publish)
     │
     └──────────► handler           (mqtt_service 收到消息后调用 handler)

handler ───────► send_service       (status handler 调用 verify_xxx_check_code，用于确认流程)
```

### 5.2 职责划分

| 组件 | 是否持有 mqtt_service | 是否连接 MQTT | 职责边界 |
|-----|----------------------|--------------|---------|
| mqtt_service | - | ✓ | 连接、订阅、发布、路由 |
| handler | ✗ | ✗ | 解析 payload、写库、校验 check_code |
| send_service | ✓ | ✗ | 查模型、构造命令、调用 publish、等待确认 |

### 5.3 数据流

**下行（接收）**

```
MQTT Broker → mqtt_service._on_message
    → _find_handler → handler(topic, payload)
    → 验证 → 查 Model → 入库（SensorData / SensorStatusCollection / DeviceData）
    → [可选] verify_xxx_check_code → 唤醒 send_service 的 Event
```

**上行（发送）**

```
业务 / API / 自动化
    → send_service.send_command / send_custom_command / send_custom_command_with_make_sure
    → mqtt_service.publish(mqtt_topic_control, payload)
    → MQTT Broker → 设备/传感器
```

---

## 六、初始化与使用示例

### 6.1 服务启动时

```python
from services import mqtt_service, sensor_command_send_service, device_command_send_service

mqtt_service.connect()
mqtt_service.setup_sensor_data_handler()
mqtt_service.setup_sensor_status_handler()
mqtt_service.setup_device_status_handler()

# 注入 mqtt_service 到 send_service（若未在 __init__ 传入）
sensor_command_send_service.set_mqtt_service(mqtt_service)
device_command_send_service.set_mqtt_service(mqtt_service)
```

### 6.2 命令下发示例

```python
# 简单发送
sensor_command_send_service.send_custom_command("DHT11-WEMOS-001", "turn_on")
device_command_send_service.send_custom_command("SG_80_01", "set_brightness", {"val": 80})

# 带确认发送（需先 setup_sensor_status_handler / setup_device_status_handler）
success = sensor_command_send_service.send_custom_command_with_make_sure(
    "DHT11-WEMOS-001", "set_interval", {"val": 60}, time_out=3
)
```

---

## 七、自启动设计（sensors/apps.py）

MQTT 服务通过 `sensors.apps.SensorsConfig.ready()` 在应用启动时自动连接并初始化，无需在 `runserver` 或 `shell` 中手动调用。

### 7.1 触发时机

`ready()` 在 Django 完成应用加载后执行，逻辑流程：

```
SensorsConfig.ready()
    → _should_start_mqtt()  # 判断当前命令是否需启动 MQTT
    → _start_mqtt_service()  # 若未启动过则执行
```

### 7.2 启动条件（_should_start_mqtt）

| 命令 | 是否启动 | 说明 |
|-----|---------|------|
| `runserver` | 仅子进程 | `RUN_MAIN=true` 时启动，避免 reloader 父进程重复连接 |
| `gunicorn` / `uwsgi` | ✓ | Docker 等生产环境需启动 MQTT |
| `shell` / `runscript` | ✓ | 交互环境或脚本中直接使用 MQTT |
| `test` / `migrate` / `makemigrations` | ✗ | 不启动，避免干扰测试和迁移 |

### 7.3 初始化步骤（_start_mqtt_service）

| 步骤 | 调用 | 说明 |
|-----|------|------|
| 1 | `mqtt_service.connect(timeout=5)` | 连接 MQTT Broker |
| 2 | `sensor_command_send_service.set_mqtt_service(mqtt_service)` | 绑定传感器命令服务 |
| 3 | `device_command_send_service.set_mqtt_service(mqtt_service)` | 绑定设备命令服务 |
| 4 | `mqtt_service.setup_sensor_data_handler()` | 注册并订阅 `iot/sensors/+/data` |
| 5 | `mqtt_service.setup_sensor_status_handler()` | 注册并订阅 `iot/sensors/+/status` |
| 6 | `mqtt_service.setup_device_status_handler()` | 注册并订阅 `iot/devices/+/status` |
| 7 | `SensorsConfig.mqtt_service_started = True` | 标记已启动，避免重复 |

### 7.4 防重复机制

类变量 `mqtt_service_started` 确保同一进程内只启动一次。若需重新连接（如调试），需先调用 `mqtt_service.stop()` 并重置该标志，或重启进程。

---

## 八、文件结构

```
sensors/
└── apps.py                         # SensorsConfig，负责 MQTT 自启动

services/
├── mqtt_service.py                    # MQTT 传输核心
├── sensors_service/
│   ├── sensor_upload_data_handlers.py  # 传感器数据 handler
│   ├── sensor_upload_status_handlers.py# 传感器状态 handler
│   └── sensor_command_send_service.py  # 传感器命令下发
└── devices_service/
    ├── device_upload_status_handlers.py# 设备状态 handler
    └── device_command_send_service.py # 设备命令下发
```
