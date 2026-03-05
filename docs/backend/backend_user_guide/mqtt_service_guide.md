# MQTT 服务使用指南（Django Shell）

本文档介绍如何在 Django Shell 中使用 MQTT 服务，包括传感器/设备命令发送、手动初始化及 mqtt_service 高级用法。架构说明见 [mqtt_service_design.md](../backend_design/mqtt_service_design.md)。

---

## 一、概述与前置条件

### 1.1 架构简述

| 组件 | 职责 |
|-----|------|
| `mqtt_service` | MQTT 连接、订阅、发布、消息路由 |
| `sensor_command_send_service` | 向传感器发送控制命令 |
| `device_command_send_service` | 向设备（执行器）发送控制命令 |
| handlers | 接收 MQTT 消息并写入数据库（由 mqtt_service 自动调用） |

### 1.2 前置条件

- MQTT Broker 已启动（如 EMQX、Mosquitto）
- MQTT 配置：优先从 `platform_settings` 读取，回退到环境变量 `MQTT_BROKER`、`MQTT_PORT` 等。详见 [platform_settings_guide.md](./platform_settings_guide.md)
- **传感器**：已创建 `SensorType` 和 `Sensor`，`SensorType.commands` 中定义好命令
- **设备**：已创建 `DeviceType` 和 `Device`，`DeviceType.commands` 中定义好命令

### 1.3 自动初始化

`manage.py runserver`、`manage.py shell`、`runscript` 等命令启动时，`sensors.apps.SensorsConfig.ready()` 会自动执行 MQTT 初始化（详见 [mqtt_service_design.md 自启动设计](../backend_design/mqtt_service_design.md#七自启动设计sensorsappspy)）：

- 连接 MQTT Broker
- 将 `sensor_command_send_service`、`device_command_send_service` 绑定到 mqtt_service
- 注册并订阅传感器数据、传感器状态、设备状态主题

进入 Shell 后可直接发送命令，无需手动初始化。`test`、`migrate`、`makemigrations` 不启动 MQTT。

---

## 二、标准用法：发送传感器控制命令

### 2.1 进入 Shell 并导入

```bash
python manage.py shell
```

```python
from services import sensor_command_send_service, mqtt_service
from sensors.models import Sensor, SensorType

# 或使用完整路径
# from services.sensors_service.sensor_command_send_service import sensor_command_send_service
```

### 2.2 查看可用命令

```python
target_sensor = Sensor.objects.get(sensor_id='DHT11-WEMOS-001')  # 替换为实际 sensor_id
available = sensor_command_send_service.show_sensor_control_commands(target_sensor)

for cmd_name, info in available.items():
    params = info.get('params', [])
    desc = info.get('description', '')
    print(f"  {cmd_name}: {desc}  (参数: {params})")
```

### 2.3 发送无参数命令

```python
success = sensor_command_send_service.send_custom_command(
    sensor_id='DHT11-WEMOS-001',
    command_name='enable'  # 需在 SensorType.commands 中定义
)
# 返回 True 表示 MQTT 发布成功，不表示设备已执行
```

### 2.4 发送带参数命令

```python
success = sensor_command_send_service.send_custom_command(
    sensor_id='DHT11-WEMOS-001',
    command_name='set_interval',
    params={'val': 120}  # 参数名需与 commands 中 params 一致
)
```

### 2.5 发送原始 payload（不按类型定义）

```python
success = sensor_command_send_service.send_command(
    sensor_id='DHT11-WEMOS-001',
    command_payload={'command': 'enable', 'extra': 'value'}
)
```

---

## 三、标准用法：发送设备控制命令

### 3.1 导入

```python
from services import device_command_send_service
from devices.models import Device, DeviceType
```

### 3.2 查看可用命令

```python
target_device = Device.objects.get(device_id='SG_80_01')  # 替换为实际 device_id
available = device_command_send_service.show_device_control_commands(target_device)

for cmd_name, info in available.items():
    print(f"  {cmd_name}: {info.get('description', '')}")
```

### 3.3 发送命令

```python
# 无参数
success = device_command_send_service.send_custom_command(
    device_id='SG_80_01',
    command_name='turn_on'
)

# 带参数
success = device_command_send_service.send_custom_command(
    device_id='SG_80_01',
    command_name='set_brightness',
    params={'val': 80}
)

# 原始 payload
success = device_command_send_service.send_command(
    device_id='SG_80_01',
    command_payload={'command': 'power_on'}
)
```

---

## 四、带确认的命令（send_custom_command_with_make_sure）

当需要确认设备/传感器已正确执行时，使用 `send_custom_command_with_make_sure`。该方法会注入 `check_code`，阻塞等待回传确认，超时则返回 `False`。

### 4.1 前提

- 固件支持在状态上报中回传 `check_code`
- 已注册状态处理器：`mqtt_service.setup_sensor_status_handler()` / `mqtt_service.setup_device_status_handler()`（应用自动启动时已执行）

### 4.2 传感器

```python
# 默认等待 3 秒
success = sensor_command_send_service.send_custom_command_with_make_sure(
    sensor_id='DHT11-WEMOS-001',
    command_name='set_interval',
    params={'val': 60},
    time_out=3
)

# 指定等待 5 秒
success = sensor_command_send_service.send_custom_command_with_make_sure(
    sensor_id='DHT11-WEMOS-001',
    command_name='enable',
    time_out=5
)
```

### 4.3 设备

```python
# 注意：设备使用 time 参数（非 time_out），默认 3 秒
success = device_command_send_service.send_custom_command_with_make_sure(
    device_id='SG_80_01',
    command_name='set_brightness',
    params={'val': 80},
    time=3
)
```

### 4.4 两种发送方式对比

| 方法 | 校验码 | 返回值含义 |
|-----|--------|------------|
| `send_custom_command` | 不包含 | 仅表示 MQTT 是否发布成功 |
| `send_custom_command_with_make_sure` | 自动注入并校验 | 表示设备/传感器是否在限定时间内回传确认 |

---

## 五、手动操作各初始化函数示例

以下示例展示如何**逐步**手动调用自启动时执行的初始化函数，便于调试、覆盖自动行为或理解启动流程。各函数与 `sensors.apps.SensorsConfig._start_mqtt_service` 中调用顺序一致。

### 5.1 导入与检查连接状态

```python
from services import mqtt_service, sensor_command_send_service, device_command_send_service

# 检查当前连接状态
print(mqtt_service.is_connected)  # True/False
```

### 5.2 connect()：连接 MQTT Broker

```python
# 若已有连接，需先 stop 再 connect
if mqtt_service.is_connected:
    mqtt_service.stop()
    import time
    time.sleep(1)

# 连接，超时 10 秒
ok = mqtt_service.connect(timeout=10)
if ok:
    print("✓ MQTT 连接成功")
else:
    print("✗ 连接失败，请检查 MQTT_BROKER、MQTT_PORT 等配置")
```

### 5.3 set_mqtt_service()：绑定命令服务

将 mqtt_service 注入到 send_service，否则 `send_command` 会报「MQTT服务未初始化」：

```python
if mqtt_service.is_connected:
    sensor_command_send_service.set_mqtt_service(mqtt_service)
    device_command_send_service.set_mqtt_service(mqtt_service)
    print("✓ 命令服务已绑定")
```

### 5.4 setup_sensor_data_handler()：传感器数据接收

注册 `handle_mqtt_data_message` 并订阅 `iot/sensors/+/data`，消息会写入 `SensorData`：

```python
mqtt_service.setup_sensor_data_handler()
# 输出：✓ 已注册处理器、✓ 已订阅主题
```

### 5.5 setup_sensor_status_handler()：传感器状态接收

注册并订阅 `iot/sensors/+/status`，消息写入 `SensorStatusCollection`，支持 `check_code` 校验（`send_custom_command_with_make_sure` 依赖此）：

```python
mqtt_service.setup_sensor_status_handler()
```

### 5.6 setup_device_status_handler()：设备状态接收

注册并订阅 `iot/devices/+/status`，消息写入 `DeviceData`：

```python
mqtt_service.setup_device_status_handler()
```

### 5.7 stop()：停止 MQTT 服务

```python
mqtt_service.stop()
# 断开连接并停止网络循环，is_connected 变为 False
```

### 5.8 完整手动初始化脚本（按顺序执行）

```python
import time
from services import mqtt_service, sensor_command_send_service, device_command_send_service

# 1. 断开（若已连接）
if mqtt_service.is_connected:
    mqtt_service.stop()
    time.sleep(1)

# 2. 连接
if not mqtt_service.connect(timeout=10):
    raise RuntimeError("MQTT 连接失败")

# 3. 绑定命令服务
sensor_command_send_service.set_mqtt_service(mqtt_service)
device_command_send_service.set_mqtt_service(mqtt_service)

# 4. 注册处理器并订阅（与自启动步骤一致）
mqtt_service.setup_sensor_data_handler()
mqtt_service.setup_sensor_status_handler()
mqtt_service.setup_device_status_handler()

# 5. 验证：可直接发送命令
from sensors.models import Sensor
s = Sensor.objects.first()
if s:
    success = sensor_command_send_service.send_custom_command(s.sensor_id, 'enable')
    print(f"发送结果: {success}")
```

---

## 六、mqtt_service 其他高级用法

### 6.1 直接发布消息

```python
# 向指定主题发布 JSON
success = mqtt_service.publish(
    topic='iot/devices/SG_80_01/control',
    payload={'command': 'power_on'},
    qos=1
)
```

### 6.2 订阅自定义主题与自定义处理器

```python
# 订阅主题
mqtt_service.subscribe('iot/custom/+/events', qos=1)

# 注册自定义处理器
def my_handler(topic, payload):
    print(f"收到: {topic} -> {payload}")

mqtt_service.register_handler('iot/custom/+/events', my_handler)
```

---

## 七、完整手动初始化流程（调试）

适用于排查连接问题或覆盖自动行为：

```python
import logging
import time
from services import mqtt_service, sensor_command_send_service, device_command_send_service

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(name)s %(message)s')

# 1. 断开已有连接
if mqtt_service.is_connected:
    mqtt_service.stop()
    time.sleep(1)

# 2. 连接
ok = mqtt_service.connect(timeout=10)
if not ok:
    print("✗ 连接失败，检查 MQTT 配置")
    exit(1)

# 3. 绑定 send_service
sensor_command_send_service.set_mqtt_service(mqtt_service)
device_command_send_service.set_mqtt_service(mqtt_service)

# 4. 注册处理器并订阅
mqtt_service.setup_sensor_data_handler()
mqtt_service.setup_sensor_status_handler()
mqtt_service.setup_device_status_handler()

# 5. 开始发送命令
success = sensor_command_send_service.send_custom_command('DHT11-WEMOS-001', 'enable')
print(f"发送结果: {success}")
```

---

## 八、主题与消息格式速览

### 8.1 主题

| 主题格式 | 方向 | 说明 |
|---------|------|------|
| `iot/sensors/{sensor_id}/data` | 接收 | 传感器数据上报 → SensorData |
| `iot/sensors/{sensor_id}/status` | 接收 | 传感器状态上报 → SensorStatusCollection |
| `iot/sensors/{sensor_id}/control` | 发送 | 传感器控制命令 |
| `iot/devices/{device_id}/status` | 接收 | 设备状态上报 → DeviceData |
| `iot/devices/{device_id}/control` | 发送 | 设备控制命令 |

### 8.2 消息格式（接收端期望）

**传感器数据** `iot/sensors/+/data`：
```json
{"sensor_id": "DHT11-WEMOS-001", "data": {"temperature": 25.5, "humidity": 60}, "timestamp": 1708500000}
```

**传感器状态** `iot/sensors/+/status`：
```json
{"sensor_id": "DHT11-WEMOS-001", "event": "interval_updated", "status": {"samplingInterval": 60}, "check_code": "123456", "timestamp": 1708500000}
```

**设备状态** `iot/devices/+/status`：
```json
{"device_id": "SG_80_01", "event": "heartbeat", "status": {"power_state": true, "brightness": 80}, "check_code": "123456", "timestamp": 1708500000}
```

---

## 九、服务与导入路径速查

| 服务 | 导入方式 |
|-----|---------|
| mqtt_service | `from services import mqtt_service` |
| sensor_command_send_service | `from services import sensor_command_send_service` |
| device_command_send_service | `from services import device_command_send_service` |

| 方法 | 说明 |
|-----|------|
| `sensor_command_send_service.send_custom_command(sensor_id, command_name, params?)` | 发送传感器命令 |
| `sensor_command_send_service.send_custom_command_with_make_sure(sensor_id, command_name, params?, time_out=3)` | 发送并等待确认 |
| `sensor_command_send_service.show_sensor_control_commands(sensor)` | 查看传感器可用命令 |
| `device_command_send_service.send_custom_command(device_id, command_name, params?)` | 发送设备命令 |
| `device_command_send_service.send_custom_command_with_make_sure(device_id, command_name, params?, time=3)` | 发送并等待确认 |
| `device_command_send_service.show_device_control_commands(device)` | 查看设备可用命令 |
| `mqtt_service.publish(topic, payload, qos=1)` | 直接发布消息 |
| `mqtt_service.subscribe(topic, qos=1)` | 订阅主题 |
