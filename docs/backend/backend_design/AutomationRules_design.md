# 自动化规则设计文档

本文档描述物联网控制平台的自动化规则实现，涵盖 `AutomationRule` 模型、`engine` 执行引擎与 `head_files`（sensors、devices）的协作方式。

---

## 一、架构概览

| 组件 | 路径 | 职责 |
|-----|------|------|
| AutomationRule | `automation.models` | 存储规则、脚本、device_list、轮询状态及最后执行时间 |
| engine | `automation.engine` | 注入 sensors/devices，执行脚本，查找并调用控制器类的 loop() |
| scheduler | `automation.scheduler` | 后台守护线程，负责定期扫描并触发执行处于轮询状态的规则 |
| head_files.sensors | `automation.head_files.sensors` | 构建 sensors 代理，提供 `sensors.get(device_id)` 获取传感器包装对象 |
| head_files.devices | `automation.head_files.devices` | 构建 devices 代理，提供 `devices.get(device_id)` 获取设备包装对象及 send_command |

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AutomationRule                                       │
│  script, device_list, poll_interval, last_run_time                           │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      ▲ (检查与更新状态)
                                      │
┌─────────────────────────────────────┴───────────────────────────────────────┐
│                        scheduler (后台守护线程)                              │
│  1. 每秒扫描 `is_launched=True` 且 `process_status='running'` 的规则           │
│  2. 检查 `当前时间 - last_run_time >= poll_interval`                          │
│  3. 满足条件则更新 `last_run_time` 并调用 `engine.execute_rule(rule)`           │
│  4. 若执行抛出异常，更新状态为 `error_stopped` 并记录 `error_message`           │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │ (触发执行)
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  engine.execute_rule(rule)                                                   │
│    1. build_sensors(device_list) / build_devices(device_list)                │
│    2. 构造 engine 模块（sensors, devices）                                   │
│    3. 自定义 __import__ 使 from engine import sensors, devices 生效          │
│    4. exec(rule.script)                                                       │
│    5. 查找带 loop() 的控制器类 → 实例化 → 执行一次 loop()                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                    ┌──────────────────┴──────────────────┐
                    ▼                                     ▼
┌──────────────────────────────┐         ┌──────────────────────────────┐
│  head_files.sensors          │         │  head_files.devices          │
│  build_sensors(device_list)  │         │  build_devices(device_list)   │
│  → sensors.get(sensor_id)    │         │  → devices.get(device_id)     │
│  返回 SensorWrapper:         │         │  返回 DeviceWrapper:          │
│  - device_id                 │         │  - device_id                  │
│  - current_state (只读)      │         │  - current_state (只读)       │
│  - model (Sensor)            │         │  - send_command(name,params)│
│                              │         │  - model (Device)            │
└──────────────────────────────┘         └──────────────────────────────┘
         │ 读 SensorData.data                      │ 读 DeviceData.data
         │                                        │ 发 DeviceType.commands
         ▼                                        ▼
┌──────────────────┐                    ┌──────────────────┐
│  sensors.Sensor  │                    │  devices.Device   │
│  SensorData      │                    │  DeviceData       │
└──────────────────┘                    └──────────────────┘
```

---

## 二、AutomationRule 模型

### 2.1 字段说明

| 字段 | 类型 | 说明 |
|-----|------|------|
| name | CharField(100) | 规则名称 |
| description | TextField | 规则描述 |
| script_id | CharField(50), unique | 脚本唯一ID，供 `execute_by_script_id()` 调用 |
| script | TextField | Python 脚本内容 |
| device_list | JSONField | 关联设备与传感器列表 |
| is_launched | BooleanField | 是否启动轮询 |
| poll_interval | PositiveIntegerField | 轮询间隔（秒），默认 30 |
| process_status | CharField | idle / running / stopped_by_user / error_stopped |
| error_message | TextField | 错误详情（error_stopped 时） |
| last_run_time | DateTimeField | 最后执行时间（供调度器计算下次执行时间） |

### 2.2 device_list 格式

```json
[
  {"device_id": "DHT11-WEMOS-001", "device_type": "Sensor", "name": "温湿度传感器"},
  {"device_id": "SG_80_01", "device_type": "Device", "name": "LED灯"}
]
```

- `device_id`：传感器对应 `Sensor.sensor_id`，设备对应 `Device.device_id`
- `device_type`：`"Sensor"` 或 `"Device"`，决定由 `build_sensors` 还是 `build_devices` 处理

### 2.3 方法

| 方法 | 说明 |
|-----|------|
| `rule.execute()` | 执行一次脚本，返回 True/False |
| `AutomationRule.execute_by_script_id(script_id)` | 按 script_id 执行规则 |
| `AutomationRule.execute_by_script_id_with_timed_polling(script_id, interval_seconds)` | 定时轮询执行，Ctrl+C 停止 |
| `rule.get_device_count()` | 关联设备/传感器数量 |
| `rule.get_device_summary()` | 简要摘要，如 "DHT11-WEMOS-001(Sensor), SG_80_01(Device)" |

---

## 三、engine 执行引擎

### 3.1 execute_rule(rule) 流程

1. **构建 sensors、devices**
   ```python
   sensors = build_sensors(rule.device_list)
   devices = build_devices(rule.device_list)
   ```

2. **构造 engine 模块**
   ```python
   engine = types.ModuleType('engine')
   engine.sensors = sensors
   engine.devices = devices
   ```

3. **自定义 __import__ 与安全沙箱**
   - 脚本中 `from engine import sensors, devices` 时，返回注入的 engine，从而获取 sensors、devices
   - **白名单 import**：仅允许导入 `engine` 和 `automation.head_files` 下的模块，其余一律拒绝
   - **禁用危险内置函数**：`open`, `eval`, `exec`, `compile`, `__import__`(原始), `globals`, `locals`, `breakpoint`, `input`
   - 脚本在受限命名空间中执行，无法进行文件/进程/动态代码操作

4. **执行脚本**
   ```python
   exec(compile(rule.script, '<rule:name>', 'exec'), namespace)
   ```

5. **查找控制器并执行**
   - 从 namespace 查找第一个满足条件的类：非内置、有 `loop()` 方法
   - 实例化：`controller = controller_cls()`（相当于 setup）
   - 执行一次：`controller.loop()`（相当于 Arduino loop）

### 3.2 控制器类约定

- 类名不限，但不能以 `_` 开头
- 必须实现 `loop()` 方法，无参数，返回值用于表示是否成功（True/False/None→False）
- `__init__` 相当于 Arduino 的 setup，可用于 `sensors.get()`、`devices.get()`

### 3.3 脚本可用的导入

| 导入 | 说明 |
|-----|------|
| `from engine import sensors, devices` | 核心依赖，由引擎注入 |
| `from typing import Optional` | 已注入到 namespace |
| `from automation.head_files import ...` | 白名单允许的辅助模块 |
| 其他标准库 | 正常 `import time` 等均可使用 |

### 3.4 安全沙箱

脚本执行在受限命名空间中，具备以下安全策略：

| 策略 | 说明 |
|-----|------|
| 白名单 import | 仅允许 `engine` 和 `automation.head_files` 前缀匹配的模块 |
| 禁用危险内置 | `open`, `eval`, `exec`, `compile`, `__import__`, `globals`, `locals`, `breakpoint`, `input` |
| 受限命名空间 | 脚本只能访问注入的 `__builtins__`（已移除危险函数） |
| 异常捕获 | `ImportError` 单独捕获并记录，其他异常也会记录但不会崩溃 |

```
脚本中的 import 请求
    → _custom_import(name)
    → name == 'engine' ? 返回注入的 engine 模块
    → name 在白名单前缀中 ? 调用 real_import
    → 否则抛出 ImportError
```

---

## 四、head_files：sensors 与 devices

### 4.1 build_sensors(device_list)

从 device_list 中筛选 `device_type == "Sensor"` 的项，为每个 `device_id` 查询 `Sensor.objects.get(sensor_id=device_id)`，构建包装对象并注册到 sensors 代理。

**SensorWrapper 属性：**

| 属性 | 类型 | 说明 |
|-----|------|------|
| device_id | str | 传感器 ID |
| current_state | dict | 最新一条 SensorData.data，如 `{"temperature": 25.5, "humidity": 60}` |
| model | Sensor \| None | Sensor 模型实例，不存在时为 None |

**使用方式：** `sensor = sensors.get('DHT11-WEMOS-001')`

### 4.2 build_devices(device_list)

从 device_list 中筛选 `device_type == "Device"` 的项，为每个 `device_id` 查询 `Device.objects.get(device_id=device_id)`，构建包装对象。

**DeviceWrapper 属性：**

| 属性 | 类型 | 说明 |
|-----|------|------|
| device_id | str | 设备 ID |
| current_state | dict | 最新一条 DeviceData.data |
| send_command(name, params) | callable | 发送控制命令，内部调用 `device_command_send_service.send_custom_command_with_make_sure` |
| model | Device \| None | Device 模型实例 |

**send_command 说明：**
- `name`：命令名，需在 `DeviceType.commands` 中定义
- `params`：参数字典，如 `{"val": 80}`，对应 mqtt_message 中的占位符 `{val}`
- 默认等待 3 秒确认，失败返回 False

### 4.3 数据来源与命令发送

| 类型 | 数据来源 | 可发送命令 |
|-----|---------|-----------|
| Sensor | SensorData 最新一条 data | 否（仅读） |
| Device | DeviceData 最新一条 data | 是，通过 send_command |

---

## 五、执行方式

### 5.1 单次执行

```python
rule = AutomationRule.objects.get(script_id='humidity_alert')
rule.execute()

# 或
AutomationRule.execute_by_script_id('humidity_alert')
```

### 5.2 定时轮询执行

```python
AutomationRule.execute_by_script_id_with_timed_polling('humidity_alert', interval_seconds=30)
# 每 30 秒执行一次 loop()，Ctrl+C 停止
```

### 5.3 后台守护轮询 (Scheduler)

自动化规则的轮询通过 `automation.scheduler` 模块中的后台线程实现：
- 线程在 Django 启动时（`apps.py` 的 `ready()` 方法）自动启动。
- 每秒钟扫描一次 `AutomationRule` 表，查找所有标记为运行状态 (`is_launched=True` 且 `process_status='running'`) 的规则。
- 对比 `last_run_time` 与当前时间，如果超过 `poll_interval`，则调用 `execute_rule`，并更新 `last_run_time`。
- 如果执行中发生严重异常，调度器将自动把 `process_status` 置为 `error_stopped`，记录错误并停止该规则的轮询，保护系统稳定。

### 5.4 通过 API / 管理后台

规则可由 views (`/api/automation-rules/{id}/launch/`) 触发状态更新。前端只负责修改状态并定期查询结果，由后台调度器接管实际的执行循环。

---

## 六、文件结构

```
automation/
├── models.py              # AutomationRule 模型
├── engine.py              # execute_rule、_find_controller_class
├── scheduler.py           # 后台守护线程轮询器
├── apps.py                # 注册启动 scheduler
├── head_files/
│   ├── __init__.py
│   ├── sensors.py         # build_sensors、SensorWrapper
│   └── devices.py         # build_devices、DeviceWrapper、send_command
└── script/                # 示例脚本（仅供参考，规则脚本存在 DB）
    ├── sample_file.txt
    ├── humidity_alert.py
    ├── humidity_overflow_print.py
    └── rotation_sensor_control_sg90.py
```
