# IoT 控制平台 — Claude 协作说明

## 环境

| 项 | 值 |
|---|---|
| Python | `/Users/xhr_mac/miniconda3/envs/iot_platform_env/bin/python` (conda env `iot_platform_env`) |
| Django | 6.0.3，DRF |
| 数据库 | SQLite（`iot_control_platform/db.sqlite3`） |
| 后端工作目录 | `/Users/xhr_mac/server/iot_control_platform/iot_control_platform/` |
| 前端工作目录 | `/Users/xhr_mac/server/iot_control_platform/frontend/` |
| 前端栈 | Vue 3 + Vite + Pinia + Vue Router + Element Plus + Vue Flow |
| Django settings | `config/settings.py` |
| Django urls | `config/urls.py` |
| 主干分支 | `main`；开发分支 `beta_version` |

> ⚠️ 系统 `python` 不带 Django。所有后端命令必须用绝对路径 `/Users/xhr_mac/miniconda3/envs/iot_platform_env/bin/python` 或先 `conda activate iot_platform_env`。

## 常用命令

```bash
# 后端（在 iot_control_platform/iot_control_platform/ 目录）
/Users/xhr_mac/miniconda3/envs/iot_platform_env/bin/python manage.py check
/Users/xhr_mac/miniconda3/envs/iot_platform_env/bin/python manage.py makemigrations
/Users/xhr_mac/miniconda3/envs/iot_platform_env/bin/python manage.py migrate
/Users/xhr_mac/miniconda3/envs/iot_platform_env/bin/python manage.py runserver

# 前端（在 frontend/ 目录）
npm run dev
npm run build
```

## 后端架构

### 主 Django apps
- `sensors`、`devices`、`automation`、`platform_settings`
- 主模型：`sensors.Sensor` / `sensors.SensorData` / `sensors.SensorStatusCollection`、`devices.Device` / `devices.DeviceStatusCollection`、对应的 `SensorType` / `DeviceType`

### 插件机制（重要）
- 插件目录：`iot_control_platform/plugins/<name>/`，必须含 `plugin.json`（`enabled: true` 才生效）
- `plugins/__init__.py` 的 `discover_plugins()` 自动发现并加入 `INSTALLED_APPS`
- `config/urls.py` 自动挂载到 `/api/plugins/<name>/`
- 插件 app 命名约定：`apps.py` 中 `name="plugins.<name>"`，`label="plugin_<name>"`

现有插件：`eb_plant`（乙苯装置大屏）、`plant_diagram`（P&ID 画板编辑器）、`data_viz`（时序可视化）

### 解耦规则（2026-05-15 已实施，重要约束）
**主模型 `Sensor` / `Device` 必须保持插件清洁**——任何插件不得：
1. 给主模型加字段（曾有 `plant_code` / `plant_metadata`，已彻底移除）
2. 写 management 命令往主模型 seed 数据
3. 在 `services/` 通用层引用具体插件名

正确模式（以 `eb_plant` 为参考）：
- 插件在 `plugins/<name>/models.py` 定义自己的表
- 通过 `OneToOneField("sensors.Sensor", on_delete=CASCADE)` 引用主模型；主模型对插件零感知
- 通过 Django signals（如 `post_save` of `SensorData`）在 `plugins/<name>/signals.py` 注入实时数据流；`apps.py` 的 `ready()` 中 `from . import signals`
- 插件提供"从主模型导入到自有表"的 API（参考 `plugins/eb_plant/views.py` 的 `bindable_sources` + `sensor_bindings` CRUD）

### 实时数据链路
```
MQTT 消息
  → services/sensors_service/sensor_upload_data_handlers.py（落库 SensorData，纯主模型职责）
  → SensorData.save 触发 post_save 信号
  → plugins/<name>/signals.py（按插件 binding 表过滤）
  → services/realtime/latest_values.py 的 ingest_sensor_data(plugin_code, binding=...)
  → LatestValuesCache + Broadcaster.publish (内存)
  → /api/plugins/<name>/stream（SSE）
  → 前端 composables/useSSE.js
```

`PointSample` 字段名 `plugin_code`（非 `plant_code`），insgest 入参用 `binding` 鸭子类型对象（需有 `tag/unit/data_key/hi_threshold/lo_threshold/severity` 属性）。

## 前端架构

- 入口路由：`frontend/src/router/index.js`，`requiresAuth` meta 配合 `localStorage['iot-access-token']` 做守卫；`guest: true` 的页面为登录/注册
- axios 实例：`frontend/src/api/index.js`，baseURL 含 `/api` 前缀；调用时路径以 `/` 开头不含 `/api`
- Pinia stores：`frontend/src/stores/`，命名风格 `useXxxStore`
- 插件页面：`frontend/src/views/plugins/<name>/`
- 插件 API：`frontend/src/api/plugins/<name>.js`
- SSE：`frontend/src/composables/useSSE.js`，对外暴露 `status` ref（`idle/connecting/open/closed/error`）

## 权限模型
- DRF token 认证 + session 兼容
- 写接口默认 `IsAuthenticated + IsAdminUser`（即 `is_staff=True`）
- 读接口默认 `IsAuthenticated`
- SSE 端点用 `AllowAny`（因 `EventSource` 无法附 Authorization header），生产化时换 token 查询参数

## 协作惯例
- 用户偏好中文交流、中文代码注释
- 用户偏好简洁清晰的架构；明确反感"主模型被插件污染"
- 修改架构性问题时，倾向于**一次性彻底解耦**而不是渐进兼容（参考本次 EB 解耦的"一并改造 plant_diagram + 删模拟器 + 清数据"策略）
- 前端 UI 风格："Claude 官网风格（暖米色 + 珊瑚橙）"，EB 大屏单独走"工程蓝白图纸风格"
- 演示/模拟数据不要进生产代码——所有测试数据由用户手动创建

## 已知文档
- `docs/EB装置大屏使用手册.md` — 含 2026-05-15 重构提示，旧流程段落保留作历史参考
- `docs/development_plans/` — 大功能方案文档目录
