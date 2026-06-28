# 自动化规则设计文档

本文档说明自由脚本规则 `AutomationRule` 的模型、执行引擎、包装 API、调度机制和完整示例。结构化双位/PI/PID 控制方案请同时参阅 [Project 模块设计](project_design.md) 与 [Project 使用指南](../backend_user_guide/project_guide.md)。

## 一、架构概览

| 组件 | 路径 | 职责 |
|---|---|---|
| `AutomationRule` | `automation/models.py` | 存储脚本、资源清单和轮询状态 |
| 执行引擎 | `automation/engine.py` | 注入资源、建立受限命名空间、查找并执行 `loop()` |
| 调度器 | `automation/scheduler.py` | 定期执行已启动规则，并与结构化控制方案共享单实例循环 |
| SensorWrapper | `automation/head_files/sensors.py` | 最新值、历史、均值、在线状态 |
| DeviceWrapper | `automation/head_files/devices.py` | 最新状态、在线状态和命令发送 |
| REST API | `automation/views.py` | CRUD、启动、停止、单次执行、可选资源 |

```text
AutomationRule
  ├── script + device_list
  ├── poll_interval + process_status
  └── scheduler
        → engine.execute_rule(rule)
            → build_sensors / build_devices
            → 受限 Python 命名空间
            → 控制器类 loop() 或顶层 loop()
            → 读取 SensorData / DeviceStatusCollection
            → DeviceWrapper.send_command()
```

## 二、AutomationRule 模型

| 字段 | 说明 |
|---|---|
| `name` | 规则名称 |
| `description` | 规则描述 |
| `script_id` | 唯一脚本 ID |
| `script` | 存储在数据库中的 Python 代码 |
| `device_list` | 本规则可访问的传感器和设备白名单 |
| `project` | 可选的 Project 场景关联 |
| `is_launched` | 是否进入后台轮询 |
| `poll_interval` | 轮询间隔，单位秒 |
| `process_status` | `idle` / `running` / `stopped_by_user` / `error_stopped` |
| `error_message` | 最近错误信息 |
| `last_run_time` | 最近调度时间 |

`device_list` 示例：

```json
[
  {"device_id": "DHT11-WEMOS-001", "device_type": "Sensor", "name": "温湿度传感器"},
  {"device_id": "SG_80_01", "device_type": "Device", "name": "LED灯"}
]
```

只有清单内的资源会注册到脚本的 `sensors` / `devices` 代理中。未声明的 ID 调用 `get()` 时返回 `None`。

## 三、执行引擎

### 3.1 执行流程

`execute_rule(rule)` 每次执行：

1. 根据 `device_list` 构建 SensorWrapper 和 DeviceWrapper。
2. 创建临时 `engine` 模块并注入 `sensors`、`devices`。
3. 使用受限内置函数和自定义 import 执行数据库中的脚本。
4. 优先查找第一个包含 `loop()` 的控制器类。
5. 找不到控制器类时，查找顶层 `loop()` 函数。
6. 执行一次并返回布尔结果。

引擎每一拍都会重新执行脚本并重新实例化控制器，因此 `__init__` 中的内存状态不会跨轮询周期保留。需要持久状态时应使用数据库模型；简单规则优先使用顶层 `loop()`。

### 3.2 两种脚本形式

类风格适合拆分辅助方法：

```python
from engine import sensors, devices

class MyController:
    def loop(self) -> bool:
        sensor = sensors.get('DHT11-WEMOS-001')
        return sensor is not None
```

函数风格适合短规则：

```python
from engine import sensors, devices

def loop() -> bool:
    sensor = sensors.get('DHT11-WEMOS-001')
    return sensor is not None
```

### 3.3 安全边界

脚本运行在受限命名空间中：

- 允许 `from engine import sensors, devices`。
- 允许平台明确放行的辅助模块。
- 禁止任意文件、进程、网络或动态代码能力。
- 移除 `open`、`eval`、`exec`、`compile`、原始 `__import__`、`globals`、`locals`、`breakpoint` 和 `input` 等危险内置函数。
- import 失败和脚本运行异常会被捕获、记录日志并返回 `False`；只有调度器自身出现未被引擎吸收的异常时，才会把规则切换为 `error_stopped`。

这是一层应用级约束，不应把数据库脚本执行能力开放给不可信用户。规则增删改仅限超级用户。

## 四、脚本资源 API

### 4.1 SensorWrapper

| 属性/方法 | 说明 |
|---|---|
| `device_id` | 传感器 ID |
| `current_state` | 最新 `SensorData.data`，同一拍内缓存 |
| `refresh()` | 强制刷新最新值 |
| `history(field, n=10)` | 最近 N 条字段值，按时间升序 |
| `average(field, minutes=5)` | 时间窗口平均值，无有效数据时返回 `None` |
| `is_online` | 按平台在线口径判断当前是否在线 |
| `model` | 对应 `Sensor` 实例 |

### 4.2 DeviceWrapper

| 属性/方法 | 说明 |
|---|---|
| `device_id` | 设备 ID |
| `current_state` | 最新 `DeviceStatusCollection.data`，同一拍内缓存 |
| `refresh()` | 强制刷新最新状态 |
| `is_online` | 按平台在线口径判断当前是否在线 |
| `send_command(name, params)` | 复用设备命令服务发送命令并等待确认 |
| `model` | 对应 `Device` 实例 |

命令名必须存在于 `DeviceType.commands`，参数名必须与命令模板一致：

```python
device.send_command('turn_on', {})
device.send_command('set_angle', {'val': 90})
```

## 五、调度与权限

调度器每秒扫描一次：

- `AutomationRule(is_launched=True, process_status='running')`
- `ControlScheme(is_enabled=True, status='running')`

到达各自执行间隔后运行一拍。自由脚本抛出严重异常时会切换为 `error_stopped`；控制方案异常时会被停用并切换为 `error`。

生产环境中调度器只在单实例 `iot-mqtt-runner` 容器运行。`iot-backend` 设置 `IOT_MQTT_RUNNER=false`，不会在多个 ASGI worker 中重复执行规则或重复下发命令。本地 `runserver` 仅在主进程启动调度器。

| 操作 | 权限 |
|---|---|
| 查看规则 | 已登录用户 |
| 新建、修改、删除规则 | 超级用户 |
| 单次执行、启动、停止 | 工作人员 |

主要接口：

| 接口 | 说明 |
|---|---|
| `GET/POST /api/automation-rules/` | 列表与创建 |
| `POST /api/automation-rules/<id>/execute/` | 单次执行并返回输出 |
| `POST /api/automation-rules/<id>/launch/` | 启动后台轮询 |
| `POST /api/automation-rules/<id>/stop/` | 停止轮询 |
| `GET /api/automation-rules/available-sources/` | 可选传感器、字段、设备和命令 |

## 六、完整脚本示例

以下内容由原独立示例文件合并而来。示例 ID 和命令仅用于说明，使用时必须替换为数据库中的真实资源。

### 6.1 通用模板：类风格与函数风格

```python
from engine import sensors, devices


class TemperatureMonitor:
    """温度超过阈值时开启 LED。"""

    TEMP_THRESHOLD = 30.0
    SENSOR_ID = 'DHT11-WEMOS-001'
    LED_ID = 'SG_80_01'

    def loop(self) -> bool:
        sensor = sensors.get(self.SENSOR_ID)
        led = devices.get(self.LED_ID)
        if not sensor or not led:
            return False

        temp = sensor.current_state.get('temperature')
        if temp is None:
            return False

        if float(temp) > self.TEMP_THRESHOLD:
            return bool(led.send_command('high', {}))
        return True


# 简单逻辑也可以不用类：
# def loop() -> bool:
#     sensor = sensors.get('DHT11-WEMOS-001')
#     led = devices.get('SG_80_01')
#     if not sensor or not led:
#         return False
#     temp = sensor.current_state.get('temperature', 0)
#     if float(temp) > 30:
#         return bool(led.send_command('high', {}))
#     return True
```

### 6.2 湿度告警并控制设备

```python
from engine import sensors, devices


class HumidityAlert:
    """湿度超过 70% 时发送 high，否则发送 low。"""

    SENSOR_ID = 'DHT11-WEMOS-001'
    DEVICE_ID = 'SG_80_001'
    HUMIDITY_THRESHOLD = 70.0

    def loop(self) -> bool:
        sensor = sensors.get(self.SENSOR_ID)
        device = devices.get(self.DEVICE_ID)
        if not sensor or not device:
            return False

        humidity = (sensor.current_state or {}).get('humidity')
        try:
            humidity = float(humidity)
        except (TypeError, ValueError):
            return False

        command = 'high' if humidity > self.HUMIDITY_THRESHOLD else 'low'
        return bool(device.send_command(command, {}))
```

### 6.3 湿度超限打印

```python
from engine import sensors, devices


class HumidityOverflowPrint:
    """湿度超过 80% 时打印告警，不控制设备。"""

    SENSOR_ID = 'DHT11-WEMOS-001'
    HUMIDITY_THRESHOLD = 80.0

    def loop(self) -> bool:
        sensor = sensors.get(self.SENSOR_ID)
        if not sensor:
            return False

        humidity = (sensor.current_state or {}).get('humidity')
        try:
            humidity = float(humidity)
        except (TypeError, ValueError):
            return False

        if humidity > self.HUMIDITY_THRESHOLD:
            print('[湿度超 80%%] 传感器 %s 当前湿度: %s%%' % (self.SENSOR_ID, humidity))
        return True
```

### 6.4 旋转传感器控制 SG90

```python
from engine import sensors, devices


class RotationSensorControlSG90:
    """把旋转传感器角度映射为舵机角度。"""

    SENSOR_ID = 'Rotation-001'
    DEVICE_ID = 'sg90_001'

    def loop(self) -> bool:
        sensor = sensors.get(self.SENSOR_ID)
        device = devices.get(self.DEVICE_ID)
        if not sensor or not device:
            return False

        angle = (sensor.current_state or {}).get('angle')
        try:
            angle = float(angle)
        except (TypeError, ValueError):
            return False

        if 0 <= angle <= 180:
            return bool(device.send_command('set_angle', {'val': angle}))
        return False
```

### 6.5 历史均值与趋势判断

```python
from engine import sensors, devices


def loop() -> bool:
    sensor = sensors.get('DHT11-WEMOS-001')
    fan = devices.get('fan_001')
    if not sensor or not fan or not sensor.is_online:
        return False

    average = sensor.average('temperature', minutes=5)
    history = sensor.history('temperature', n=10)
    if average is None or len(history) < 3:
        return False

    rising = history[-1] > history[-3] + 2
    if average > 30 or rising:
        return bool(fan.send_command('turn_on', {}))
    return True
```

## 七、编写与排查建议

- 不要在 `loop()` 中使用 `sleep()`；执行频率由 `poll_interval` 控制。
- 所有外部值先处理 `None` 并进行数值转换。
- 优先使用卫语句，避免在资源离线时继续执行。
- 下发命令后使用 `send_command()` 返回值判断是否确认成功。
- 单次执行会捕获 `print()` 和相关应用日志，适合启用轮询前调试。
- 脚本报 `get()` 返回 `None` 时，先检查 `device_list` 的 ID 和类型。
- 运行中规则持续异常时会自动停止，应查看 `error_message` 与后端日志。

## 八、关键代码位置

```text
iot_control_platform/automation/
├── models.py
├── engine.py
├── scheduler.py
├── views.py
├── serializers.py
└── head_files/
    ├── sensors.py
    └── devices.py
```

示例不再以独立生产文件保存在仓库中；本章是其唯一维护位置。
