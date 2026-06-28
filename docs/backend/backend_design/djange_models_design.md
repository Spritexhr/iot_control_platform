# Django 数据模型设计文档

本文档以当前 `Beta_version` 模型和迁移为准，描述传感器、设备、项目/场景、自动化和平台配置的数据结构。Project 的接口、实时通道和前端视图另见 [Project 场景模块设计](project_design.md)。

> 审核日期：2026-06-28。旧文档中的 `DeviceData`、`DeviceType.state_fields`、仅四个核心 app、AutomationRule 无 Project 关联等描述均已按当前代码修正。

## 一、应用与模型概览

| App | 职责 | 核心模型 |
|---|---|---|
| `sensors` | 输入器类型、实例、采集值与状态事件 | `SensorType`、`Sensor`、`SensorData`、`SensorStatusCollection` |
| `devices` | 执行器类型、实例与统一状态事件 | `DeviceType`、`Device`、`DeviceStatusCollection` |
| `projects` | 项目、房间、场景成员和展示视图 | `Project`、`ProjectSection`、`ProjectSensorMember`、`ProjectDeviceMember`、`ProjectView` |
| `automation` | 自由脚本规则与结构化闭环控制 | `AutomationRule`、`ControlScheme` |
| `platform_settings` | 运行时配置与插件登记 | `PlatformConfig`、`Plugin` |

整体关系：

```text
SensorType 1 ── N Sensor 1 ── N SensorData
                         └── N SensorStatusCollection
                         └── N ProjectSensorMember

DeviceType 1 ── N Device 1 ── N DeviceStatusCollection
                         └── N ProjectDeviceMember

User 1 ── N Project
Project 1 ── N ProjectSection
        ├── N ProjectSensorMember
        ├── N ProjectDeviceMember
        ├── N ProjectView
        ├── N AutomationRule（可选关联）
        └── N ControlScheme

ProjectSection 1 ── N 成员 / View / ControlScheme
ProjectSensorMember 1 ── N ControlScheme（PROTECT）
ProjectDeviceMember 1 ── N ControlScheme（PROTECT）
```

## 二、传感器模块（sensors）

### 2.1 SensorType

定义一类传感器的字段、配置参数和可用命令。

| 字段 | 类型/约束 | 说明 |
|---|---|---|
| `SensorType_id` | `CharField(50)`，unique，db_index | 类型业务 ID |
| `name` | `CharField(50)`，unique | 类型名称 |
| `description` | `TextField(blank=True)` | 描述 |
| `data_fields` | `JSONField(default=list)` | 数据上报字段，如 `temperature`、`humidity` |
| `config_parameters` | `JSONField(default=list)` | 状态/配置字段 |
| `commands` | `JSONField(default=list)` | 传感器支持的命令定义 |
| `created_at` | `DateTimeField(auto_now_add=True)` | 创建时间 |

`commands` 的业务结构实际按命令名映射，与 DeviceType 类似。模型历史默认值仍为 `list`，新建类型时应明确写入字典，避免命令服务收到错误结构。

默认排序：`name`。

### 2.2 Sensor

| 字段 | 类型/约束 | 说明 |
|---|---|---|
| `sensor_id` | `CharField(50)`，unique，db_index | 传感器业务 ID |
| `name` | `CharField(100)` | 名称 |
| `description` | `TextField(blank=True)` | 描述 |
| `location` | `CharField(200, blank=True)` | 物理位置 |
| `mqtt_topic_data` | `CharField(200, blank=True)` | 数据主题 |
| `mqtt_topic_control` | `CharField(200, blank=True)` | 控制主题 |
| `is_online` | `BooleanField(default=False, db_index=True)` | 持久化在线标记 |
| `last_seen` | `DateTimeField(null=True, blank=True)` | 最后上报时间 |
| `sort_order` | `IntegerField(default=0, db_index=True)` | 前端排序 |
| `sensor_type` | FK → `SensorType`，`PROTECT` | 类型；有实例时禁止删除类型 |
| `created_at/updated_at` | 时间字段 | 创建/更新时间 |

默认排序：`sort_order`、`-created_at`。

保存时若 MQTT topic 为空，会生成：

```text
iot/sensors/{sensor_id}/data
iot/sensors/{sensor_id}/control
```

因此空字符串不会被长期保留；旧文档“只有 None 才自动生成”的描述已经失效。

主要行为：

- `computed_is_online`：`last_seen` 距现在小于 3 分钟。
- `update_last_seen(timestamp)`：更新 `last_seen` 并把 `is_online` 设为 `True`。
- 主模型不包含 `plant_code`、`plant_metadata` 或任何插件字段；相关历史字段已由迁移 `0006_remove_sensor_plant_fields` 删除。

### 2.3 SensorData

传感器业务采集值。

| 字段 | 类型/约束 | 说明 |
|---|---|---|
| `sensor` | FK → `Sensor`，`CASCADE`，`related_name=data_records` | 所属传感器 |
| `data` | `JSONField` | 原始采集值 |
| `timestamp` | `DateTimeField(db_index=True)` | 数据时间 |
| `received_at` | `DateTimeField(auto_now_add=True)` | 服务器接收时间 |

索引：`(sensor, -timestamp)` 和 `timestamp`；默认按 `-timestamp` 排序。

保存后调用 `sensor.update_last_seen(timestamp)`。此外，主实时层和 Project 层分别监听 `post_save`，在事务提交后推送 WebSocket 数据。

### 2.4 SensorStatusCollection

传感器状态、心跳或配置变化事件。

| 字段 | 类型/约束 | 说明 |
|---|---|---|
| `sensor` | FK → `Sensor`，`CASCADE`，`related_name=status_records` | 所属传感器 |
| `data` | `JSONField` | 状态内容 |
| `event_name` | `CharField(100, blank=True)` | `online`、`heartbeat`、`interval_updated` 等 |
| `timestamp` | `DateTimeField(db_index=True)` | 事件时间 |
| `received_at` | `DateTimeField(auto_now_add=True)` | 接收时间 |

索引与 SensorData 相同；保存后同样更新 Sensor 的最后上报时间。

## 三、设备模块（devices）

### 3.1 DeviceType

| 字段 | 类型/约束 | 说明 |
|---|---|---|
| `DeviceType_id` | `CharField(50)`，unique，db_index | 类型业务 ID |
| `name` | `CharField(50)`，unique | 类型名称 |
| `description` | `TextField(blank=True)` | 描述 |
| `config_parameters` | `JSONField(default=list)` | 所有可读状态与配置字段 |
| `commands` | `JSONField(default=dict, blank=True)` | 命令 schema 与 MQTT 模板 |
| `created_at` | `DateTimeField(auto_now_add=True)` | 创建时间 |

旧的 `state_fields` 已被移除，状态字段与配置项统一放在 `config_parameters`。

命令示例：

```json
{
  "turn_on": {
    "mqtt_message": {"command": "power_on"},
    "description": "打开设备",
    "params": []
  },
  "set_brightness": {
    "mqtt_message": {"command": "set_brightness", "value": "{val}"},
    "description": "设置亮度",
    "params": ["val"]
  }
}
```

### 3.2 Device

| 字段 | 类型/约束 | 说明 |
|---|---|---|
| `device_id` | `CharField(50)`，unique，db_index | 设备业务 ID |
| `name` | `CharField(100)` | 名称 |
| `description` | `TextField(blank=True)` | 描述 |
| `location` | `CharField(200, blank=True)` | 位置 |
| `mqtt_topic_data` | `CharField(200, blank=True)` | 状态主题 |
| `mqtt_topic_control` | `CharField(200, blank=True)` | 控制主题 |
| `is_online` | `BooleanField(default=False, db_index=True)` | 持久化在线标记 |
| `last_seen` | `DateTimeField(null=True, blank=True)` | 最后状态时间 |
| `sort_order` | `IntegerField(default=0, db_index=True)` | 前端排序 |
| `device_type` | FK → `DeviceType`，`PROTECT` | 设备类型 |
| `created_at/updated_at` | 时间字段 | 创建/更新时间 |

默认排序：`sort_order`、`-created_at`。topic 为空时自动生成：

```text
iot/devices/{device_id}/status
iot/devices/{device_id}/control
```

主要行为：

- `get_heartbeat_interval()`：当前由 DeviceType 固定返回 60 秒。
- `computed_is_online`：最后上报未超过心跳间隔 3 倍，即当前为 180 秒。
- `check_online_status()`：超时后把持久化 `is_online` 更新为 `False`。
- `update_heartbeat(timestamp)`：更新最后上报并置在线。
- `get_data_count(hours)`：统计 `status_records`。
- 主模型中的旧场景字段已由迁移 `0012_remove_device_plant_fields` 删除。

### 3.3 DeviceStatusCollection

统一保存设备状态和事件。它在迁移 `0010_unify_status_records` 后取代旧 `DeviceData` 名称。

| 字段 | 类型/约束 | 说明 |
|---|---|---|
| `device` | FK → `Device`，`CASCADE`，`related_name=status_records` | 所属设备 |
| `data` | `JSONField` | 状态内容 |
| `event_name` | `CharField(100, blank=True)` | 状态事件标签 |
| `timestamp` | `DateTimeField(db_index=True)` | 状态时间 |
| `received_at` | `DateTimeField(auto_now_add=True)` | 接收时间 |

索引：`(device, -timestamp)` 和 `timestamp`；默认按 `-timestamp` 排序。保存后使用记录自身时间戳调用 `device.update_heartbeat()`。

## 四、项目/场景模块（projects）

### 4.1 设计边界

Project 通过成员表引用全局 Sensor/Device，场景元数据不写回主模型：

```text
Sensor / Device（全局、通用）
        ↑ CASCADE 外键
ProjectSensorMember / ProjectDeviceMember（位号、阈值、区域、可见性）
```

成员、视图和控制方案必须归属 ProjectSection。成员表同时保存 `project` 和 `section`，其中 `project` 是便于查询的冗余外键；REST 序列化器以 `section.project` 为准回填并校验。数据库本身没有约束两个外键一定一致，绕过 API 直接写 ORM 时必须自行维护。

### 4.2 Project

| 字段 | 类型/约束 | 说明 |
|---|---|---|
| `code` | `CharField(30)`，unique | 项目短码 |
| `name` | `CharField(100)` | 名称 |
| `description` | `TextField(blank=True)` | 描述 |
| `scene_type` | choices | `industrial`、`smart_home`、`custom` |
| `is_active` | `BooleanField(default=True)` | 是否启用 |
| `sort_order` | `IntegerField(default=0, db_index=True)` | 排序 |
| `view_settings` | `JSONField(default=dict, blank=True)` | 项目级显示设置 |
| `created_by` | FK → User，`SET_NULL`，可空 | 创建人 |
| `created_at/updated_at` | 时间字段 | 创建/更新时间 |

默认排序：`sort_order`、`id`。

### 4.3 ProjectSection

| 字段 | 类型/约束 | 说明 |
|---|---|---|
| `project` | FK → `Project`，`CASCADE`，`related_name=sections` | 所属项目 |
| `name` | `CharField(50)` | 房间/工段名称 |
| `sort_order` | `IntegerField(default=0, db_index=True)` | 顺序 |
| `created_at/updated_at` | 时间字段 | 创建/更新时间 |

Section 是成员和视图的强制隔离边界。没有 ControlScheme 时，删除 Section 会级联删除成员和视图；存在 ControlScheme 时，方案对成员的 `PROTECT` 会先阻止整次删除，必须先删除控制方案。全局 Sensor/Device 始终不会因删除 Section 而被删除。

### 4.4 ProjectSensorMember

| 字段组 | 字段 | 说明 |
|---|---|---|
| 关联 | `project`、`section`、`sensor` | 均为 `CASCADE` 外键 |
| 点位 | `tag`、`area`、`data_key`、`unit` | 场景显示与取值字段 |
| 阈值 | `normal_value`、`hi_threshold`、`lo_threshold`、`severity` | 状态判定元数据 |
| 展示 | `sort_order`、`is_visible` | 排序与可见性 |
| 时间 | `created_at`、`updated_at` | 审计时间 |

数据库唯一约束：

```text
(section, sensor, data_key)
```

所以同一 Sensor 可以在多个房间复用，也可以在同一房间按不同 `data_key` 拆成多个点位。

`point_id`：

```text
data_key 为空 → sensor.sensor_id
data_key 有值 → sensor.sensor_id::data_key
```

### 4.5 ProjectDeviceMember

| 字段组 | 字段 | 说明 |
|---|---|---|
| 关联 | `project`、`section`、`device` | `CASCADE` 外键 |
| 场景 | `tag`、`area` | 位号与区域 |
| 展示 | `sort_order`、`is_visible` | 排序与可见性 |
| 时间 | `created_at`、`updated_at` | 审计时间 |

唯一约束为 `(section, device)`，因此同一设备可以加入不同房间，但同一房间只能绑定一次。

### 4.6 ProjectView

| 字段 | 类型/约束 | 说明 |
|---|---|---|
| `project` | FK → `Project`，`CASCADE` | 所属项目 |
| `section` | FK → `ProjectSection`，`CASCADE` | 所属房间 |
| `name` | `CharField(50)` | 视图名称 |
| `view_type` | choices | `card`、`diagram`、`timeseries`、`control` |
| `config` | `JSONField(default=dict, blank=True)` | 类型特定配置/画布 |
| `is_default` | `BooleanField(default=False)` | 默认视图标记 |
| `sort_order` | `IntegerField(default=0, db_index=True)` | 排序 |
| `created_at/updated_at` | 时间字段 | 审计时间 |

当前没有“每个房间只能有一个默认视图”的数据库唯一约束。前端会优先选择查询结果中的第一个 `is_default=True`；写接口调用方应主动清理重复默认标记。

## 五、自动化模块（automation）

### 5.1 AutomationRule

自由 Python 脚本规则，通过 JSON 清单逻辑引用 Sensor/Device。

| 字段 | 类型/约束 | 说明 |
|---|---|---|
| `name` | `CharField(100)` | 规则名称 |
| `description` | `TextField(blank=True)` | 描述 |
| `project` | FK → `Project`，`SET_NULL`，可空 | 可选场景归属；删除项目后保留为全局规则 |
| `script_id` | `CharField(50)`，unique | 脚本业务 ID，不允许空 |
| `script` | `TextField(blank=True)` | Python 脚本 |
| `device_list` | `JSONField(default=list)` | 允许脚本访问的资源清单 |
| `is_launched` | `BooleanField(default=False)` | 是否进入调度 |
| `poll_interval` | `PositiveIntegerField(default=30)` | 调度间隔 |
| `process_status` | choices | `idle`、`running`、`stopped_by_user`、`error_stopped` |
| `error_message` | `TextField(blank=True)` | 错误信息 |
| `last_run_time` | `DateTimeField(null=True, blank=True)` | 最近调度时间 |
| `created_at/updated_at` | 时间字段 | 审计时间 |

`device_list` 是应用级白名单而非数据库外键：

```json
[
  {"device_id": "DHT11-WEMOS-001", "device_type": "Sensor", "name": "温湿度"},
  {"device_id": "FAN-001", "device_type": "Device", "name": "风机"}
]
```

- Sensor 状态来源：`sensor.data_records`。
- Device 状态来源：`device.status_records`。
- 删除 Sensor/Device 不会自动修改已有规则 JSON，脚本需处理 `get()` 返回 `None`。
- 完整引擎与示例见 [AutomationRule 设计](AutomationRules_design.md)。

### 5.2 ControlScheme

结构化闭环控制，绑定 Project 成员而不是自由字符串 ID。

| 字段组 | 字段 | 说明 |
|---|---|---|
| 作用域 | `project`、`section` | `CASCADE` 外键 |
| PV | `sensor_member` | FK → ProjectSensorMember，`PROTECT` |
| 执行器 | `device_member` | FK → ProjectDeviceMember，`PROTECT` |
| 输入 | `data_key`、`setpoint` | PV 字段与 SP |
| 算法 | `control_type`、`action`、`sample_interval` | 双位/PI/PID、heat/cool、周期 |
| 输出 | `output_mode`、`params` | analog/switch 与命令映射 |
| 运行态 | `runtime_state`、`is_enabled`、`status` | 积分、上拍误差、开关/PWM 状态 |
| 观测 | `last_run_time`、`last_pv`、`last_output`、`last_command`、`error_message` | 最近执行结果 |
| 时间 | `created_at`、`updated_at` | 审计时间 |

虽然 `ControlScheme.project` / `section` 使用 `CASCADE`，但方案同时以 `PROTECT` 引用成员。实测 Django 删除收集器会优先触发该保护，因此存在控制方案时，删除 Project、Section、Sensor、Device 或成员都会失败；应先停用并删除控制方案。

当前数据库没有约束 `project`、`section`、两个 member 必须完全一致。API 序列化器校验同 Project，前端仅提供当前 Section 成员，但尚未在后端强制同 Section；直接 ORM 或自定义 API 客户端必须维护这一不变量。

## 六、平台配置模块（platform_settings）

### 6.1 PlatformConfig

| 字段 | 类型/约束 | 说明 |
|---|---|---|
| `key` | `CharField(100)`，unique | 配置键 |
| `value` | `JSONField(null=True, blank=True)` | 任意 JSON 值 |
| `category` | `CharField(50, default=general)` | 配置分组 |
| `description` | `CharField(200, blank=True)` | 说明 |
| `created_at/updated_at` | 时间字段 | 审计时间 |

默认排序：`category`、`key`。`get_value(key, default)` 在键不存在时返回默认值。

### 6.2 Plugin

| 字段 | 类型/约束 | 说明 |
|---|---|---|
| `name` | `CharField(100)`，unique | 与 `plugins/<name>` 一致 |
| `enabled` | `BooleanField(default=True)` | 是否启用 |
| `version` | `CharField(50, blank=True)` | 版本 |
| `description` | `CharField(200, blank=True)` | 描述 |
| `installed_at/updated_at` | 时间字段 | 登记/更新时间 |

该表由 `sync_plugins` 与 `plugin.json` 同步。改变启用状态后需重启 Django，HTTP/WS 动态路由才会按新状态重新挂载。

## 七、删除语义

| 删除对象 | 结果 |
|---|---|
| SensorType / DeviceType | 有实例引用时被 `PROTECT` 阻止 |
| Sensor | 级联删除数据、状态和 ProjectSensorMember；若成员被 ControlScheme 引用，`PROTECT` 会阻止整次删除 |
| Device | 级联删除状态和 ProjectDeviceMember；若成员被 ControlScheme 引用，`PROTECT` 会阻止整次删除 |
| Project | 无 ControlScheme 时级联删除 Section、成员和 View，AutomationRule 的 `project` 置空；存在 ControlScheme 时先被成员 `PROTECT` 阻止，需先删方案 |
| ProjectSection | 无 ControlScheme 时级联删除本房间成员和 View；存在 ControlScheme 时先被 `PROTECT` 阻止，需先删方案 |
| 单个 Project member | 无 ControlScheme 引用时删除；有引用时被 `PROTECT` 阻止 |
| User | `Project.created_by` 置空，Project 保留 |

## 八、模型设计约束与已知边界

1. **主模型插件清洁**：Sensor/Device 不含场景或插件字段；场景属性全部位于 Project member。
2. **类型保护**：类型实例关系使用 `PROTECT`，避免类型删除破坏已登记硬件。
3. **历史记录级联**：删除主资源时采集/状态记录随之删除。
4. **JSON 扩展**：采集值、状态、命令、视图、算法参数使用 JSONField，灵活但结构主要由 serializer/service 保证。
5. **Project 冗余外键**：成员/View 同时保存 project 与 section，API 会校验，数据库无跨表一致性约束。
6. **ControlScheme 一致性**：当前只在 API 层校验同 Project，尚未强制同 Section。
7. **ControlScheme 删除保护**：成员上的 `PROTECT` 会阻止包含该成员的 Project/Section 级联删除，必须先删除方案。
8. **默认视图**：`is_default` 没有唯一约束，可能出现多个默认项。
9. **SensorType.commands 默认值**：模型默认 `list`，业务期望命令映射字典；创建数据时需显式传入 `{}` 或实际 schema。
10. **在线状态双轨**：`is_online` 是持久化标记，页面通常应优先使用基于 `last_seen` 的 `computed_is_online`。
11. **生产数据库**：Docker 环境使用 MySQL；本地 SQLite 仅用于脱机开发，不能用于判断线上数据状态。

## 九、审核修正记录

本次对旧文档进行了以下修正：

- `DeviceData` 更名为当前的 `DeviceStatusCollection`，反向关系改为 `status_records`。
- 删除已经不存在的 `DeviceType.state_fields`，说明字段已合并到 `config_parameters`。
- 修正 Sensor/Device topic 自动填充条件：当前为空即填充，不是仅 `None`。
- 补充 Sensor/Device 的 `sort_order`、实时在线属性和主模型场景字段移除事实。
- 补充 AutomationRule 的 `project`、`last_run_time`、函数式脚本现状及正确数据来源。
- 新增完整 Project、ProjectSection、成员、View 和 ControlScheme 模型设计。
- 补充房间级唯一约束、CASCADE/PROTECT/SET_NULL 删除语义。
- 通过内存数据库验证 ControlScheme 的 `PROTECT` 会阻止 Project/Section 的级联删除，修正旧说明。
- 明确 Project 冗余外键、默认视图和 ControlScheme 同房间约束目前主要依赖应用层。

## 十、相关文档

- [Project 场景模块设计](project_design.md)
- [Project 使用指南](../backend_user_guide/project_guide.md)
- [AutomationRule 设计与示例](AutomationRules_design.md)
- [平台配置设计](platform_settings_design.md)
- [MQTT 服务设计](mqtt_service_design.md)
