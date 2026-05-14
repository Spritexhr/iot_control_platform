# Simulation —— 虚拟传感器与设备仿真

复刻 `hardware/wemos-d1/` 下各 `.ino` 固件的 MQTT 行为，用 Python 模拟一台台"软件版的硬件"——同样的主题、同样的 payload、同样的 check_code 回传协议，但跑在 Mac/Linux 上而不是 ESP8266 上。

> 与 `iot_control_platform/` Django 后端**完全解耦**。仿真器只是一组 MQTT 客户端，通过 broker 与后端通信，不依赖任何 Django 代码或数据库。

---

## 目录结构

```
simulation/
├── README.md                 本文档
├── TESTING.md                端到端验证教程（L1 日志 / L2 抓包 / L3 入库）
├── requirements.txt          paho-mqtt + PyYAML
├── config.yaml.example       broker 配置模板（提交到 git）
├── config.yaml               broker 真实配置（gitignore，复制 .example 后改）
├── run.py                    统一启动器，加载 manifests/ 下的清单
├── manifests/                节点清单目录（提交到 git，按项目分文件）
│   ├── default.yaml          默认清单：常规测试节点
│   └── eb_plant.yaml         乙苯(EB)装置清单（占位，等设备拆分）
├── common/
│   ├── mqtt_node.py          基类：连接/重连/订阅/心跳/check_code 回传
│   └── waveforms.py          数据波形：sine / random_walk / uniform / constant
├── sensors/                  传感器节点（上报 data，可能上报 status）
│   ├── temp_humi_sensor/
│   ├── bmp280_temp_pressure_sensor/
│   ├── rotation_sensor/
│   ├── touch_sensor_switch/
│   ├── radial_counting_module/
│   ├── temp_pressure_sensor/
│   └── flow_sensor/
└── devices/                  设备节点（执行器，只上报 status，响应命令）
    ├── sg90_servo/
    ├── pin_control/
    ├── pump/
    └── eb_plant/             乙苯装置（装置级模拟器，独立运行）
```

---

## 环境准备

```bash
# 创建独立 conda 环境
conda create -n simulation_env python=3.11 -y
conda activate simulation_env

# 安装依赖
pip install -r simulation/requirements.txt
```

依赖只有 `paho-mqtt`（MQTT 客户端）和 `PyYAML`（解析配置）。

---

## 配置

配置分两层：

- **`config.yaml`** —— 只放 broker 地址/默认账号（gitignore，每人本地一份）。首次使用 `cp config.yaml.example config.yaml` 后改 broker.host。
- **`manifests/*.yaml`** —— 节点清单，按项目/场景分文件（进 git，团队共享）。`run.py` 根据 `--manifest` 决定加载哪一份（或哪几份）。

最小 `config.yaml`：
```yaml
broker:
  host: 116.62.68.29       # 你的 EMQX 地址
  port: 1883
  username: ""             # broker 级默认账号，留空表示匿名
  password: ""
```

最小 `manifests/<name>.yaml`：
```yaml
name: <name>
description: 给团队成员的说明
nodes:
  - module: temp_humi_sensor
    id: DHT11-WEMOS-001
    sampling_interval: 10
    status_report_interval: 30
```

### 节点级 username/password 覆盖

`broker.username/password` 是所有节点的默认账号。如果 EMQX 启用了 ACL，可以在 manifest 里给单个节点指定自己的账号：

```yaml
nodes:
  - module: temp_humi_sensor
    id: DHT11-WEMOS-001
    # 不写 username → 用 broker 级默认（匿名）

  - module: temp_humi_sensor
    id: DHT11-WEMOS-002
    username: sensor_002    # 这个节点用专属账号
    password: "secret123"
```

---

## 启动方式

### 方式 1：批量启动（推荐）

`run.py` 从 `config.yaml` 拿 broker，从 `manifests/*.yaml` 拿节点列表，每个节点起一个独立线程，client_id = `WemosD1-<id>`（与固件一致）。

```bash
# 加载默认清单 manifests/default.yaml
python simulation/run.py

# 加载指定清单（manifest 名 = 文件名去掉 .yaml）
python simulation/run.py --manifest eb_plant
python simulation/run.py -m eb_plant            # 短写法

# 同时加载多份清单（会合并并检测重复的 module+id）
python simulation/run.py -m default -m eb_plant

# 也可以直接指定 yaml 路径
python simulation/run.py -m ./my_custom_manifest.yaml
```

`Ctrl-C` 会优雅停止所有节点。

### 清单的设计意图

- **一个项目一份清单**：苯乙烯装置写在 `eb_plant.yaml`、常规测试写在 `default.yaml`、有新场景就新建一份。
- **按需启动**：跑 EB 大屏时只需 `-m eb_plant`，不会被无关节点污染。
- **组合启动**：调试时可以叠加，比如 `-m eb_plant -m sandbox`。重复的 `(module, id)` 会直接报错，避免 client_id 冲突。
- **共享进 git**：manifest 不含敏感凭据（凭据走 broker 级默认或节点级覆盖），团队成员 clone 下来就能跑。

### 方式 2：单独跑一个节点

每个 `.py` 都可以独立运行，使用 `argparse` 接受命令行参数。这种方式不读 `config.yaml`、不读 manifest，适合调试单个节点或者快速验证。

```bash
# 温湿度
python simulation/sensors/temp_humi_sensor.py \
  --id DHT11-WEMOS-001 --broker 116.62.68.29 \
  --sampling-interval 5 --status-report-interval 15

# 舵机
python simulation/devices/sg90_servo.py \
  --id sg90_001 --broker 116.62.68.29

# 水泵
python simulation/devices/pump.py \
  --id pump_001 --broker 116.62.68.29 --max-power-kw 20
```

每个脚本 `--help` 看完整参数列表。

---

## 节点目录

### 复刻硬件（与对应 .ino 协议一致）

| Module | 默认 ID | 数据字段 | 关键命令 |
|--------|---------|---------|---------|
| `temp_humi_sensor` | DHT11-WEMOS-001 | `temperature`(°C), `humidity`(%) | enable/disable/set_data_interval/set_status_interval |
| `bmp280_temp_pressure_sensor` | BMP280-WEMOS-001 | `temperature`(°C), `pressure`(**hPa**) | 同上 |
| `rotation_sensor` | Rotation-001 | `raw`(0-1023), `position`(0-100%), `angle`(0-360°) | 同上 |
| `touch_sensor_switch` | Switch-Touch-001 | `switch`(bool)，**事件驱动**：状态翻转才发 data | enable/disable/set_status_interval |
| `radial_counting_module` | H2010-PHOTO-001 | 协议同 touch | 同上 |
| `sg90_servo` | sg90_001 | 仅 status，无 data | set_angle/current_status/set_status_interval |
| `pin_control` | potential_controler_001 | 仅 status，`level_d5/d6/d7` | high/low/high_all/low_all/current_status/set_status_interval |

### 新增节点（无对应固件）

| Module | 默认 ID | 数据字段 / 状态字段 | 关键命令 |
|--------|---------|---------|---------|
| `temp_pressure_sensor` | TP-KPA-001 | `temperature`(°C), `pressure`(**kPa**) | enable/disable/set_data_interval/set_status_interval |
| `pump` | pump_001 | 仅 status：`power_kw`, `target_power_kw`, `is_running` | **start/stop/set_power**/current_status/set_status_interval |
| `flow_sensor` | FLOW-001 | `flow_rate`(L/min), `accumulated_volume`(L) | enable/disable/set_data_interval/set_status_interval/**reset_volume** |

---

## 配置波形

只对**传感器节点**有效（设备节点状态由命令驱动，不需要波形）。每个节点可以为每个 data 字段独立配置波形：

```yaml
- module: temp_humi_sensor
  id: DHT11-WEMOS-001
  waveforms:
    temperature: {type: sine, min: 20, max: 26, period: 3600, jitter: 0.3}
    humidity:    {type: random_walk, start: 55, step: 1.5, bounds: [40, 70]}
```

**支持的波形类型**：

| type | 参数 | 用途 |
|------|------|------|
| `sine` | `min`, `max`, `period`(秒), `jitter`(±噪声，默认 0), `phase`(初始相位偏移秒，默认 0) | 昼夜温度、潮汐等周期信号 |
| `random_walk` | `start`, `step`, `bounds`(`[lo, hi]`) | 湿度、电池电量等慢变量 |
| `uniform` | `min`, `max` | 独立采样随机数 |
| `constant` | `value` | 恒定值（开关基线、固定 setpoint） |

**用 phase 错开同型号节点**：多个同型号传感器默认会同步——比如两个 `temp_humi_sensor` 启动时 `_t0` 接近相同，正弦波相位也接近相同。通过 `phase: <秒数>` 把其中一个的相位推后，曲线就错开了：

```yaml
- module: temp_humi_sensor
  id: room_A
  waveforms:
    temperature: {type: sine, min: 20, max: 26, period: 3600, phase: 0}

- module: temp_humi_sensor
  id: room_B
  waveforms:
    temperature: {type: sine, min: 20, max: 26, period: 3600, phase: 900}  # 偏移 15 分钟
```

**不写 waveforms 字段**：每个传感器 `.py` 顶部都有一个 `DEFAULT_WAVEFORMS` 常量提供合理默认值，单独跑（不通过 `run.py`）时就用这套默认。

---

## 与 Django 后端对接

仿真器是一组**纯 MQTT 客户端**，对 Django 透明。Django 那一侧需要：

1. **EMQX 在线** 且 Django `mqtt_service` 已连接（`runserver` 启动时会自动连）。
2. **数据库里有匹配的 Sensor / Device 记录**：仿真器 `id` 字段必须等于 `Sensor.sensor_id` 或 `Device.device_id`，否则 Django 收到消息会因为找不到对应记录而拒绝入库。
3. **SensorType / DeviceType 的字段定义匹配**：
   - `SensorType.data_fields` 要包含仿真器上报的所有键（如 BMP280 要有 `temperature`, `pressure`）
   - `SensorType.commands` / `DeviceType.commands` 要包含你想从后端发送的命令，参考 `hardware/wemos-d1/*/mqtt_command_form.txt`

详细的端到端验证步骤见 [`TESTING.md`](TESTING.md)。

---

## 添加新节点

1. 在 `sensors/` 或 `devices/` 下新建 `xxx.py`
2. 继承 `MqttNode`，设置 `NODE_TYPE`（`"sensor"`/`"device"`）和 `ID_FIELD`（`"sensor_id"`/`"device_id"`）
3. 实现：
   - `build_status_payload()` —— 返回 status 字典
   - `handle_command(command, payload, check_code)` —— 处理控制命令；**响应命令后必须调用 `self.publish_status(event, check_code)`**，把收到的 check_code 原样回传，否则后端 `send_custom_command_with_make_sure` 会超时
   - `on_tick()` —— （可选）周期任务，比如发数据。基类的 tick 频率约 10 Hz
4. 在 `run.py` 顶部 `from xxx import XxxClass`，并加到 `REGISTRY` 字典
5. 在某份 `manifests/*.yaml`（或新建一份）的 `nodes:` 里加一条 `module: xxx`

最简模板参考 `sensors/radial_counting_module.py`（继承 `TouchSensorSwitch` 仅 20 行）。完整模板参考 `sensors/temp_humi_sensor.py` 或 `devices/pump.py`。

---

## 常见问题

| 现象 | 可能原因 | 处理 |
|------|---------|------|
| `Connection refused 127.0.0.1:1883` | 单脚本没传 `--broker`，用了默认本地地址 | `--broker <你的IP>` 或改用 `run.py` 跑 |
| `unknown module: xxx` | yaml 里 module 名拼错 / 没在 REGISTRY 注册 | 对照 [节点目录](#节点目录) 表格 |
| simulator 日志正常但后端没入库 | `sensor_id`/`device_id` 在 Django 里不存在 | admin 里建对应记录 |
| `send_custom_command_with_make_sure` 超时 | check_code 没回传 | L2 抓包看 status payload 是否带 `check_code` 字段 |
| 心跳很正常但没收到 data | 该节点是事件驱动（touch/h2010）或 disabled | 等状态翻转 / 发 enable 命令 |

更多排错见 [`TESTING.md`](TESTING.md) 末尾的"常见问题排查"表。
