# 仿真模块端到端验证教程

本文档介绍如何端到端验证 `simulation/` 下的虚拟传感器和设备是否正确复刻了 `hardware/wemos-d1/*.ino` 的行为。模块说明与节点目录见 [仿真模块使用说明](simulation_guide.md)。

---

## 0. 前置条件

| 依赖 | 用途 | 检查命令 |
|------|------|----------|
| conda 环境 `simulation_env` | 运行 simulator | `conda env list \| grep simulation_env` |
| 可达的 MQTT broker | 数据中转 | `nc -zv 116.62.68.29 1883` |
| `simulation/config.yaml` | broker 配置（地址/默认账号） | `ls simulation/config.yaml`（首次运行需 `cp simulation/config.yaml.example simulation/config.yaml` 并改 broker） |
| `simulation/manifests/*.yaml` | 节点清单（按项目分文件） | `ls simulation/manifests/` 至少能看到 `default.yaml` 和 `st_plant.yaml` |
| Django 后端（仅 L3 验证需要） | 接收 MQTT 并入库 | `python iot_control_platform/manage.py runserver` |

```bash
conda activate simulation_env
pip install -r simulation/requirements.txt
```

---

## 验证策略：四层递进

| 层级 | 验证目标 | 不依赖 |
|------|----------|--------|
| **L1 日志验证** | simulator 进程能起、能发消息 | broker、Django |
| **L2 MQTT 验证** | broker 收到 payload，格式正确 | Django |
| **L3 端到端验证** | Django 入库、控制命令链路、check_code | 全链路 |
| **L4 批量启动验证** | manifest 清单批量起多节点、优雅退出 | Django（可选） |

每一层跑通后再进行下一层。

---

## L1：日志验证

启动单个节点，看本地日志是否正常打印数据上报和心跳。注意单节点脚本是 `simulation/<sensors|devices>/<module>/<module>.py` 的嵌套路径：

```bash
# 启动虚拟温湿度传感器（采样间隔 5s，心跳间隔 15s 方便观察）
python simulation/sensors/temp_humi_sensor/temp_humi_sensor.py \
  --id DHT11-WEMOS-001 \
  --broker 116.62.68.29 \
  --sampling-interval 5 \
  --status-report-interval 15
```

**预期输出**（前 20 秒内）：

```
INFO [DHT11-WEMOS-001] ✓ MQTT 已连接 116.62.68.29:1883
INFO [DHT11-WEMOS-001] ✓ 已订阅 iot/sensors/DHT11-WEMOS-001/control
INFO [DHT11-WEMOS-001] → status event=online
INFO [DHT11-WEMOS-001] 启动完成，进入主循环
INFO [DHT11-WEMOS-001] → data temperature=22.3°C humidity=51.8%
... 每 5 秒一条 data ...
INFO [DHT11-WEMOS-001] → status event=heartbeat   ← 15s 后出现
```

如果看到 `✗ 无法连接 116.62.68.29:1883`，先排查 broker 网络（`nc -zv 116.62.68.29 1883`）。

设备节点同理：

```bash
python simulation/devices/sg90_servo/sg90_servo.py \
  --id sg90_001 \
  --broker 116.62.68.29 \
  --status-report-interval 15
```

设备没有数据流，只有 `online` 和周期 `heartbeat`。

---

## L2：MQTT 抓包验证

simulator 自己说自己发了消息不算数，需要从 broker 侧反向确认。

### 方式 A：mosquitto_sub（推荐）

```bash
# 订阅传感器所有主题
mosquitto_sub -h 116.62.68.29 -t 'iot/sensors/DHT11-WEMOS-001/#' -v

# 订阅设备所有主题
mosquitto_sub -h 116.62.68.29 -t 'iot/devices/sg90_001/#' -v
```

### 方式 B：用 Python 临时订阅

如果机器上没装 mosquitto-clients，开一个临时 Python 脚本：

```bash
python - <<'EOF'
import paho.mqtt.client as mqtt
c = mqtt.Client()
c.on_message = lambda c, u, m: print(f"{m.topic}: {m.payload.decode()}")
c.connect("116.62.68.29", 1883, 60)
c.subscribe("iot/#")
c.loop_forever()
EOF
```

### 预期 payload

**传感器数据**（`iot/sensors/DHT11-WEMOS-001/data`）：
```json
{"sensor_id":"DHT11-WEMOS-001","data":{"temperature":22.3,"humidity":51.8},"timestamp":1778509698}
```

**传感器状态**（`iot/sensors/DHT11-WEMOS-001/status`）：
```json
{"sensor_id":"DHT11-WEMOS-001","event":"heartbeat","status":{"is_enabled":true,"samplingInterval":5,"statusReportInterval":15},"timestamp":1778509698}
```

**设备状态**（`iot/devices/sg90_001/status`）：
```json
{"device_id":"sg90_001","event":"online","status":{"angle":90,"statusReportInterval":15},"timestamp":1778509698}
```

**对照 form 文件验证**：
- `hardware/wemos-d1/sensors/temp_humi_sensor/mqtt_data_form.txt`
- `hardware/wemos-d1/sensors/temp_humi_sensor/mqtt_status_form.txt`
- `hardware/wemos-d1/devices/SG_90/mqtt_status_form.txt`

字段名和结构必须完全一致，否则 Django 那边 `_validate_message` 会拒绝。
（节点目录里每个模块还附带了 `mqtt_data.json` / `mqtt_status.json` / `mqtt_command.json` 样例，可直接对照。）

---

## L3：端到端验证（含 Django）

### 3.1 在 Django 中注册对应的传感器和设备

启动 Django：
```bash
conda activate iot_platform_env
python iot_control_platform/manage.py runserver
```

进入 admin（`http://127.0.0.1:8000/admin/`），创建：

**SensorType**（如果不存在）：
- 名称：`DHT11`
- `data_fields`: `["temperature", "humidity"]`
- `config_parameters`: `["is_enabled", "samplingInterval", "statusReportInterval"]`
- `commands`：参照 `hardware/wemos-d1/sensors/temp_humi_sensor/mqtt_command_form.txt` 的内容粘贴

**Sensor**：
- `sensor_id`: `DHT11-WEMOS-001`（必须和 simulator 的 `--id` 完全一致）
- `sensor_type`: 选刚才的 DHT11
- 名称、位置随意

**DeviceType**：
- 名称：`SG90`
- `state_fields`: `["angle", "statusReportInterval"]`
- `commands`：参照 `hardware/wemos-d1/devices/SG_90/mqtt_command_form.txt`

**Device**：
- `device_id`: `sg90_001`
- `device_type`: SG90

### 3.2 验证数据上报入库

启动 simulator 后，等几秒：

```bash
python iot_control_platform/manage.py shell <<'EOF'
from sensors.models import Sensor, SensorData, SensorStatusCollection
from devices.models import Device, DeviceData

s = Sensor.objects.get(sensor_id='DHT11-WEMOS-001')
print(f"in_online={s.is_online}, last_seen={s.last_seen}")
print(f"最新 3 条数据:")
for d in s.data_records.all()[:3]:
    print(f"  {d.timestamp}  {d.data}")
print(f"最新 3 条状态:")
for d in s.status_records.all()[:3]:
    print(f"  {d.timestamp}  event={d.event_name}  {d.data}")
EOF
```

**预期**：
- `is_online=True`
- 每 `sampling_interval` 秒一条 `SensorData`
- 至少一条 `event=online` 和若干 `event=heartbeat` 的 `SensorStatusCollection`

Django 日志同时会打印：
```
✓ 数据保存成功 - 传感器: DHT11-WEMOS-001, 数据: {'temperature': 22.3, 'humidity': 51.8}
```

### 3.3 验证控制命令 + check_code 链路（核心）

这是 simulator 最关键的复刻点：收到带 `check_code` 的命令后，要在 status 中原样回传，否则 `send_custom_command_with_make_sure` 会超时失败。

在 Django shell 里发命令：

```bash
python iot_control_platform/manage.py shell <<'EOF'
from services import sensor_command_send_service, device_command_send_service, mqtt_service

# 确保 mqtt_service 已启动（manage.py runserver 会自动起；shell 单跑需手动）
if not mqtt_service.is_connected:
    mqtt_service.connect()
    import time; time.sleep(1)

sensor_command_send_service.set_mqtt_service(mqtt_service)
device_command_send_service.set_mqtt_service(mqtt_service)

# 场景 1：set_data_interval（传感器侧应回 event=interval_updated 且 check_code 一致）
ok = sensor_command_send_service.send_custom_command_with_make_sure(
    'DHT11-WEMOS-001', 'set_data_interval', {'val': 8}, timeout=5
)
print(f"set_data_interval -> {ok}")  # 预期 True

# 场景 2：disable
ok = sensor_command_send_service.send_custom_command_with_make_sure(
    'DHT11-WEMOS-001', 'turn_off', {}, timeout=5
)
print(f"turn_off -> {ok}")

# 场景 3：set_angle
ok = device_command_send_service.send_custom_command_with_make_sure(
    'sg90_001', 'set_angle', {'val': 45}, timeout=5
)
print(f"set_angle 45 -> {ok}")
EOF
```

**simulator 侧应打印**：
```
INFO [DHT11-WEMOS-001] ← iot/sensors/.../control: b'{"command":"set_data_interval","interval":"8","check_code":"412933"}'
INFO [DHT11-WEMOS-001] ✓ samplingInterval → 8s
INFO [DHT11-WEMOS-001] → status event=interval_updated check_code=412933
```

**Django 侧 log**：`check_code 校验通过 - sensor_id=DHT11-WEMOS-001 已正确执行命令`

如果命令超时返回 `False`，最大可能原因：
1. `check_code` 没正确回传（看 simulator 日志里 `check_code=xxx` 是否和发送端一致）
2. Django 的 mqtt_service 没启动（`runserver` 模式下应自动启）
3. `sensor_id` 不匹配

### 3.4 验证离线检测

按 `Ctrl-C` 停掉 simulator，等 3 分钟（传感器默认）/ 心跳间隔×3（设备）后：

```python
Sensor.objects.get(sensor_id='DHT11-WEMOS-001').computed_is_online  # 应为 False
```

注意：`is_online` 字段不会自动变 False（只在收到数据时被设 True），需要看 `computed_is_online` 属性或等定时任务刷新。

---

## L4：批量启动验证

```bash
# 默认清单（manifests/default.yaml）
python simulation/run.py

# 指定其他清单 / 多份清单合并
python simulation/run.py -m default -m st_plant
```

预期：清单里的每个节点日志交错出现，各自独立心跳，互不干扰。启动时会先打印一行清单加载信息：

```
INFO 加载清单: default (6 节点) - 常规测试用节点（DHT11 + 舵机 + 双泵 + pin_control + 工业 TP）
INFO 已启动: temp_humi_sensor id=DHT11-WEMOS-001
...
INFO 共启动 6 个虚拟节点。Ctrl-C 退出。
```

`Ctrl-C` 后所有节点应优雅停止：
```
INFO 收到信号 2，停止所有节点…
INFO [DHT11-WEMOS-001] 已停止
INFO [sg90_001] 已停止
```

---

## 常见问题排查

| 现象 | 可能原因 | 处理 |
|------|----------|------|
| `✗ 无法连接 ...` | broker 不可达 / 防火墙 | `nc -zv <host> 1883` 检查 |
| simulator 日志正常但 Django 没入库 | `Sensor.sensor_id` 与 simulator `--id` 不一致 / Django mqtt_service 未连接 | 检查 admin 和 Django 日志 |
| `send_custom_command_with_make_sure` 超时 | check_code 链路断了 | 在 L2 抓包看 simulator status 是否带 `check_code` 字段 |
| 收到命令但 simulator 无反应 | command 名称不匹配 | 看 simulator 日志的 `← control:` 行，确认命令名 |
| 设备 `is_online` 一直 False | 没收到任何心跳 / `last_seen` 未更新 | 检查 broker 是否有 status 消息（L2） |

---

## 一键冒烟测试

把上述 L1+L2+L3 浓缩成一个最小冒烟：

```bash
# 终端 1：MQTT 监听
mosquitto_sub -h 116.62.68.29 -t 'iot/sensors/DHT11-WEMOS-001/#' -v &
SUB_PID=$!

# 终端 2：启动 simulator（30s 后自动停）
timeout 30 python simulation/sensors/temp_humi_sensor/temp_humi_sensor.py \
  --id DHT11-WEMOS-001 --broker 116.62.68.29 \
  --sampling-interval 3 --status-report-interval 10

kill $SUB_PID
```

30 秒内 mosquitto_sub 应至少看到：1 条 online、~10 条 data、2 条 heartbeat。
