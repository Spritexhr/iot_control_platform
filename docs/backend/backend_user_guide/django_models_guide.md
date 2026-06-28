# Django 模型使用指南（Shell 视角）

本文档从 Django Shell 角度介绍如何查询、创建、更新各模型，以及如何调用相关方法与访问关联数据。适用于快速上手与调试。

---

## 一、启动 Shell

生产环境必须进入 backend 容器，连接实际 MySQL：

```bash
docker exec -it iot-backend python manage.py shell
```

本地脱机开发才使用 conda 环境：

```bash
# 在 iot_control_platform/ 后端目录
/Users/xhr_mac/miniconda3/envs/iot_platform_env/bin/python manage.py shell
```

或使用 iPython（如已安装）以获得更好体验：

```bash
/Users/xhr_mac/miniconda3/envs/iot_platform_env/bin/python manage.py shell -i ipython
```

---

## 二、常用导入

```python
from datetime import timedelta
from django.utils import timezone
from devices.models import DeviceType, Device, DeviceStatusCollection
from sensors.models import SensorType, Sensor, SensorData, SensorStatusCollection
from projects.models import (
    Project, ProjectSection, ProjectSensorMember,
    ProjectDeviceMember, ProjectView,
)
from automation.models import AutomationRule, ControlScheme
from platform_settings.models import PlatformConfig, Plugin
```

平台配置详细用法见 [platform_settings_guide.md](./platform_settings_guide.md)。

---

## 三、设备模块 (devices)

### 3.1 DeviceType（设备类型）

**查询**

```python
# 全部
DeviceType.objects.all()
list(DeviceType.objects.all())

# 按主键
DeviceType.objects.get(pk=1)

# 按类型ID
dt = DeviceType.objects.get(DeviceType_id='LED-01')

# 按名称
dt = DeviceType.objects.get(name='LED灯')
```

**创建**

```python
dt = DeviceType.objects.create(
    DeviceType_id='LED-01',
    name='LED灯',
    description='可调亮度LED',
    # 原 state_fields 已合并到 config_parameters
    config_parameters=['power_state', 'brightness', 'heartbeat_interval'],
    commands={
        'turn_on': {'mqtt_message': {'command': 'power_on'}, 'description': '打开', 'params': []},
        'turn_off': {'mqtt_message': {'command': 'power_off'}, 'description': '关闭', 'params': []},
        'set_brightness': {'mqtt_message': {'command': 'set_brightness', 'value': '{val}'}, 'description': '设置亮度', 'params': ['val']}
    }
)
```

**方法调用**

```python
dt.get_config_parameters()   # 返回全部可读状态/配置字段
dt.get_heartbeat_interval()  # 返回 60（默认）

# 反向关联：该类型下所有设备
dt.devices.all()
```

---

### 3.2 Device（设备实例）

**查询**

```python
# 全部
Device.objects.all()

# 按 device_id
dev = Device.objects.get(device_id='SG_80_01')

# 预加载类型（减少查询）
dev = Device.objects.select_related('device_type').get(device_id='SG_80_01')

# 过滤在线
Device.objects.filter(is_online=True)

# 某类型下的设备
Device.objects.filter(device_type__DeviceType_id='LED-01')
```

**创建**

```python
dt = DeviceType.objects.get(DeviceType_id='LED-01')
dev = Device.objects.create(
    device_id='SG_80_01',
    name='客厅LED灯',
    description='可调光',
    location='客厅',
    device_type=dt
)
# save 时若 topic 为空，会自动写入 mqtt_topic_data / mqtt_topic_control
```

**访问关联**

```python
dev.device_type           # DeviceType 实例
dev.device_type.name      # 类型名称
dev.status_records          # 反向关联：DeviceStatusCollection QuerySet
dev.status_records.all()
dev.status_records.first()  # 最新一条（模型默认按 timestamp 倒序）
```

**方法调用**

```python
dev.get_heartbeat_interval()   # 从 device_type 获取，默认 60
dev.check_online_status()      # 检查是否超时离线，必要时更新 is_online
dev.update_heartbeat()         # 手动更新 last_seen 和 is_online
dev.get_data_count(24)         # 近 24 小时数据条数
dev.get_data_count(hours=7)    # 近 7 小时
```

---

### 3.3 DeviceStatusCollection（设备状态记录）

**查询**

```python
# 某设备最新 10 条
DeviceStatusCollection.objects.filter(
    device__device_id='SG_80_01'
).order_by('-timestamp')[:10]

# 通过设备反向查询
dev = Device.objects.get(device_id='SG_80_01')
dev.status_records.all()[:10]
dev.status_records.filter(timestamp__gte=timezone.now() - timedelta(days=1))
```

**创建**

```python
dev = Device.objects.get(device_id='SG_80_01')
DeviceStatusCollection.objects.create(
    device=dev,
    data={'power_state': True, 'brightness': 80},
    event_name='heartbeat',
    timestamp=timezone.now()
)
# 保存时会调用 dev.update_heartbeat()
```

**访问数据内容**

```python
record = dev.status_records.first()
record.data              # dict，如 {'power_state': True, 'brightness': 80}
record.data.get('brightness')
record.event_name        # 如 heartbeat / online / offline
record.timestamp
record.device.device_id
```

---

## 四、传感器模块 (sensors)

### 4.1 SensorType（传感器类型）

**查询**

```python
SensorType.objects.all()
st = SensorType.objects.get(SensorType_id='DHT11-01')
st = SensorType.objects.get(name='DHT11温湿度传感器')
```

**创建**

```python
st = SensorType.objects.create(
    SensorType_id='DHT11-01',
    name='DHT11温湿度传感器',
    description='温湿度',
    data_fields=['temperature', 'humidity'],
    config_parameters=['samplingInterval', 'is_enabled'],
    commands={
        'turn_on': {'mqtt_message': {'command': 'enable'}, 'description': '启动', 'params': []},
        'set_interval': {'mqtt_message': {'command': 'set_interval', 'interval': '{val}'}, 'description': '设间隔', 'params': ['val']}
    }
)
```

**反向关联**

```python
st.sensors.all()   # 该类型下所有传感器
```

---

### 4.2 Sensor（传感器实例）

**查询**

```python
Sensor.objects.all()
s = Sensor.objects.get(sensor_id='DHT11-WEMOS-001')
s = Sensor.objects.select_related('sensor_type').get(sensor_id='DHT11-WEMOS-001')
Sensor.objects.filter(is_online=True)
```

**创建**

```python
st = SensorType.objects.get(SensorType_id='DHT11-01')
s = Sensor.objects.create(
    sensor_id='DHT11-WEMOS-001',
    name='客厅温湿度',
    location='客厅',
    sensor_type=st
)
```

**关联数据**

```python
s.sensor_type
s.data_records          # SensorData，采集数据
s.status_records        # SensorStatusCollection，状态事件
s.data_records.first()  # 最新采集数据
s.status_records.first()# 最新状态
```

**属性和方法**

```python
s.computed_is_online     # 属性：3 分钟内有上报视为在线
s.update_last_seen()    # 更新 last_seen、is_online
s.update_last_seen(timestamp=某个datetime)  # 指定时间
```

---

### 4.3 SensorData（传感器采集数据）

**查询**

```python
SensorData.objects.filter(sensor__sensor_id='DHT11-WEMOS-001').order_by('-timestamp')[:10]
# 或
s = Sensor.objects.get(sensor_id='DHT11-WEMOS-001')
s.data_records.all()[:10]
```

**创建**

```python
from django.utils import timezone
s = Sensor.objects.get(sensor_id='DHT11-WEMOS-001')
SensorData.objects.create(
    sensor=s,
    data={'temperature': 25.5, 'humidity': 60.0},
    timestamp=timezone.now()
)
# 保存时会调用 s.update_last_seen(timestamp)
```

**读取**

```python
rec = s.data_records.first()
rec.data['temperature']
rec.data['humidity']
rec.timestamp
```

---

### 4.4 SensorStatusCollection（传感器状态记录）

**查询**

```python
SensorStatusCollection.objects.filter(sensor__sensor_id='DHT11-WEMOS-001').order_by('-timestamp')
s.status_records.all()
```

**创建**

```python
SensorStatusCollection.objects.create(
    sensor=s,
    data={'is_enabled': True, 'samplingInterval': 60},
    timestamp=timezone.now(),
    event_name='interval_updated'
)
```

---

## 五、自动化模块 (automation)

### 5.1 AutomationRule（自动化规则）

**查询**

```python
AutomationRule.objects.all()
rule = AutomationRule.objects.get(script_id='humidity_alert')
rule = AutomationRule.objects.get(pk=1)
```

**创建**

```python
rule = AutomationRule.objects.create(
    name='湿度超限告警',
    description='湿度>80%时打印',
    script_id='humidity_alert',
    script='''# 示例脚本省略''',
    device_list=[
        {'device_id': 'DHT11-WEMOS-001', 'device_type': 'Sensor', 'name': '温湿度传感器'},
        {'device_id': 'SG_80_01', 'device_type': 'Device', 'name': 'LED灯'}
    ],
    poll_interval=30
)
# 如需归属场景，可额外传 project=Project.objects.get(code='HOME')
```

**方法调用**

```python
rule.get_device_count()    # 关联设备/传感器数量
rule.get_device_summary()  # 简要摘要，如 "DHT11-WEMOS-001(Sensor), SG_80_01(Device)"
rule.execute()             # 执行一次规则脚本，返回 True/False
```

**类方法**

```python
# 按 script_id 执行一次
AutomationRule.execute_by_script_id('humidity_alert')  # 返回 bool

# 定时轮询执行（阻塞，Ctrl+C 停止）
AutomationRule.execute_by_script_id_with_timed_polling('humidity_alert', interval_seconds=30)
```

**device_list 与模型关联**

```python
# device_list 中 device_id 可能是 Sensor.sensor_id 或 Device.device_id
for item in rule.device_list:
    did = item.get('device_id')
    dtype = item.get('device_type')
    if dtype == 'Sensor':
        try:
            obj = Sensor.objects.get(sensor_id=did)
        except Sensor.DoesNotExist:
            obj = None
    elif dtype == 'Device':
        try:
            obj = Device.objects.get(device_id=did)
        except Device.DoesNotExist:
            obj = None
```

---

## 六、Project 项目/场景模块（projects）

Project 成员同时包含 `project` 与 `section` 外键，直接 ORM 写入容易制造不一致数据。生产配置优先使用前端或 REST API；Shell 更适合查询和排障。完整操作见 [Project 场景使用指南](project_guide.md)。

**查询项目与房间**

```python
p = Project.objects.get(code='HOME')
p.sections.all()
p.sensor_members.select_related('sensor', 'section').all()
p.device_members.select_related('device', 'section').all()
p.views.select_related('section').all()
p.automation_rules.all()   # 可选归属此项目的自由脚本规则
p.control_schemes.all()    # 结构化双位/PI/PID 控制方案
```

**按房间查询成员和视图**

```python
section = ProjectSection.objects.get(project=p, name='客厅')
section.sensor_members.select_related('sensor').all()
section.device_members.select_related('device').all()
section.views.all()
section.control_schemes.all()
```

**查看传感器场景点位**

```python
member = section.sensor_members.select_related('sensor').first()
member.sensor.sensor_id
member.data_key
member.point_id       # sensor_id 或 sensor_id::data_key
member.hi_threshold
member.lo_threshold
```

**从主模型反查所属场景**

```python
s = Sensor.objects.get(sensor_id='DHT11-WEMOS-001')
s.project_members.select_related('project', 'section').all()

dev = Device.objects.get(device_id='SG_80_01')
dev.project_members.select_related('project', 'section').all()
```

> 删除项目、房间、Sensor 或 Device 前应先检查 `ControlScheme`。方案对成员使用 `PROTECT`，存在引用时删除会抛出 `ProtectedError`。

---

## 七、综合查询示例

### 7.1 获取传感器最新一条采集数据

```python
s = Sensor.objects.get(sensor_id='DHT11-WEMOS-001')
latest = s.data_records.first()
if latest:
    print(latest.data)  # {'temperature': 25.5, 'humidity': 60.0}
```

### 7.2 获取设备近 24 小时状态条数

```python
dev = Device.objects.get(device_id='SG_80_01')
count = dev.get_data_count(24)
```

### 7.3 批量检查设备在线状态

```python
for dev in Device.objects.filter(is_online=True):
    if not dev.check_online_status():
        print(f"{dev.device_id} 已离线")
```

### 7.4 按类型统计设备数量

```python
from django.db.models import Count
DeviceType.objects.annotate(cnt=Count('devices')).values('name', 'cnt')
```

---

## 八、常用 ORM 片段速查

| 需求 | 示例 |
|-----|------|
| 按 ID 查询 | `Device.objects.get(device_id='SG_80_01')` |
| 过滤 | `Sensor.objects.filter(is_online=True)` |
| 反向关联 | `dt.devices.all()` / `dev.status_records.all()` |
| 预加载 | `Device.objects.select_related('device_type')` |
| 最新 N 条 | `dev.status_records.all()[:10]` |
| 时间范围 | `dev.status_records.filter(timestamp__gte=start, timestamp__lte=end)` |
| 存在性 | `Sensor.objects.filter(sensor_id='xxx').exists()` |
| 计数 | `Sensor.objects.count()` / `dev.get_data_count(24)` |

---

## 九、平台配置模块 (platform_settings)

### 9.1 PlatformConfig（平台配置）

**查询**

```python
PlatformConfig.objects.all()
cfg = PlatformConfig.objects.get(key='mqtt_broker')
PlatformConfig.objects.filter(category='mqtt')
```

**创建 / 更新**

```python
PlatformConfig.objects.create(key='mqtt_broker', value='127.0.0.1', category='mqtt', description='MQTT 地址')
cfg = PlatformConfig.objects.get(key='mqtt_broker')
cfg.value = '192.168.1.100'
cfg.save()
```

**统一读取（数据库中不存在时使用调用方默认值）**

```python
from config.platform_config import get_config
broker = get_config('mqtt_broker', '127.0.0.1')
port = get_config('mqtt_port', 1883, int)
```

**初始化命令**：`/Users/xhr_mac/miniconda3/envs/iot_platform_env/bin/python manage.py configure --init` 将 `platform_settings/defaults.py` 中的默认值写入数据库；不带参数运行 `configure` 可进入交互式 wizard。详见 [platform_settings_guide.md](./platform_settings_guide.md)。

### 9.2 Plugin（插件登记）

```python
Plugin.objects.all()
Plugin.objects.filter(enabled=True)
plugin = Plugin.objects.get(name='data_viz')
plugin.enabled = False
plugin.save(update_fields=['enabled', 'updated_at'])
```

插件启用状态影响启动时的路由挂载，修改后需要重启 Django 容器或进程。
