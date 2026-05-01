# 插件系统 (plugins) 设计文档

本文档描述物联网控制平台的插件机制：在不侵入核心代码的前提下挂载实验性功能（数据可视化、ML 推理、报表等）。涵盖目录约定、发现/启用/路由的生命周期、`Plugin` 登记模型、与前端的集成，以及第一个内置插件 `data_viz` 的实现示意。

---

## 一、架构概览

### 1.1 设计目标

- **零侵入**：新功能放在 `plugins/<name>/` 子目录，不修改核心 app
- **文件系统驱动**：以 `plugin.json` 清单为唯一真源，`sync_plugins` 把清单同步到数据库
- **数据库可控**：`Plugin.enabled` 决定 `/api/plugins/<name>/` 是否注册，前端可在线切换
- **失败隔离**：单个插件 import/include 失败只跳过该插件，不影响主路由
- **迁移可用**：所有发现到的插件都加入 `INSTALLED_APPS`，保证 `makemigrations` 正常工作；URL 层按 `enabled` 过滤

### 1.2 模块关系

```
┌──────────────────────────────────────────────────────────────────────┐
│                        插件加载流程（启动时）                            │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│   plugins/ 目录                                                        │
│      │  扫描子目录 + plugin.json                                        │
│      ▼                                                                 │
│   discover_plugins()  ──►  list[PluginMeta]                            │
│      │                                                                 │
│      ├──► settings.INSTALLED_APPS  （所有发现到的）                       │
│      │      └─ 保证 makemigrations / migrate 可用                        │
│      │                                                                 │
│      └──► config/urls.py:_mount_enabled_plugins()                      │
│              │                                                         │
│              ├─ enabled_plugin_names()  ←  Plugin 表 (DB 优先)          │
│              │                              ↓ DB 不可用                 │
│              │                          plugin.json 默认值              │
│              │                                                         │
│              └─ 仅启用的插件注册：                                        │
│                 path("api/plugins/<name>/", include(<name>.urls))      │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│                        插件登记流程（运维时）                            │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│   plugins/<name>/plugin.json                                           │
│           │                                                            │
│           ▼                                                            │
│   python manage.py sync_plugins                                        │
│      或  POST /api/plugin-manager/sync/  （管理员）                       │
│           │                                                            │
│           ▼                                                            │
│   platform_settings.Plugin                                             │
│      • 新增：按清单 enabled 默认值登记                                    │
│      • 已存在：仅刷新 version/description，保留 enabled 用户决策          │
│      • --prune：移除文件系统已删除的插件登记                              │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 二、插件目录约定

### 2.1 物理布局

```
iot_control_platform/
└── plugins/
    ├── __init__.py                  # 提供 discover_plugins / enabled_plugin_names
    ├── README.md                    # 简短的目录说明
    └── <plugin_name>/               # 一个插件 = 一个独立 Django app
        ├── plugin.json              # 必需：插件清单
        ├── apps.py                  # 必需：AppConfig
        ├── __init__.py              # 必需
        ├── urls.py                  # 可选：API 路由
        ├── views.py                 # 可选
        ├── models.py                # 可选：插件可定义自己的模型
        ├── serializers.py           # 可选
        ├── admin.py                 # 可选
        └── migrations/              # 可选：插件自身的迁移
```

### 2.2 plugin.json 字段

| 字段          | 类型    | 必填 | 说明                                          |
|---------------|---------|------|-----------------------------------------------|
| `name`        | string  | 是   | 插件唯一标识，建议与目录名一致                |
| `version`     | string  | 是   | 语义化版本，如 `"0.2.0"`                       |
| `description` | string  | 是   | 简短描述，会写入 `Plugin.description`         |
| `enabled`     | boolean | 是   | 默认启用状态，**首次** `sync_plugins` 时写入 DB |

`enabled` 字段仅在首次登记时被读入 DB，之后再改 JSON 不会覆盖用户在 DB 里的决策（详见 §四 sync 流程）。

### 2.3 PluginMeta 数据类

`plugins/__init__.py` 定义的轻量数据类，作为发现阶段的内存表示：

| 字段         | 类型    | 说明                                  |
|--------------|---------|---------------------------------------|
| `name`       | str     | 插件标识                              |
| `version`    | str     | 版本                                  |
| `description`| str     | 描述                                  |
| `enabled`    | bool    | 清单默认启用状态                      |
| `path`       | Path    | 插件目录绝对路径                      |
| `app_label`  | property| Django app 路径，固定为 `plugins.<name>` |
| `url_module` | property| URL 模块路径 `plugins.<name>.urls`    |

---

## 三、发现与启用

### 3.1 discover_plugins()

定义在 `plugins/__init__.py`，仅做文件系统扫描，**不依赖数据库**：

```python
def discover_plugins() -> list[PluginMeta]:
    # 扫描 plugins/ 子目录
    # 合法条件：目录名不以 _ 或 . 开头，且包含 plugin.json
    # JSON 解析失败的子目录会被跳过并 warning，不抛异常
```

**调用点**：
- `config/settings.py`：把所有发现到的插件加入 `INSTALLED_APPS`
- `config/urls.py:_mount_enabled_plugins()`：枚举候选挂载列表
- `sync_plugins` 命令：枚举待登记列表

### 3.2 enabled_plugin_names()

返回当前**已启用**插件的名字集合，以数据库为准、清单为兜底：

```python
def enabled_plugin_names() -> set[str]:
    # 优先读 platform_settings.Plugin 表
    # 表不存在 / DB 未就绪 / 应用未加载 → 回退到清单 enabled 默认值
    # DB 中无该插件记录 → 用清单默认（首次启动到 sync 之间的窗口）
```

**回退机制的意义**：迁移尚未应用、数据库不可达等启动初期场景下，插件系统仍能基于清单工作，避免 `makemigrations` / 容器首启时的鸡生蛋问题。

### 3.3 INSTALLED_APPS 注入

`config/settings.py` 在标准 `INSTALLED_APPS` 之后追加：

```python
try:
    from plugins import discover_plugins as _discover_plugins
    INSTALLED_APPS.extend(p.app_label for p in _discover_plugins())
except Exception as _e:
    print(f"[plugins] 发现失败，已跳过: {_e}", file=sys.stderr)
```

**所有插件**（包括 `enabled=False` 的）都会被注入。原因：
- 保证 `makemigrations` 能识别插件的 `models`
- `enabled=False` 仅影响 URL 是否暴露，不影响 ORM
- `try/except` 包裹，发现阶段失败不阻断 Django 启动

### 3.4 URL 挂载

`config/urls.py` 在 `urlpatterns` 定义之后调用：

```python
def _mount_enabled_plugins():
    enabled = enabled_plugin_names()
    for meta in discover_plugins():
        if meta.name not in enabled:
            continue
        try:
            urlpatterns.append(
                path(f"api/plugins/{meta.name}/", include(meta.url_module))
            )
            logger.info(f"[plugins] 已挂载: /api/plugins/{meta.name}/")
        except Exception as e:
            logger.exception(f"[plugins] 挂载 {meta.name} 失败，已跳过: {e}")
```

**关键约束**：
- 路由前缀固定：`/api/plugins/<name>/`，插件无法自选根路径
- 单个插件挂载失败被 `try/except` 隔离，记录日志后继续处理下一个
- URL 配置在 Django 启动时绑定一次，**toggle `enabled` 必须重启进程**才生效

---

## 四、Plugin 登记模型

### 4.1 字段定义

定义于 `platform_settings.models.Plugin`：

| 字段           | 类型           | 约束               | 说明                                       |
|----------------|----------------|--------------------|--------------------------------------------|
| `name`         | CharField(100) | unique             | 与 `plugins/` 下的目录名一致                |
| `enabled`      | BooleanField   | default=True       | 是否启用，启用变更需重启 Django 进程        |
| `version`      | CharField(50)  | blank, default=""  | 版本号，由 sync 从清单同步                  |
| `description`  | CharField(200) | blank              | 描述，由 sync 从清单同步                    |
| `installed_at` | DateTimeField  | auto_now_add       | 登记时间                                    |
| `updated_at`   | DateTimeField  | auto_now           | 更新时间                                    |

### 4.2 `sync_plugins` 管理命令

文件：`platform_settings/management/commands/sync_plugins.py`

| 行为           | 说明                                                              |
|----------------|-------------------------------------------------------------------|
| 新增插件登记   | 按清单 `enabled` 默认值写入 DB                                     |
| 已存在的插件   | **仅刷新** `version` 和 `description`，**保留** 用户的 `enabled` 决策 |
| `--prune`      | 移除文件系统中已不存在的插件登记记录                                |

输出形如：

```
发现 1 个插件: ['data_viz']
  + 登记: data_viz v0.2.0
完成: 新增 1，刷新 0，移除 0
```

---

## 五、API 与权限

### 5.1 PluginViewSet

定义于 `platform_settings/views.py`，注册路径 `/api/plugin-manager/`：

| 操作                         | HTTP                                       | 权限                       | 说明                                  |
|------------------------------|--------------------------------------------|----------------------------|---------------------------------------|
| 列表                         | `GET /api/plugin-manager/`                 | IsAuthenticated            | 已登记插件                            |
| 详情                         | `GET /api/plugin-manager/<name>/`          | IsAuthenticated            |                                       |
| 同步                         | `POST /api/plugin-manager/sync/`           | IsAuthenticated + IsSuperuser | 触发 `sync_plugins` 命令              |
| 启用                         | `POST /api/plugin-manager/<name>/enable/`  | IsAuthenticated + IsSuperuser | 仅设置 `enabled=True`，需重启生效     |
| 禁用                         | `POST /api/plugin-manager/<name>/disable/` | IsAuthenticated + IsSuperuser | 仅设置 `enabled=False`，需重启生效    |

`lookup_field = "name"`，按插件名作为资源标识。`PluginViewSet` 是 `ReadOnlyModelViewSet`，不暴露 PUT/POST/DELETE 写接口；启用切换通过专用 action 完成，避免直接编辑模型。

### 5.2 序列化器

`PluginSerializer` 中除 `enabled` 外全部为 `read_only_fields`：版本、描述只能由 sync 写入，前端不能在常规 PATCH 里改。

### 5.3 插件自身的 API

每个启用的插件，URL 前缀固定为 `/api/plugins/<name>/`，由 `_mount_enabled_plugins` 自动 include 插件的 `urls.py`。例如 `data_viz` 暴露：

| 端点                                    | 方法 | 权限              | 说明                  |
|-----------------------------------------|------|-------------------|-----------------------|
| `/api/plugins/data_viz/ping/`           | GET  | IsAuthenticated   | 端到端探针            |
| `/api/plugins/data_viz/sources/`        | GET  | IsAuthenticated   | 列出可视化数据源      |
| `/api/plugins/data_viz/series/?...`     | GET  | IsAuthenticated   | 取时间窗时序数据      |

---

## 六、与前端的集成

### 6.1 路由

`frontend/src/router/index.js` 静态注册插件视图（不自动从后端拉取菜单）：

```javascript
{ path: 'plugins',          name: 'Plugins',         component: PluginsListView },
{ path: 'plugins/data_viz', name: 'PluginDataViz',   component: DataVizView },
```

### 6.2 API 客户端

`frontend/src/api/plugins.js` 提供两组 API：

- 插件管理：`getPlugins`、`syncPlugins`、`enablePlugin(name)`、`disablePlugin(name)`
- `data_viz` 业务：`getDataVizSources()`、`getDataVizSeries({kind, sourceId, start, end, limit})`

### 6.3 视图

| 视图               | 路径                            | 说明                                          |
|--------------------|---------------------------------|-----------------------------------------------|
| `PluginsListView`  | `/plugins`                      | 列出已登记插件，提供启用切换、同步按钮         |
| `DataVizView`      | `/plugins/data_viz`             | `data_viz` 插件的可视化页面                    |

---

## 七、内置插件：data_viz

### 7.1 职责

按时间窗读取 sensor / device 的时序数据，附加 sensor 的状态事件，供前端渲染图表。

### 7.2 数据源与查询

- 数据源列表：枚举 `Sensor + Device`，附 `data_fields / state_fields`（来自 type 定义）作为前端可绘字段
- 时序查询：按 `kind=sensor|device`、`source_id`、`start/end`（缺省最近 24h）筛选
- 截断策略：超过 `limit`（默认 2000，上限 10000）时仅保留时间窗末尾的 `limit` 条，并标 `truncated=true`
  - 图表通常关心"最近"，前段截断比均匀采样更直观
- 状态事件（仅 sensor）：从 `SensorStatusCollection` 读取，独立 limit，不与数据点共用

### 7.3 设计取舍

- 不做客户端聚合（avg / max / 桶分组）：交给前端图表库的下采样能力
- 不做缓存：DB 查询走索引（timestamp），节流由 DRF 全局 throttle 兜底
- 仅返回 JSON 原文：`r.data` 直接透传，由前端解析字段

---

## 八、设计要点总结

1. **零配置发现**：扔进 `plugins/<name>/` 加 `plugin.json` 即可被识别
2. **DB 优先 + 清单兜底**：`enabled_plugin_names()` 在 DB 不可用时优雅降级
3. **失败隔离**：发现 / `INSTALLED_APPS` 注入 / URL 挂载三处都用 try/except 包裹
4. **重启生效**：`enabled` 切换不热加载，URL conf 仅在启动时绑定
5. **sync 幂等**：保留用户在 DB 中的 `enabled` 决策，仅刷新 version/description
6. **路径硬性约束**：所有插件 API 走 `/api/plugins/<name>/`，避免插件污染主路由
7. **app_label 统一**：`plugins.<name>`，与目录路径一一对应

---

## 九、已知限制与未来扩展

### 9.1 当前限制

- 不支持热插拔：`enabled` 切换后必须重启 Django 进程
- 路由前缀固定：插件无法自选 `/api/<custom>/` 路径
- 没有依赖管理：插件之间不能声明 `depends_on`，加载顺序仅按目录字典序
- 前端菜单是静态注册：新增插件需要在 `router/index.js` 里手动加路由

### 9.2 可能的扩展方向

- 插件清单中声明前端入口（`entry: "DataVizView.vue"`），由前端 `PluginsListView` 动态生成菜单
- 插件清单中声明 `depends_on: ["data_viz"]`，按拓扑序加载
- 进程级热加载（`importlib.reload` + URL conf 重建），代价是与 Django 的 app registry 兼容性

---

## 十、文件结构

```
plugins/                                # 插件根目录
├── __init__.py                         # discover_plugins / enabled_plugin_names
├── README.md                           # 简短说明（与本文档互补）
└── data_viz/                           # 内置插件
    ├── plugin.json
    ├── apps.py
    ├── urls.py
    └── views.py

platform_settings/
├── models.py                           # Plugin 模型
├── views.py                            # PluginViewSet
├── serializers.py                      # PluginSerializer
├── admin.py                            # PluginAdmin
└── management/commands/
    └── sync_plugins.py                 # 文件系统 → DB 同步

config/
├── settings.py                         # INSTALLED_APPS 注入
└── urls.py                             # _mount_enabled_plugins()

frontend/src/
├── api/plugins.js                      # 插件管理 + data_viz API 客户端
├── router/index.js                     # 静态注册插件视图路由
└── views/plugins/
    ├── PluginsListView.vue             # 插件中心
    └── DataVizView.vue                 # data_viz 视图
```
