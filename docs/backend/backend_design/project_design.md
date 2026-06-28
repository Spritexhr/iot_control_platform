# Project 项目/场景模块设计

本文档说明平台原生 Project 模块的数据边界、模型、API、实时通道、视图架构及结构化控制方案。操作步骤和工业场景示例见 [Project 使用指南](../backend_user_guide/project_guide.md)。

## 一、模块定位

Project 把全局传感器和设备组织成具体业务场景，并统一承载监控、流程图、历史趋势和闭环控制：

```text
Project（项目/场景）
└── ProjectSection（房间/工段）
    ├── ProjectSensorMember（传感器点位）
    ├── ProjectDeviceMember（执行设备）
    ├── ProjectView（卡片/流程图/趋势/控制）
    └── ControlScheme（双位/PI/PID）
```

该模块吸收了原 `eb_plant` 的分区与大屏、原 `plant_diagram` 的 P&ID 画板，以及 `data_viz` 中适合场景内使用的趋势能力。`eb_plant` 和 `plant_diagram` 已删除；独立 `data_viz` 插件仍可用于全局查询。

## 二、核心边界

### 2.1 主模型不承载场景字段

`Sensor` / `Device` 只保存通用身份、类型、通信与状态信息。位号、工段、单位、阈值、严重度等场景属性存放在 Project 成员表中。

```text
Sensor / Device（全局资源）
        ↑ 外键引用
ProjectSensorMember / ProjectDeviceMember（场景配置）
```

同一资源可以加入不同项目或不同房间，并拥有不同的展示配置。Project 删除或成员解绑不会删除主资源。

### 2.2 Section 是隔离边界

成员、视图和控制方案必须属于一个 `ProjectSection`。序列化器以 `section.project` 为准回填冗余 `project` 外键，并拒绝跨项目组合。

- 传感器成员唯一约束：`(section, sensor, data_key)`。
- 设备成员唯一约束：`(section, device)`。
- 视图只向前端提供本房间成员作为绑定候选。
- 控制方案的传感器成员、设备成员和 section 必须属于同一项目。前端只提供当前 section 的成员；当前后端序列化器尚未额外强制两个成员与 section 完全相同，直接调用 API 时需由调用方保持一致。

### 2.3 静态配置与运行数据分离

- Project 表保存布局、阈值、画布和默认选项。
- `SensorData` / `DeviceStatusCollection` 保存运行记录。
- `ProjectView.config` 不保存实时值。
- 工作台通过快照加 WebSocket 增量组合当前状态。

## 三、数据模型

### 3.1 Project

| 字段 | 说明 |
|---|---|
| `code` | 唯一短码，如 `EB`、`ST`、`HOME` |
| `name` | 项目名称 |
| `scene_type` | `industrial`、`smart_home`、`custom` |
| `is_active` | 是否启用 |
| `sort_order` | 列表排序 |
| `view_settings` | 项目级展示设置 JSON |
| `created_by` | 创建人 |

### 3.2 ProjectSection

代表工段、区域或房间。成员和视图均为必选外键。无控制方案时删除 section 会级联删除成员和视图；存在 ControlScheme 时，方案对成员的 `PROTECT` 会阻止删除，必须先删除控制方案。

### 3.3 ProjectSensorMember

| 字段组 | 字段 |
|---|---|
| 关联 | `project`、`section`、`sensor` |
| 点位 | `tag`、`area`、`data_key`、`unit` |
| 阈值 | `normal_value`、`hi_threshold`、`lo_threshold`、`severity` |
| 展示 | `sort_order`、`is_visible` |

`point_id` 规则：

```text
data_key 为空   → sensor_id
data_key 非空   → sensor_id::data_key
```

批量导入时，后端按 `SensorType.data_fields` 自动拆分多字段传感器；单字段或缺少字段元数据时生成一个空 `data_key` 成员。

### 3.4 ProjectDeviceMember

保存 `project`、`section`、`device` 以及场景内的 `tag`、`area`、排序和可见性。设备命令 schema 由序列化器从 `DeviceType.commands` 提取，隐藏内部 MQTT 模板，仅向前端暴露名称、描述、参数和确认标记。

### 3.5 ProjectView

| 类型 | 用途 | `config` 内容 |
|---|---|---|
| `card` | 实时卡片大屏 | 网格等显示设置 |
| `diagram` | P&ID/场景流程图 | Vue Flow canvas：viewport、nodes、edges |
| `timeseries` | 历史趋势 | 默认数据源、字段和时间范围 |
| `control` | 结构化闭环控制入口 | 当前主要由 `ControlScheme` 表保存配置 |

`config` 使用 JSONField，便于不同视图独立演进。画布节点只存绑定 ID 和静态样式，运行时数据从 Project Store 注入。

## 四、REST API

所有接口位于 `/api` 下。

### 4.1 聚合接口

| 接口 | 说明 |
|---|---|
| `/projects/` | 项目 CRUD |
| `/projects/<id>/layout/` | 有序 section 及其可见成员元数据 |
| `/projects/<id>/snapshot/` | 所有可见成员的最新传感器值和设备状态 |
| `/projects/<id>/bindable_sources/` | 可导入的全局 Sensor / Device |
| `/projects/<id>/series/` | 指定传感器或设备的时间窗记录 |

`snapshot` 直接查询数据库最新记录，不依赖进程缓存。原因是同一点位可能被多个项目/房间复用，用单一 `point_id` 缓存会发生场景覆盖。

时序查询默认最近 24 小时、最多 2,000 条，允许的硬上限为 10,000 条；返回原始点、字段列表、状态事件和截断标记。

### 4.2 子资源接口

| 接口 | 说明 |
|---|---|
| `/project_sections/` | section CRUD 与 `reorder` |
| `/project_sensor_members/` | 成员 CRUD、多字段批量导入 |
| `/project_device_members/` | 设备成员 CRUD、批量导入 |
| `/project_views/` | 视图 CRUD |

子资源使用 `?project=<id>` 过滤；成员和视图还支持 `?section=<id>`。

## 五、实时架构

### 5.1 初始化与增量

```text
浏览器进入 ProjectWorkspace
  ├── GET layout      → 静态分区/成员结构
  ├── GET snapshot    → 数据库最新状态
  └── WS /ws/projects/<project_id>/?token=<jwt>
          ├── snapshot
          ├── sample
          └── device.status
```

WebSocket Consumer 建连后也会发送一次 snapshot，用于覆盖 REST 与建连之间可能出现的状态变化。

### 5.2 传感器流

```text
SensorData post_save
  → projects.signals 查询可见 ProjectSensorMember
  → build_point_sample(binding)
  → 按 (project_id, point_id) 去重
  → transaction.on_commit
  → projects.<project_id>
```

样本沿用通用 `PointSample` 结构，其中 `plugin_code` 字段承载 project code。这是实时 DTO 的历史命名，不表示 Project 依赖具体插件。

### 5.3 设备流

项目 Consumer 同时订阅 `devices.all`，根据建连时取得的已绑定设备 ID 集合过滤，只转发当前项目设备状态。

### 5.4 前端状态

`frontend/src/stores/project.js` 使用两个 Map：

- `samples: Map<point_id, PointSample>`
- `devices: Map<device_id, DeviceState>`

`findByBinding()` 同时支持完整 `sensor_id::data_key` 和单纯 `sensor_id` 回退。

## 六、视图前端架构

### 6.1 工作台

`ProjectWorkspace.vue` 负责项目标题、连接状态、section 导航和视图 tab。当前房间无持久化视图时，会生成一个仅存在于前端的默认卡片页。

### 6.2 卡片视图

`CardDashboard.vue` 按 section 渲染 InstrumentCard 和 DeviceCard，支持搜索、在线/报警过滤。设备控制按钮由 `is_staff` 控制。

### 6.3 Diagram 视图

画布由 Vue Flow 渲染：

```json
{
  "version": 1,
  "viewport": {"x": 0, "y": 0, "zoom": 1},
  "nodes": [],
  "edges": []
}
```

- `DiagramEditor`：编辑、拖放、连线和属性配置。
- `DiagramRuntime`：只读运行态和实时值展示。
- `symbols.js`：通用工业图元的唯一注册表；当前只有 InstrumentNode 启用了传感器绑定，设备绑定扩展点已预留但尚未为泵/阀等图元开启。
- `nodeTypes.js`：把专用 InstrumentNode 和通用 SymbolNode 注册到 Vue Flow。
- `SymbolGlyph`：按注册表几何定义绘制 SVG。

### 6.4 Timeseries 视图

ECharts 根据 `/series/` 返回值动态生成曲线，支持多个字段、快捷时间范围、自定义时间和状态事件线。心跳事件在前端过滤，不显示为事件标记。

## 七、结构化控制方案

`ControlScheme` 位于 automation app，与自由脚本 `AutomationRule` 并存。

### 7.1 绑定与配置

```text
ProjectSection
  ├── ProjectSensorMember → PV
  ├── ProjectDeviceMember → 执行器
  └── ControlScheme
        ├── SP / action / sample_interval
        ├── on_off / PI / PID
        └── analog / switch 输出映射
```

核心字段包括 `setpoint`、`action`、`control_type`、`sample_interval`、`output_mode`、`params`、`runtime_state`、最近 PV/输出/命令及错误状态。

传感器和设备成员使用 `PROTECT`，防止单独删除成员造成静默失控。删除整个 section 时控制方案本身随 section 级联删除。

### 7.2 算法与执行

- 双位：带回差，死区内保持上一拍状态。
- PI：比例、积分、输出限幅和抗积分饱和。
- PID：在 PI 上增加误差微分项。
- `heat`：PV 低于 SP 时增大输出。
- `cool`：PV 高于 SP 时增大输出。
- `analog`：输出映射为设备命令参数。
- `switch`：输出映射为开/关命令，可选阈值或 PWM 转换。

调度器只在生产 `iot-mqtt-runner` 单实例运行，避免多 worker 重复控制。API 提供模板、CRUD、启用、停用和单拍测试。

## 八、权限与删除语义

| 操作 | 权限 |
|---|---|
| 查看项目、布局、快照、历史和视图 | 已登录用户 |
| 项目、section、成员、视图写操作 | 工作人员 |
| 查看 ControlScheme | 已登录用户 |
| ControlScheme 启停与单拍 | 工作人员 |
| ControlScheme 增删改 | 超级用户 |

删除关系：

```text
删除 Project
  → 无 scheme 时删除 sections / members / views
  → 有 scheme 时被成员 PROTECT 阻止，需先删除 scheme
  → Sensor / Device 保留

删除 Section
  → 无 scheme 时删除本 section 的 members / views
  → 有 scheme 时被成员 PROTECT 阻止，需先删除 scheme
  → Sensor / Device 保留

删除 Sensor / Device
  → 无控制方案引用时，对应 Project member 随主资源级联删除
  → 有 ControlScheme 引用时，成员上的 PROTECT 会阻止删除
```

生产数据变更必须通过 `iot-backend` 容器连接 MySQL，不得依据本地 SQLite 判断实际状态。

## 九、关键代码

| 内容 | 路径 |
|---|---|
| 模型 | `iot_control_platform/projects/models.py` |
| 序列化 | `iot_control_platform/projects/serializers.py` |
| REST API | `iot_control_platform/projects/views.py` |
| 实时信号 | `iot_control_platform/projects/signals.py` |
| WebSocket | `iot_control_platform/projects/consumers.py` |
| 控制模型 | `iot_control_platform/automation/models.py` |
| 控制算法 | `iot_control_platform/automation/controllers.py` |
| 调度器 | `iot_control_platform/automation/scheduler.py` |
| 工作台 | `frontend/src/views/projects/ProjectWorkspace.vue` |
| 配置页 | `frontend/src/views/projects/ProjectConfigView.vue` |
| 画板 | `frontend/src/views/projects/diagram/` |
| 实时 Store | `frontend/src/stores/project.js` |
