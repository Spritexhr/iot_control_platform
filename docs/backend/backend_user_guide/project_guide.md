# Project 项目/场景使用指南

本文档介绍如何创建 Project、组织房间、导入点位、搭建卡片/P&ID/趋势视图并配置结构化控制方案。内部模型与实时架构见 [Project 模块设计](../backend_design/project_design.md)。

## 一、使用前准备

Project 不生成演示数据。请先在平台中创建真实的：

- `SensorType` 与 `Sensor`
- `DeviceType` 与 `Device`
- 正确的 MQTT data/status/control topic
- DeviceType 中可实际执行的命令模板

生产环境实际数据位于 Docker MySQL。检查或修改线上数据时使用：

```bash
docker exec iot-backend python manage.py shell -c "..."
```

不要用本地 `db.sqlite3` 判断线上资源是否存在。

## 二、创建场景

### 2.1 创建 Project

进入左侧“项目/场景”，工作人员点击“新建项目”：

| 配置 | 建议 |
|---|---|
| 项目代号 | 简短且唯一，如 `EB`、`ST`、`HOME` |
| 场景类型 | 工业装置、智能家居或自定义 |
| 名称 | 使用清晰的业务名称 |
| 描述 | 说明装置范围、用途或责任人 |

项目代号会进入实时样本元数据，不建议创建后频繁修改。

### 2.2 创建房间/工段

打开项目配置页，在左侧新建 section：

- 工业场景：反应工段、精馏工段、泵房、公用工程。
- 家居场景：客厅、卧室、厨房。
- 实验场景：反应区、采集区、控制区。

section 可以重命名和排序。没有控制方案时，删除 section 会删除其成员和视图，但不会删除全局传感器或设备；存在 ControlScheme 时删除会被 `PROTECT` 拒绝，必须先在控制视图中删除相关方案。

## 三、导入传感器和设备

### 3.1 导入传感器

在当前房间的“传感器”页签选择全局 Sensor 并导入。

如果 `SensorType.data_fields` 为：

```json
["temperature", "pressure"]
```

系统自动生成：

```text
SENSOR-01::temperature
SENSOR-01::pressure
```

分别配置：

| 字段 | 用途 |
|---|---|
| 位号 `tag` | 工程显示名，如 `TI-101` |
| 单位 `unit` | `°C`、`kPa`、`L/min` 等 |
| 低/高阈值 | 卡片和仪表节点的状态判定 |
| 严重度 | `low`、`mid`、`high`、`critical` |
| 显示 | 是否进入 layout、snapshot 和工作台 |

同一传感器可加入多个房间；同一房间内不能重复添加相同 `data_key`。

### 3.2 导入设备

在“设备”页签导入执行器，并配置位号、区域和可见性。设备卡片的命令来自 DeviceType，不在 Project 中重复定义。

同一设备可以加入不同房间；同一房间内只能出现一次。

### 3.3 移动与删除成员

- 成员可以移动到其他 section。
- 目标 section 已存在相同点位或设备时，移动会被唯一约束拒绝。
- 删除成员只解除场景绑定。
- 被 ControlScheme 引用的成员不能直接删除，应先停用并删除对应控制方案。

## 四、配置视图

在房间的“视图”页签填写名称并选择类型。可将常用视图设为默认。

### 4.1 卡片大屏

适合快速投用，无需额外画布配置：

- 实时显示数值、单位、在线状态和更新时间。
- 根据高低阈值显示正常、告警状态。
- 支持名称/位号搜索。
- 支持全部、仅在线、报警/离线筛选。
- 工作人员可以在设备卡片中发送命令。

如果房间没有创建任何视图，工作台也会临时显示一个默认卡片大屏。

### 4.2 工艺流程图

创建 `diagram` 视图后进入工作台：

1. 点击“编辑模式”。
2. 从左侧工具箱拖入仪表、容器、阀门、泵、塔或其他图元。
3. 通过连接点绘制管线。
4. 在属性面板为仪表节点绑定本房间传感器点位。
5. 配置标签和显示属性。
6. 保存后切换到预览模式。

只有本视图所属 section 的成员会出现在绑定列表中。当前 InstrumentNode 已实现传感器绑定；PropertiesPanel 已预留设备绑定能力，但泵、阀等通用图元尚未声明 `bindable: ['device']`。画布保存为 ProjectView 的 `config` JSON，实时值不会写入画布。

### 4.3 时序趋势

创建 `timeseries` 视图后：

1. 选择当前房间的传感器或设备。
2. 选择一个或多个字段。
3. 选择近 1 小时、6 小时、24 小时、7 天或自定义范围。
4. 点击“查询刷新”。
5. 工作人员可保存为该视图的默认配置。

返回数据超过限制时，界面使用最近的数据；大量历史分析应缩短时间窗口或另建聚合接口。

### 4.4 自动化控制

创建 `control` 视图后可以管理双位、PI、PID 控制方案：

1. 选择当前 section 的 PV 传感器成员。
2. 选择数据字段和执行器设备成员。
3. 设置 SP、加热/冷却作用方向和采样周期。
4. 选择开关量或模拟量输出。
5. 填写算法参数与设备命令映射。
6. 保存后先执行“单拍测试”。
7. 检查 PV、输出、命令和错误信息，再启用连续运行。

#### 双位控制

适合继电器、电磁阀等开关执行器。死区可避免 PV 在 SP 附近波动时频繁启停。

#### PI/PID

适合调节阀、舵机等连续执行器：

- `Kp`：响应强度。
- `Ki`：消除稳态误差。
- `Kd`：抑制快速变化，仅 PID 使用。
- `out_min/out_max`：控制输出边界。

参数整定应从保守值开始。控制命令会实际通过 MQTT 下发，生产设备启用前必须确认作用方向、量程和安全联锁。

## 五、工业场景示例：苯乙烯装置

以下示例吸收自旧 EB/ST 实施方案，用于说明如何把工艺装置映射到通用 Project；它不是生产种子数据，所有资源需由用户手动创建。

### 5.1 建议结构

```text
苯乙烯装置（ST）
├── 反应工段
│   ├── 反应器进口温度/压力
│   ├── 反应器出口温度
│   └── 进料流量与进料泵
├── 换热冷凝工段
│   ├── 换热后温度
│   ├── 冷凝出口温度
│   └── 冷却水泵
└── 公用工程
    └── 蒸汽流量
```

### 5.2 点位配置参考

| 位号 | Sensor ID | data_key | 单位 | 用途 |
|---|---|---|---|---|
| `TI-101` | `ST-TP-R01-IN` | `temperature` | `°C` | 反应器进口温度 |
| `PI-101` | `ST-TP-R01-IN` | `pressure` | `kPa` | 反应器进口压力 |
| `TI-102` | `ST-TP-R01-OUT` | `temperature` | `°C` | 反应器出口温度 |
| `TI-103` | `ST-TP-HE01` | `temperature` | `°C` | 换热后温度 |
| `TI-104` | `ST-TP-CD01` | `temperature` | `°C` | 冷凝出口温度 |
| `FI-101` | `ST-FLOW-FEED` | `flow_rate` | `L/min` | 进料流量 |
| `FI-102` | `ST-FLOW-STEAM` | `flow_rate` | `L/min` | 蒸汽流量 |

| 位号 | Device ID | 用途 |
|---|---|---|
| `P-101` | `ST-PUMP-FEED` | 进料泵 |
| `P-102` | `ST-PUMP-CW` | 冷却水泵 |

阈值应来自真实工艺设计或实验标定，不要直接把示例数字写入生产环境。

### 5.3 P&ID 布局参考

在 diagram 视图中按物料方向布置：

```text
进料泵 P-101
  → FI-101
  → 反应器 R-101（TI-101 / PI-101 / TI-102）
  → 换热器 E-101（TI-103）
  → 冷凝器 C-101（TI-104）
```

仪表节点绑定具体 `point_id`。当前泵和其他工艺设备节点作为纯图元使用；若需绑定 Device，应按第六章先为对应 type 开启设备绑定并实现运行态行为。

### 5.4 ID 与位号命名

建议资源 ID：

```text
{项目}-{类型}-{区域}-{序号}

ST-TP-R01-IN
ST-FLOW-FEED
ST-PUMP-CW
```

常用 ISA 风格位号：

```text
T 温度  P 压力  F 流量  L 液位
I 指示  R 记录  C 控制  A 报警

TI-101   温度指示
PIA-102  压力指示并报警
FIC-103  流量指示控制
```

## 六、扩展 P&ID 图元

当前图元使用集中注册表，不再采用旧插件文档中的“三处同步修改”方式。

### 6.1 添加普通静态图元

编辑：

```text
frontend/src/views/projects/diagram/editor/symbols.js
```

1. 在 `SIMPLE_SYMBOLS` 增加定义。
2. 在 `ORDER` 中加入 type，决定工具箱顺序。
3. 重新构建前端。

示例：

```javascript
export const SIMPLE_SYMBOLS = {
  // ...已有图元
  tank: {
    label: '储罐',
    group: '仪表/容器',
    defaultData: { label: 'V-1' },
    size: { w: 70, h: 100 },
    viewBox: '0 0 70 100',
    labelMode: 'below',
    draw: [
      { el: 'ellipse', cx: 35, cy: 12, rx: 28, ry: 8 },
      { el: 'line', x1: 7, y1: 12, x2: 7, y2: 88 },
      { el: 'line', x1: 63, y1: 12, x2: 63, y2: 88 },
      { el: 'ellipse', cx: 35, cy: 88, rx: 28, ry: 8 },
    ],
  },
}

const ORDER = [
  // ...已有 type
  'tank',
]
```

`nodeTypes.js` 会把所有 `SIMPLE_SYMBOLS` 自动注册为通用 `SymbolNode`，工具箱预览与运行态也使用同一几何定义；后端 JSONField 无需 migration。

支持的基础几何元素包括 `line`、`polyline`、`rect`、`circle`、`ellipse`、`polygon`、`path` 和 `text`。

### 6.2 添加专用交互图元

需要实时值、特殊属性、动态形状或自定义连接点时：

1. 在 `diagram/editor/nodes/` 新建 Vue 组件。
2. 参考 `InstrumentNode.vue` 接收 Vue Flow props 和 Project Store 数据。
3. 在 `nodeTypes.js` 显式注册专用 type。
4. 在 `symbols.js` 的专用 palette 定义中提供工具箱预览。
5. 同时验证 `DiagramEditor` 与 `DiagramRuntime`。

新增 type 会直接保存在画布 JSON 中。删除或重命名已有 type 会影响旧画布，应提供迁移或兼容映射。

## 七、验收检查

### 7.1 数据与实时链路

- MQTT 上报后，生产 MySQL 中出现新的 SensorData/DeviceStatusCollection。
- `GET /api/projects/<id>/snapshot/` 返回所有可见成员。
- 浏览器 `/ws/projects/<id>/` 状态为已连接。
- 新数据到达后卡片和仪表节点无需刷新即可更新。

### 7.2 场景隔离

- 每个视图只显示所属 section 的成员。
- 同一传感器可以在不同 section 使用不同位号和阈值。
- 删除成员不影响全局 Sensor/Device。
- 普通用户不能进入写接口或控制设备。

### 7.3 画板

- 保存、刷新后节点、连线和 viewport 保持。
- 绑定点位显示正确字段和单位。
- 越限时仪表状态正确变化。
- 编辑模式仅对工作人员开放。

### 7.4 控制方案

- 单拍测试能读取正确 PV。
- heat/cool 方向与现场执行器一致。
- 输出边界与设备量程一致。
- MQTT 命令名称和参数与 DeviceType.commands 一致。
- 停用后不再产生新命令。

## 八、常见问题

| 现象 | 检查 |
|---|---|
| 导入后看不到点位 | 成员是否属于当前 section、`is_visible` 是否开启 |
| 多字段值显示 `--` | `data_key` 是否与 SensorData.data 键一致 |
| WebSocket 未授权 | Access Token 是否有效；关闭码 4001 后检查刷新流程 |
| 设备卡片无命令 | DeviceType.commands 是否定义，当前用户是否为 staff |
| 趋势无数据 | 数据源、字段和时间窗口是否正确，数据库是否有历史记录 |
| 画板节点不更新 | binding 是否使用正确 point_id，Project WebSocket 是否已连接 |
| 成员无法删除 | 是否被 ControlScheme 的 `PROTECT` 外键引用 |
| 控制方案立即报错 | PV 缺失/不可转数值、命令映射或设备确认是否失败 |

## 九、前端发布

Project 前端由 nginx 提供构建产物，修改源码后必须重建：

```bash
cd /Users/xhr_mac/server/iot_control_platform/frontend
npm run build

cd /Users/xhr_mac/server/iot_control_platform
docker compose build frontend
docker compose up -d frontend
```

验证产物 hash：

```bash
docker exec iot-frontend sh -c "grep -o 'index-[A-Za-z0-9_-]*\.js' /usr/share/nginx/html/index.html"
```
