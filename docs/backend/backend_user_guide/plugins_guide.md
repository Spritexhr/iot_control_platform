# 插件开发指南

本文档面向想为平台添加新功能的开发者，给出从 0 到 1 编写一个插件的完整流程：目录骨架、清单字段、URL 挂载、模型迁移、与前端联调，以及常见坑位。架构原理见 [plugins_design.md](../backend_design/plugins_design.md)。

---

## 一、什么时候用插件

| 场景                                       | 推荐方式                |
|--------------------------------------------|-------------------------|
| 实验性功能 / 单点工具（数据可视化、报表等）| **插件**                |
| 与现有 sensor / device / automation 紧耦合 | 直接修改对应 app        |
| 跨多个核心模块的横切能力（中间件、信号）   | 直接放在 `config/`      |
| 需要独立部署、独立进程的功能（推理服务）   | 拆为独立服务，不走插件   |

判断标准：**只读核心模型，写自己的模型，对外只暴露 `/api/plugins/<name>/`** 的功能，最适合做成插件。

---

## 二、5 分钟添加一个 hello 插件

### 2.1 创建目录

```bash
cd iot_control_platform/plugins
mkdir hello
cd hello
touch __init__.py plugin.json apps.py urls.py views.py
```

### 2.2 plugin.json

```json
{
  "name": "hello",
  "version": "0.1.0",
  "description": "示例插件 - 返回一句问候",
  "enabled": true
}
```

| 字段          | 说明                                                                |
|---------------|---------------------------------------------------------------------|
| `name`        | 必须与目录名一致，否则 sync 时记录的是 `name` 字段而 URL 用的是目录名 |
| `version`     | 语义化版本，sync 时刷新到 DB                                         |
| `description` | 一句话说明，会在前端插件中心展示                                      |
| `enabled`     | 默认启用状态，**仅首次** sync 时写入 DB，后续改 JSON 不会覆盖用户决策 |

### 2.3 apps.py

```python
from django.apps import AppConfig


class HelloConfig(AppConfig):
    name = "plugins.hello"          # 必须为 plugins.<目录名>
    label = "plugin_hello"          # app_label，避免与核心 app 冲突，建议加 plugin_ 前缀
    verbose_name = "Hello（插件）"
```

### 2.4 views.py

```python
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def hello(request):
    return Response({"message": f"hello, {request.user.username}"})
```

### 2.5 urls.py

```python
from django.urls import path
from . import views

urlpatterns = [
    path("hello/", views.hello, name="hello"),
]
```

### 2.6 同步并重启

```bash
# 把 plugin.json 同步到 Plugin 表
python manage.py sync_plugins

# 重启 Django（URL conf 仅在启动时绑定）
# Docker:   docker compose restart backend
# 本地:     重启 runserver / gunicorn
```

启动日志应出现：

```
[plugins] 已挂载: /api/plugins/hello/
```

### 2.7 验证

```bash
TOKEN=...  # 已登录用户的 access token
curl -H "Authorization: Bearer $TOKEN" http://localhost:8081/api/plugins/hello/hello/
# {"message": "hello, admin"}
```

---

## 三、插件目录骨架（完整版）

```
plugins/<name>/
├── __init__.py              # 必需，可为空
├── plugin.json              # 必需
├── apps.py                  # 必需
├── urls.py                  # 可选；缺省时插件无 HTTP 端点
├── views.py                 # 可选
├── models.py                # 可选；要写自己的表才需要
├── serializers.py           # 可选
├── admin.py                 # 可选；想在 Django Admin 看自己的表才需要
└── migrations/              # 可选；models 存在时由 makemigrations 生成
    └── 0001_initial.py
```

最小可运行集合：`__init__.py` + `plugin.json` + `apps.py`。没有 `urls.py` 也合法，只是不会暴露 HTTP API，可以纯做后台任务（信号、定时任务等）。

---

## 四、给插件加自己的数据库表

插件可以定义自己的 Django models。注意 `app_label` 必须与 `apps.py:label` 一致。

### 4.1 models.py

```python
from django.db import models


class HelloLog(models.Model):
    user = models.CharField(max_length=100)
    message = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "plugin_hello"        # 必须与 apps.py:label 一致
        verbose_name = "Hello 日志"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user}: {self.message}"
```

### 4.2 生成并应用迁移

```bash
python manage.py makemigrations plugin_hello
python manage.py migrate
```

生成的迁移文件会落在 `plugins/hello/migrations/0001_initial.py`，与核心 app 的迁移目录隔离。

### 4.3 admin.py（可选）

```python
from django.contrib import admin
from .models import HelloLog


@admin.register(HelloLog)
class HelloLogAdmin(admin.ModelAdmin):
    list_display = ["user", "message", "created_at"]
    search_fields = ["user", "message"]
```

---

## 五、读核心模型

插件 views 可以**只读**地查询核心模型（sensors、devices、automation 等）：

```python
from sensors.models import Sensor, SensorData
from devices.models import Device


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def stats(request):
    return Response({
        "sensors": Sensor.objects.count(),
        "devices": Device.objects.count(),
    })
```

**避免**：
- 直接改核心模型字段或写入核心表（破坏数据所有权边界）
- 把核心模型注册到自己的 admin（会与 sensors/devices 的 admin 冲突）
- import core 模块的内部工具函数（除非它们已被设计为公共 API）

如果确实需要写核心数据，走对应模块的 service / API，而不是直接 ORM 写。

---

## 六、API 与权限

### 6.1 路由前缀

插件路由会自动挂载到 `/api/plugins/<name>/`，由 `_mount_enabled_plugins` 完成。**不要**在 `urls.py` 里再加 `api/plugins/<name>/` 前缀，它是相对路径：

```python
# urls.py
urlpatterns = [
    path("ping/", views.ping),                     # → /api/plugins/<name>/ping/
    path("items/<int:pk>/", views.item_detail),    # → /api/plugins/<name>/items/<pk>/
]
```

### 6.2 推荐的认证与权限

绝大多数业务接口跟随核心约定即可：

```python
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_view(request):
    ...
```

如需仅超级用户：

```python
from config.permissions import IsSuperuser

@permission_classes([IsAuthenticated, IsSuperuser])
```

### 6.3 节流

DRF 全局 throttle（5000/h 用户、100/h 匿名）已生效，插件无需额外配置。如果你的插件有重负载端点（导出大文件、训练等），自行加 `throttle_classes` 限流。

---

## 七、与前端联调

### 7.1 添加 API 客户端

在 `frontend/src/api/plugins.js` 末尾追加：

```javascript
// ==================== hello 插件 ====================
export function getHello() {
  return request.get('/plugins/hello/hello/')
}
```

### 7.2 添加视图组件

新建 `frontend/src/views/plugins/HelloView.vue`，参考 `DataVizView.vue` 的页面骨架（标题区 + 内容区 + 错误处理）。

### 7.3 注册路由

在 `frontend/src/router/index.js` 的 `children` 中追加：

```javascript
{
  path: 'plugins/hello',
  name: 'PluginHello',
  component: () => import('@/views/plugins/HelloView.vue'),
  meta: { title: 'Hello 插件' },
},
```

> 当前版本的前端**不会自动**为新插件生成菜单项，需要手动改 `router` 和 `PluginsListView.vue` 的链接。后续若启用清单驱动的菜单（见设计文档 §9.2），这一步会消失。

---

## 八、运维操作

### 8.1 同步插件清单

```bash
# 把 plugins/ 目录的 plugin.json 同步到 Plugin 表
python manage.py sync_plugins

# 同时移除 DB 中文件系统已不存在的插件登记
python manage.py sync_plugins --prune
```

也可走 API：

```bash
curl -X POST -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8081/api/plugin-manager/sync/
```

### 8.2 启用 / 禁用插件

```bash
# 查看
curl -H "Authorization: Bearer $TOKEN" http://localhost:8081/api/plugin-manager/

# 禁用
curl -X POST -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8081/api/plugin-manager/hello/disable/

# 启用
curl -X POST -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8081/api/plugin-manager/hello/enable/

# ⚠️ 启用 / 禁用都需要重启 Django 进程才会真正影响 URL 路由
```

### 8.3 Django Admin

`platform_settings.Plugin` 注册了 admin，`/admin/platform_settings/plugin/` 可以列表 + 直接编辑 `enabled`。改完同样需要重启。

---

## 九、常见坑位

| 现象                                              | 原因 / 处置                                                              |
|---------------------------------------------------|--------------------------------------------------------------------------|
| `sync_plugins` 报告 0 个插件                      | `plugin.json` 缺失 / 解析失败 / 目录名以 `_` 或 `.` 开头                  |
| `sync` 后 `/api/plugins/<name>/...` 仍是 404      | 没重启进程；或 `Plugin.enabled=False`；或 `urls.py` 报 import 错误（看日志） |
| `enable` 接口返回成功但路由依旧 404               | URL conf 在启动时绑定，必须重启 Django 进程才生效                          |
| `makemigrations` 找不到 models                    | `apps.py:name` 必须为 `plugins.<目录名>`；`Meta.app_label` 必须等于 `apps.py:label` |
| 启动日志：`插件 X 的 plugin.json 解析失败`        | JSON 语法错（多余逗号、单引号等）                                          |
| 日志没有 `[plugins] 已挂载: ...`                  | 插件被发现但被禁用，或 `urls.py` import 时抛异常被 catch 了，看 `logger.exception` |
| `app_label` 冲突 (`Conflicting model in...`)      | 别用裸名 `hello`，建议 `plugin_<name>` 前缀避免与核心 app 撞名             |

---

## 十、检查清单

发布插件前过一遍：

- [ ] 目录名 = `plugin.json` 的 `name` = `apps.py:name` 的后缀
- [ ] `apps.py:label` 加了 `plugin_` 前缀，与 `Meta.app_label` 一致
- [ ] `urls.py` 路径都是相对路径，没有 `api/plugins/<name>/` 前缀
- [ ] 视图加了 `@permission_classes([IsAuthenticated])`
- [ ] 仅读核心模型，没有直接写核心表
- [ ] 如果有 models，运行了 `makemigrations <label>` 并提交了迁移文件
- [ ] 在 `plugin.json` 写了清晰的 description，前端会展示
- [ ] 前端 `api/plugins.js` 加了客户端、`router/index.js` 加了路由
- [ ] 至少手动跑通了一个 happy path 请求

---

## 十一、参考实现

`plugins/data_viz/` 是一个相对完整的内置例子，覆盖：

- `plugin.json` 字段全集
- 多个 GET 端点（`ping` / `sources` / `series`）
- 跨表联查（`Sensor + SensorData + SensorStatusCollection`）
- 时间窗截断 + limit 上限保护
- 仅读核心模型，无自有 models

新插件可以从复制 `data_viz/` 改起，比从空目录搭建更快。
