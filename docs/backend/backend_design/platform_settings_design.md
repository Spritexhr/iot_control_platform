# 平台配置 (platform_settings) 设计文档

本文档描述物联网控制平台的平台配置模块设计，涵盖 `PlatformConfig` 模型、`get_config` 配置读取机制、`configure` 管理命令（wizard / --init / --set），以及与前端的集成方式。

> **0.7 重构说明**：自 0.7 起 `default_config.json` 与 `seed_platform_config` 已废弃，由 `platform_settings/defaults.py:DEFAULT_CONFIGS` 常量 + `configure` 管理命令替代。`.env` 不再含 MQTT 相关项，所有业务配置只走 `PlatformConfig` 表。

---

## 一、架构概览

### 1.1 设计目标

- **非敏感配置集中管理**：MQTT、设备离线超时等可调参数统一存储，支持运行时修改
- **配置来源**：仅从 platform_settings 数据库读取，防止多来源混乱
- **前端可管理**：超级用户可在系统设置中增删改平台配置，无需重启服务

### 1.2 模块关系

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        配置读取流程                                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   settings.py (MQTT_PORT 等)                                              │
│         │                                                                │
│         ▼                                                                │
│   get_config(key, default, value_type)  ← config/platform_config.py      │
│         │                                                                │
│         └──► PlatformConfig.get_value(key)  ← 仅数据库                     │
│                   │                                                       │
│                   └── 不存在/异常 → default                               │
│         │                                                                │
│         ▼                                                                │
│   返回配置值（str/int/bool/float）                                         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                        配置写入流程                                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   defaults.py: DEFAULT_CONFIGS  ──┐                                       │
│                                   ├──►  configure --init  ──►  PlatformConfig │
│                                   │     (仅补缺失的 key，已有不动)             │
│                                                                         │
│   人工/CI 输入  ──►  configure (wizard / --set / --unset)  ──►  PlatformConfig │
│                                                                         │
│   写入后默认调用 reload，让 MQTT 等服务无感重连                              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 二、PlatformConfig 模型

### 2.1 字段定义

| 字段 | 类型 | 约束 | 说明 |
|-----|------|-----|------|
| `key` | CharField(100) | unique | 配置键，如 mqtt_broker、device_offline_timeout |
| `value` | JSONField | null, blank | 配置值，支持 str、int、float、list、dict、bool、None |
| `category` | CharField(50) | default="general" | 分类，如 mqtt、devices，便于分组 |
| `description` | CharField(200) | blank | 说明 |
| `created_at` | DateTimeField | auto_now_add | 创建时间 |
| `updated_at` | DateTimeField | auto_now | 更新时间 |

### 2.2 类方法

| 方法 | 说明 |
|-----|------|
| `PlatformConfig.get_value(key, default=None)` | 获取配置值，不存在时返回 default，value 为 JSON 解析后的 Python 对象 |

### 2.3 设计要点

- **仅存储非敏感配置**：密码类敏感信息建议仍通过环境变量管理
- **value 为 JSON**：支持复杂类型，实际使用多为 str、int
- **category 分组**：便于前端按 mqtt、devices 等分类展示

---

## 三、get_config 配置读取

### 3.1 函数签名

```python
def get_config(
    key: str,        # PlatformConfig 的 key
    default: T,      # 默认值（数据库无此 key 时返回）
    value_type: type = str,  # 目标类型 str/int/bool/float
) -> T
```

### 3.2 读取规则

**仅从 platform_settings 数据库读取**，不存在或异常时返回 default，防止多来源混乱。

### 3.3 类型转换

`_coerce` 内部函数负责将值转换为 `value_type`，支持 `str`、`int`、`bool`、`float`。

### 3.4 在 settings.py 中的使用

为避免 settings 加载时数据库未就绪，使用 `SimpleLazyObject` 延迟读取：

```python
from django.utils.functional import SimpleLazyObject
from config.platform_config import get_config

def _lazy_config(key, default, value_type=str):
    return SimpleLazyObject(lambda: get_config(key, default, value_type))

MQTT_BROKER = _lazy_config("mqtt_broker", "127.0.0.1")
MQTT_PORT = _lazy_config("mqtt_port", 1883, int)
```

**注意**：MQTT 服务等使用 `str(settings.MQTT_PORT)` 或 `int(str(...))` 解析 LazyObject，因 LazyObject 在首次访问时才求值。

---

## 四、configure 管理命令

### 4.1 职责

`PlatformConfig` 表的**唯一写入入口**。支持五种模式：

| 模式 | 用途 |
|-----|------|
| `configure`（无参） | 交互式 wizard，按 DEFAULT_CONFIGS 顺序询问，回车保留当前值 |
| `--init` | 仅写入 DB 中缺失的 key，已存在不动；用于首次部署/升级补默认值 |
| `--set k=v` | 单键写入，支持重复传，CI/脚本化 |
| `--unset key` | 把 key 重置为 DEFAULT_CONFIGS 中的默认值 |
| `--list` | 列出所有当前配置（密码字段打码） |

写入后默认触发 reload，让 MQTT 等服务无感重连；`--no-reload` 跳过（启动阶段使用）。

### 4.2 配置项定义

由 `platform_settings/defaults.py` 中的 `DEFAULT_CONFIGS: List[Dict]` 维护：

```python
DEFAULT_CONFIGS = [
    {"key": "mqtt_broker", "default": "127.0.0.1", "category": "mqtt",
     "description": "MQTT/EMQX 服务器地址"},
    {"key": "mqtt_password", "default": "", "category": "mqtt",
     "description": "MQTT 密码", "secret": True},
    ...
]
```

| key | 默认值 | category | 备注 |
|-----|-------|----------|------|
| mqtt_broker | 127.0.0.1 | mqtt | 占位地址，wizard 必改 |
| mqtt_port | 1883 | mqtt | EMQX 标准端口 |
| mqtt_keepalive | 60 | mqtt | |
| mqtt_username | "" | mqtt | |
| mqtt_password | "" | mqtt | secret=True，输入不回显 |
| device_offline_timeout | 300 | devices | |
| device_reconnect_attempts | 3 | devices | |
| device_reconnect_interval | 10 | devices | |
| sensor_data_retention_days | 30 | data_retention | |
| device_data_retention_days | 30 | data_retention | |

新增配置项只需追加一条 dict 到 `DEFAULT_CONFIGS`，下次 `configure --init` 即被写入。

### 4.3 类型转换

`configure._coerce` 按 `default` 的 Python 类型自动转换字符串输入：
- `int / float`：直接转，失败抛 CommandError
- `bool`：接受 `true / 1 / yes / y / on`
- `list / dict`：解析为 JSON
- 其他：保持 str

### 4.4 Docker 部署

启动 command 在 `migrate` 之后调用 `configure --init --no-reload`：

```yaml
command: >
  sh -c "python manage.py migrate --noinput &&
    python manage.py configure --init --no-reload &&
    python manage.py collectstatic --noinput &&
    gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 1"
```

`--init` 仅在 DB 缺失 key 时写入，已配置过的不会被覆盖；`--no-reload` 因为此时 MQTT 服务还未启动。

首次部署后用户手动跑 wizard 完成配置：

```bash
docker compose exec backend python manage.py configure
```

---

## 五、API 与权限

### 5.1 PlatformConfigViewSet

| 操作 | 权限 | 说明 |
|-----|------|------|
| 列表、详情 | IsAuthenticated | 已认证用户可读 |
| 创建、更新、删除 | IsAuthenticated + IsSuperuser | 仅超级用户可写 |

### 5.2 路由

- 列表：`GET /api/platform-configs/`
- 详情：`GET /api/platform-configs/{key}/`
- 创建：`POST /api/platform-configs/`
- 更新：`PUT/PATCH /api/platform-configs/{key}/`
- 删除：`DELETE /api/platform-configs/{key}/`

`lookup_field` 为 `key`，即按配置键作为资源标识。

---

## 六、与 MQTT 服务的集成

MQTT 服务在 `sensors.apps.SensorsConfig.ready()` 中启动，连接时读取 `settings.MQTT_BROKER`、`settings.MQTT_PORT` 等。这些值通过 `_lazy_config` 从 `get_config` 获取，因此：

- 首次启动：若未执行 `configure --init`，`get_config()` 会回退到 default
- 修改 platform_settings 后：调用 `POST /api/platform-configs/reload/` 或 `configure` 写完触发的 reload，让 MQTT 重连应用新值，**无需重启进程**

`mqtt_service` 直接调用 `get_config`（见 `services/mqtt_service.py`），所以热更新有效。

---

## 七、文件结构

```
config/
├── platform_config.py          # get_config 函数
├── permissions.py              # IsSuperuser（platform_settings 写权限依赖）
└── settings.py                 # _lazy_config、MQTT_* 等

platform_settings/
├── models.py                   # PlatformConfig / Plugin
├── defaults.py                 # DEFAULT_CONFIGS 常量（替代 default_config.json）
├── views.py                    # PlatformConfigViewSet（含 reload / cleanup-old-data API）
├── serializers.py              # PlatformConfigSerializer
└── management/commands/
    ├── configure.py            # 写入唯一入口（wizard / --init / --set / --unset / --list）
    ├── cleanup_old_data.py     # 数据清理命令
    └── sync_plugins.py         # 插件同步命令
```

---

## 八、设计要点总结

1. **数据库唯一真源**：业务配置只在 `PlatformConfig` 表，不再有 `.env`/JSON/DB 三重来源
2. **`.env` 极简化**：仅保留进程级启动必备项（`SECRET_KEY` / `DB_*` / `DEBUG` / 端口）
3. **延迟加载**：settings 使用 SimpleLazyObject，避免启动时 DB 未就绪
4. **写入入口收敛**：所有写入走 `configure` 命令或 API，统一类型转换、reload、密码打码
5. **`--init` 幂等**：仅补 DB 缺失的 key，已有不动；用户改过的值永远不被覆盖
6. **权限隔离**：API 仅超级用户可增删改；命令行依赖 Docker exec 隔离

---

## 九、settings.py 安全配置

### 9.1 SECRET_KEY 管理策略

| 环境 | 行为 |
|-----|------|
| `SECRET_KEY` 环境变量已设置 | 使用环境变量值 |
| `DEBUG=True` 且未设置 `SECRET_KEY` | 使用开发默认值 `django-insecure-dev-only-key-do-not-use-in-production` |
| `DEBUG=False` 且未设置 `SECRET_KEY` | 抛出 `ImproperlyConfigured`，阻止启动 |

**原因**：防止生产环境使用不安全的默认 SECRET_KEY。

### 9.2 生产环境安全头

当 `DEBUG=False` 时自动启用：

| 配置 | 默认值 | 说明 |
|-----|--------|------|
| `SECURE_BROWSER_XSS_FILTER` | True | 浏览器 XSS 过滤 |
| `SECURE_CONTENT_TYPE_NOSNIFF` | True | 阻止 MIME 类型嗅探 |
| `X_FRAME_OPTIONS` | DENY | 防止点击劫持 |
| `SESSION_COOKIE_SECURE` | 环境变量 | 仅 HTTPS 下传输 Session Cookie |
| `CSRF_COOKIE_SECURE` | 环境变量 | 仅 HTTPS 下传输 CSRF Cookie |

### 9.3 CORS 扩展

除 `CORS_ALLOWED_ORIGINS` 硬编码列表外，支持通过环境变量 `EXTRA_CORS_ORIGINS` 追加额外源（逗号分隔）：

```bash
EXTRA_CORS_ORIGINS=https://iot.example.com,https://admin.example.com
```

### 9.4 API 节流

| 节流类别 | 速率 | 说明 |
|---------|------|------|
| `anon` | 30/hour | 匿名请求（未认证） |
| `user` | 100/hour | 已认证用户 |

---

## 十、cleanup_old_data 分批删除

### 10.1 设计目标

数据清理命令 `cleanup_old_data` 采用分批删除策略，避免一次性删除大量记录导致大表锁表或内存溢出。

### 10.2 命令参数

| 参数 | 默认值 | 说明 |
|-----|--------|------|
| `--dry-run` | false | 仅统计数量，不实际删除 |
| `--batch-size` | 1000 | 每批删除的记录数 |

### 10.3 执行流程

```
1. 读取 sensor_data_retention_days 和 device_data_retention_days
2. 计算截止时间
3. 统计将删除的记录数
4. 分批删除（每批取 batch_size 个 ID → 批量删除 → 循环直到清空）
5. 输出统计结果
```

### 10.4 使用示例

```bash
# 默认分批大小（1000 条/批）
python manage.py cleanup_old_data

# 自定义分批大小
python manage.py cleanup_old_data --batch-size 500

# 试运行
python manage.py cleanup_old_data --dry-run
```
