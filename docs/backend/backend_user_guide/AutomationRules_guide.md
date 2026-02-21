# 自动化规则脚本编写指南

本文档介绍如何编写自动化规则脚本，适用于在 `AutomationRule.script` 中填写的 Python 代码。设计说明见 [AutomationRules_design.md](../backend_design/AutomationRules_design.md)。

---

## 一、脚本基本结构

### 1.1 Arduino 风格

脚本采用 Arduino 风格：`__init__` 相当于 `setup()`，`loop()` 相当于 Arduino 的 `loop()`。引擎每次执行会实例化控制器类并调用一次 `loop()`。

### 1.2 最小模板

```python
from engine import sensors, devices

class MyController:
    """你的控制器类，类名任意，但必须实现 loop()"""

    def __init__(self):
        """相当于 setup()：获取传感器、设备"""
        self.sensor = sensors.get('DHT11-WEMOS-001')
        self.device = devices.get('SG_80_01')

    def loop(self) -> bool:
        """相当于 loop()：每轮执行一次，返回 True 表示成功"""
        # 你的逻辑
        return True
```

---

## 二、获取 sensors 与 devices

### 2.1 必须的导入

```python
from engine import sensors, devices  # engine 由引擎注入
```

**注意**：不要写 `import engine`，必须用 `from engine import sensors, devices`。

### 2.2 sensors.get(device_id)

获取传感器包装对象，**device_id 需在 device_list 中配置为 device_type: "Sensor"**。

```python
sensor = sensors.get('DHT11-WEMOS-001')
if sensor:
    state = sensor.current_state  # dict，最新 SensorData.data
    # 如 {"temperature": 25.5, "humidity": 60}
    temp = state.get('temperature')
    humidity = state.get('humidity')
```

**SensorWrapper 属性：**

| 属性 | 说明 |
|-----|------|
| `device_id` | 传感器 ID |
| `current_state` | 最新采集数据，dict，无数据时为 `{}` |
| `model` | Sensor 模型实例，不存在时为 None |

### 2.3 devices.get(device_id)

获取设备包装对象，**device_id 需在 device_list 中配置为 device_type: "Device"**。

```python
device = devices.get('SG_80_01')
if device:
    state = device.current_state  # 最新 DeviceData.data
    device.send_command('turn_on', {})           # 无参数命令
    device.send_command('set_brightness', {'val': 80})  # 带参数命令
```

**DeviceWrapper 属性：**

| 属性 | 说明 |
|-----|------|
| `device_id` | 设备 ID |
| `current_state` | 最新状态数据，dict |
| `send_command(name, params)` | 发送控制命令，等待确认，返回 True/False |
| `model` | Device 模型实例 |

---

## 三、send_command 用法

### 3.1 命令名称与参数

命令名必须在 `DeviceType.commands` 中定义，参数名需与 `params` 列表一致。

```python
# 无参数
device.send_command('turn_on', {})
device.send_command('low', {})

# 带参数（占位符 {val} 替换为 80）
device.send_command('set_brightness', {'val': 80})
device.send_command('set_angle', {'val': 90})
```

### 3.2 返回值

`send_command` 内部使用 `send_custom_command_with_make_sure`，会等待设备回传确认（默认 3 秒）。成功返回 `True`，超时或失败返回 `False`。

---

## 四、控制器类约定

### 4.1 必须实现 loop()

```python
def loop(self) -> bool:
    # 返回 True：执行成功
    # 返回 False / None：视为失败
    return True
```

### 4.2 类名与命名

- 类名任意，但**不能以 `_` 开头**
- 引擎会查找**第一个**带 `loop()` 的类并执行

### 4.3 __init__ 中使用 sensors / devices

在 `__init__` 中调用 `sensors.get()`、`devices.get()` 并保存到实例属性，`loop()` 中直接使用。

```python
def __init__(self):
    self.sensor = sensors.get('DHT11-WEMOS-001')
    self.device = devices.get('SG_80_01')

def loop(self):
    if not self.sensor or not self.device:
        return False
    # ...
```

---

## 五、完整示例

### 5.1 湿度超限打印（只读传感器）

```python
from engine import sensors, devices
from typing import Optional

class HumidityOverflowPrint:
    SENSOR_ID = 'DHT11-WEMOS-001'
    HUMIDITY_THRESHOLD = 80.0

    def __init__(self):
        self.sensor = sensors.get(self.SENSOR_ID)

    def _get_humidity(self) -> Optional[float]:
        if not self.sensor:
            return None
        state = self.sensor.current_state or {}
        try:
            return float(state.get('humidity'))
        except (TypeError, ValueError):
            return None

    def loop(self) -> bool:
        humidity = self._get_humidity()
        if humidity is None:
            return False
        if humidity > self.HUMIDITY_THRESHOLD:
            print(f"[湿度超 80%] 传感器 {self.SENSOR_ID} 当前湿度: {humidity}%")
            return True
        return True
```

**device_list 配置：** 至少包含 `{"device_id": "DHT11-WEMOS-001", "device_type": "Sensor", "name": "温湿度传感器"}`

### 5.2 湿度告警控制 LED（传感器 + 设备）

```python
from engine import sensors, devices
from typing import Optional

class HumidityAlert:
    SENSOR_ID = 'DHT11-WEMOS-001'
    DEVICE_ID = 'SG_80_01'
    HUMIDITY_THRESHOLD = 70.0

    def __init__(self):
        self.sensor = sensors.get(self.SENSOR_ID)
        self.device = devices.get(self.DEVICE_ID)

    def _get_humidity(self) -> Optional[float]:
        if not self.sensor:
            return None
        state = self.sensor.current_state or {}
        try:
            return float(state.get('humidity'))
        except (TypeError, ValueError):
            return None

    def loop(self) -> bool:
        humidity = self._get_humidity()
        if humidity is None or not self.device:
            return False
        if humidity > self.HUMIDITY_THRESHOLD:
            self.device.send_command('high', {})
        else:
            self.device.send_command('low', {})
        return True
```

**device_list 配置：**
```json
[
  {"device_id": "DHT11-WEMOS-001", "device_type": "Sensor", "name": "温湿度传感器"},
  {"device_id": "SG_80_01", "device_type": "Device", "name": "LED灯"}
]
```

### 5.3 温度过高开 LED（带常量与卫语句）

```python
from engine import sensors, devices
from typing import Optional

class TemperatureMonitor:
    TEMP_THRESHOLD = 30.0
    SENSOR_ID = 'DHT11-WEMOS-001'
    LED_ID = 'SG_80_01'

    def __init__(self):
        self.sensor = sensors.get(self.SENSOR_ID)
        self.led = devices.get(self.LED_ID)

    def _get_temperature(self) -> Optional[float]:
        if not self.sensor:
            return None
        state = self.sensor.current_state or {}
        temp = state.get('temperature')
        if temp is None:
            return None
        try:
            return float(temp)
        except (TypeError, ValueError):
            return None

    def loop(self) -> bool:
        temp = self._get_temperature()
        if temp is None or not self.led:
            return False
        if temp > self.TEMP_THRESHOLD:
            self.led.send_command('high', {})
        return True
```

---

## 六、device_list 配置说明

### 6.1 格式

每条规则在 `device_list` 中声明可访问的传感器和设备：

```json
[
  {"device_id": "DHT11-WEMOS-001", "device_type": "Sensor", "name": "温湿度传感器"},
  {"device_id": "SG_80_01", "device_type": "Device", "name": "LED灯"}
]
```

### 6.2 字段说明

| 字段 | 必填 | 说明 |
|-----|-----|------|
| device_id | ✓ | 传感器对应 `Sensor.sensor_id`，设备对应 `Device.device_id` |
| device_type | ✓ | `"Sensor"` 或 `"Device"` |
| name | - | 备注用，便于识别 |

### 6.3 注意事项

- 脚本中的 `device_id` 必须与 `device_list` 中配置的一致
- 未在 device_list 中配置的 `device_id`，`sensors.get()` / `devices.get()` 返回 None

---

## 七、常见问题

### 7.1 未找到带 loop() 的控制器类

确保类满足：
- 类名不以 `_` 开头
- 实现了 `loop()` 方法
- 方法可调用（`callable`）

### 7.2 sensors.get() / devices.get() 返回 None

- 检查 `device_list` 是否包含该 `device_id`
- 检查 `device_type` 是否为 `"Sensor"` 或 `"Device"`
- 确认数据库中存在对应的 Sensor / Device 记录

### 7.3 current_state 为空

传感器/设备尚未上报过数据时，`current_state` 为 `{}`。应在脚本中做好空值判断。

### 7.4 send_command 失败

- 确认命令名在 `DeviceType.commands` 中已定义
- 检查参数名与 `params` 列表一致
- 确保 MQTT 已连接且 `mqtt_service.setup_device_status_handler()` 已注册（设备需回传 check_code 才能确认）

---

## 八、在 Shell 中测试规则

```python
from automation.models import AutomationRule

# 按 script_id 执行一次
AutomationRule.execute_by_script_id('humidity_alert')

# 定时轮询（每 30 秒，Ctrl+C 停止）
AutomationRule.execute_by_script_id_with_timed_polling('humidity_alert', 30)
```
