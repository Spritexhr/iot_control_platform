# IoT 控制平台 - 前端设计说明

本文档描述物联网控制平台前端的架构设计、技术选型、页面规划及实现要点，供开发与维护参考。

---

## 一、技术栈

| 类别 | 技术 | 版本 / 说明 |
|------|------|-------------|
| 框架 | Vue 3 | Composition API + `<script setup>` 语法 |
| 构建工具 | Vite | 5.x，快速 HMR，ESM 原生支持 |
| 路由 | Vue Router 4 | 路由守卫、动态加载 |
| 状态管理 | Pinia | 轻量级，组合式 API 友好 |
| UI 组件库 | Element Plus | 管理后台常用组件 |
| HTTP 请求 | Axios | 统一封装、拦截器、Token 刷新 |
| 样式 | SCSS + CSS 变量 | 主题切换、设计规范 |
| 图标 | Element Plus Icons | Odometer、Cpu、Monitor 等 |

**设计阶段规划、当前未实现**：
- 图表：ECharts（传感器数据趋势、设备在线分布）
- 实时通信：MQTT.js 订阅（当前采用 REST 轮询 + 后端 MQTT）
- 代码编辑器：Monaco Editor（当前为 textarea 脚本编辑）

---

## 二、总体布局

### 2.1 布局结构

采用经典管理后台布局：**可折叠侧边栏 + 顶部导航栏 + 主内容区**。

```
+---------------------------------------------------------------+
|  Logo/Title       [MQTT状态] [主题] [全屏] [用户菜单]          |
+-------------+-------------------------------------------------+
|             |                                                 |
|   侧边栏     |              主内容区                            |
|   导航菜单   |           (Router View)                         |
|             |                                                 |
|  - 仪表盘    |   +-------------------------------------------+ |
|  - 传感器    |   |  面包屑 / 页面标题                          | |
|  - 设备      |   +-------------------------------------------+ |
|  - 自动化    |   |                                           | |
|  - 系统设置  |   |           页面具体内容                      | |
|             |   |                                           | |
|  [折叠按钮]  |   +-------------------------------------------+ |
+-------------+-------------------------------------------------+
```

### 2.2 布局组件

| 组件 | 文件 | 说明 |
|------|------|------|
| AppLayout | `layouts/AppLayout.vue` | 主布局，侧边栏 + 顶栏 + 内容 |
| AppSidebar | `layouts/AppSidebar.vue` | 侧边栏，Logo、导航菜单、折叠按钮 |
| AppHeader | `layouts/AppHeader.vue` | 顶栏，面包屑、MQTT 状态、主题、全屏、用户菜单 |
| AppMain | `layouts/AppMain.vue` | 主内容区，`<router-view />` |

### 2.3 响应式策略

| 屏幕宽度 | 侧边栏行为 |
|----------|-----------|
| ≥ 1200px | 展开（220px） |
| 768px ~ 1199px | 折叠（64px，仅图标） |
| < 768px | 隐藏，通过汉堡按钮打开抽屉式侧边栏 |

---

## 三、页面设计

### 3.1 路由与权限

#### 3.1.1 路由表

| 路径 | 名称 | 组件 | 权限 |
|------|------|------|------|
| `/login` | 登录 | LoginView | guest |
| `/register` | 注册 | RegisterView | guest |
| `/` | 仪表盘 | DashboardView | requiresAuth |
| `/sensors` | 传感器管理 | SensorsView | requiresAuth |
| `/sensors/:sensorId` | 传感器详情 | SensorDetailView | requiresAuth |
| `/devices` | 设备管理 | DevicesView | requiresAuth |
| `/devices/:deviceId` | 设备详情 | DeviceDetailView | requiresAuth |
| `/automation` | 自动化规则 | AutomationView | requiresAuth |
| `/automation/:id` | 规则详情 / 编辑 | AutomationDetailView | requiresAuth |
| `/settings` | 系统设置 | SettingsView | requiresAuth |

#### 3.1.2 路由守卫

- `requiresAuth`：需 JWT Token，否则跳转 `/login`
- `guest`：已登录时跳转 `/`
- 页面标题：`document.title = {title} - IoT 控制平台`

### 3.2 仪表盘（Dashboard）

**路由**：`/`

**功能**：平台整体运行状态一览。

- **统计卡片**：传感器总数 / 在线、设备总数 / 在线、自动化规则数、24h 数据量
- **传感器最新数据**：表格展示最近上报的传感器及数据
- **设备在线状态**：饼图或统计展示
- **最近活动日志**：操作记录列表（若有）

数据来源：`/api/dashboard/stats/` 接口。

### 3.3 传感器管理

#### 3.3.1 传感器列表（/sensors）

- 筛选：类型、在线 / 离线 / 全部
- 卡片网格：每张卡片显示类型名、状态灯、名称、最新数据、位置、最后上报时间
- 操作：点击卡片进入详情，删除等

#### 3.3.2 传感器详情（/sensors/:sensorId）

- 基本信息：ID、类型、位置、描述、MQTT 主题、最后上报时间
- 最新数据：根据 `data_fields` 动态展示
- 命令控制：`CommandPanel` 根据 `commands` 动态渲染
- 历史数据：时间范围筛选 + 表格
- 状态记录：`SensorStatusCollection` 时间线

### 3.4 设备管理

#### 3.4.1 设备列表（/devices）

- 卡片展示：图标、名称、状态字段（布尔型用开关）、在线状态
- 操作：控制面板、详情

#### 3.4.2 设备详情（/devices/:deviceId）

- 基本信息：设备 ID、类型、MQTT 主题、位置等
- 命令控制：根据 `DeviceType.commands` 动态渲染
- 状态记录：`DeviceData` 时间线

### 3.5 自动化规则

#### 3.5.1 规则列表（/automation）

- 规则卡片：名称、script_id、关联设备、启用开关、编辑 / 测试 / 删除

#### 3.5.2 规则编辑（/automation/:id）

- 基本信息：名称、脚本 ID、描述
- 关联设备：device_list，支持添加 / 删除
- 脚本编辑器：textarea 编辑 Python 脚本（设计规划为 Monaco Editor）
- 执行测试、保存

### 3.6 系统设置（/settings）

- MQTT 连接状态：Broker、端口、连接状态
- 传感器类型管理：SensorType CRUD
- 设备类型管理：DeviceType CRUD

---

## 四、组件设计

### 4.1 公共组件

| 组件名 | 文件路径 | 说明 |
|--------|---------|------|
| CommandPanel | `components/common/CommandPanel.vue` | 通用命令面板，根据 commands 动态渲染按钮和参数 |

### 4.2 业务组件

| 组件名 | 文件路径 | 说明 |
|--------|---------|------|
| SensorCard | `components/sensors/SensorCard.vue` | 传感器卡片，状态、类型、数据、位置 |
| SensorDetail | `components/sensors/SensorDetail.vue` | 传感器详情（部分页面复用） |
| DeviceCard | `components/devices/DeviceCard.vue` | 设备卡片 |

### 4.3 CommandPanel 核心逻辑

Props：
- `commands`：来自 SensorType.commands 或 DeviceType.commands
- `deviceId`：设备 / 传感器 ID
- `sendFn`：发送命令函数 `(deviceId, commandName, params, makeSure) => Promise`

渲染逻辑：
- 遍历 `commands` 的每个 key
- 无参数：渲染按钮
- 有参数：渲染输入框 + 执行按钮
- 执行后显示“已确认”或“失败”

---

## 五、样式与主题

### 5.1 配色方案

#### 亮色主题（默认）

| 用途 | 色值 |
|------|------|
| 主色 | `#1A73E8` |
| 成功 / 在线 | `#00BFA5` |
| 警告 | `#FF9800` |
| 危险 / 离线 | `#F44336` |
| 背景 | `#F5F7FA` |
| 侧边栏 | `#1E293B` |
| 卡片 | `#FFFFFF` |

#### 暗色主题

| 用途 | 色值 |
|------|------|
| 主色 | `#409EFF` |
| 背景 | `#0D1117` |
| 侧边栏 | `#161B22` |
| 卡片 | `#1C2333` |

### 5.2 设计规范

- **圆角**：卡片 `12px`，按钮 `8px`
- **阴影**：`0 2px 12px rgba(0,0,0,0.08)`
- **间距**：8px 倍数（8 / 16 / 24 / 32）
- **字体**：Inter、PingFang SC、Microsoft YaHei
- **变量**：`variables.scss` 中定义，`html.dark` 覆盖暗色变量

### 5.3 状态指示

- 在线：绿色圆点 `iot-status-dot--online`
- 离线：灰色圆点 `iot-status-dot--offline`
- MQTT：顶栏显示“MQTT”+ 状态点（绿色 / 灰色）

---

## 六、目录结构

```
frontend/
├── public/
├── src/
│   ├── api/                      # API 请求
│   │   ├── index.js              # Axios 实例、Token 刷新
│   │   ├── auth.js               # 登录、注册、个人信息、改密
│   │   ├── sensors.js            # 传感器 / SensorType
│   │   ├── devices.js            # 设备 / DeviceType
│   │   ├── automation.js         # 自动化规则
│   │   └── system.js             # MQTT 状态、仪表盘统计
│   ├── assets/styles/
│   │   ├── variables.scss        # CSS 变量、主题
│   │   └── global.scss           # 全局样式
│   ├── components/
│   │   ├── common/               # 通用组件
│   │   │   └── CommandPanel.vue
│   │   ├── sensors/
│   │   │   ├── SensorCard.vue
│   │   │   └── SensorDetail.vue
│   │   └── devices/
│   │       └── DeviceCard.vue
│   ├── layouts/
│   │   ├── AppLayout.vue
│   │   ├── AppSidebar.vue
│   │   ├── AppHeader.vue
│   │   └── AppMain.vue
│   ├── router/index.js           # 路由 + 守卫
│   ├── stores/
│   │   ├── app.js                # 主题、侧边栏、抽屉
│   │   └── user.js               # 用户信息、Token
│   ├── utils/
│   │   └── theme.js              # 主题初始化
│   ├── views/
│   │   ├── auth/                 # 登录、注册
│   │   ├── dashboard/
│   │   ├── sensors/
│   │   ├── devices/
│   │   ├── automation/
│   │   └── settings/
│   ├── App.vue
│   └── main.js
├── index.html
├── vite.config.js
├── package.json
├── Dockerfile
└── nginx.conf
```

---

## 七、数据流与接口

### 7.1 认证与请求

- **登录**：POST `/api/auth/login/` 获取 access + refresh Token
- **Token 存储**：`localStorage`（iot-access-token、iot-refresh-token）
- **请求头**：`Authorization: Bearer {token}`
- **401 处理**：优先使用 refresh Token 换取新 access Token，失败则跳转登录

### 7.2 数据获取策略

| 数据类型 | 获取方式 |
|----------|---------|
| 列表、详情 | REST API |
| MQTT 状态 | 轮询 `/api/mqtt/status/`（15s） |
| 命令发送 | POST 到后端，后端转发 MQTT |

当前未实现：前端 MQTT 订阅，实时数据由后端接收后经 API 或轮询提供。

### 7.3 主要 API 模块

- **auth**：login, refresh, register, profile, change-password
- **sensors**：getSensors, getSensor, getSensorData, sendSensorCommand, sensor-types CRUD
- **devices**：getDevices, getDevice, sendDeviceCommand, device-types CRUD
- **automation**：getRules, create/update/delete, execute
- **system**：getMqttStatus, getDashboardStats

---

## 八、侧边栏导航

| 图标 | 名称 | 路由 |
|------|------|------|
| Odometer | 仪表盘 | `/` |
| Cpu | 传感器管理 | `/sensors` |
| Monitor | 设备管理 | `/devices` |
| SetUp | 自动化规则 | `/automation` |
| Setting | 系统设置 | `/settings` |

---

## 九、开发与部署

### 9.1 开发

```bash
npm install
npm run dev
```

- 开发地址：`http://localhost:5173`
- API 代理：`/api` → `http://127.0.0.1:8000`

### 9.2 构建与预览

```bash
npm run build    # 输出 dist/
npm run preview  # 本地预览构建结果
```

### 9.3 部署

- **Docker**：使用项目根目录 `docker compose`，详见部署文档
- **非 Docker**：构建后由 Nginx 托管静态文件并代理 `/api`

---

## 十、设计规划与实现差异

| 设计规划 | 当前实现 |
|----------|----------|
| MQTT.js 前端订阅实时数据 | 后端 MQTT + REST 轮询 / 接口 |
| ECharts 图表 | 待实现，仪表盘以表格为主 |
| Monaco Editor 脚本编辑 | textarea 简易编辑 |
| StatCard、DataChart、TimeAgo 等公共组件 | 部分合并到页面或未单独抽离 |
| 传感器 / 设备 Pinia stores | 以页面内数据请求为主 |

上述差异不影响核心业务流程，可在后续迭代中逐步补齐。

---

*文档更新日期：2026 年 2 月*
