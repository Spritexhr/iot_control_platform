# 平台配置 (platform_settings) 设计文档

本文档描述物联网控制平台的平台配置模块设计，涵盖 `PlatformConfig` 模型、`get_config` 配置读取机制、`seed_platform_config` 初始化命令，以及与前端的集成方式。

---

## 一、架构概览

### 1.1 设计目标

- **非敏感配置集中管理**：MQTT、设备离线超时等可调参数统一存储，支持运行时修改
- **配置来源优先级**：数据库（platform_settings）> 环境变量 > 默认值
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
│   get_config(key, env_key, default, value_type)  ← config/platform_config.py
│         │                                                                │
│         ├──► PlatformConfig.get_value(key)  ← 优先：数据库                 │
│         │         │                                                       │
│         │         └── 不存在/异常 → os.environ.get(env_key)  ← 回退：环境变量
│         │                              │                                  │
│         │                              └── 无 → default                   │
│         │                                                                │
│         ▼                                                                │
│   返回配置值（str/int/bool/float）                                         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                        配置写入流程                                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   .env 文件  ──►  seed_platform_config  ──►  PlatformConfig (仅创建不存在的 key)
│                                                                         │
│   Docker 部署：env_file 注入环境变量 → seed_platform_config 从 os.environ 读取
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
    env_key: str,    # 环境变量名，回退时使用
    default: T,      # 默认值
    value_type: type = str,  # 目标类型 str/int/bool/float
) -> T
```

### 3.2 读取优先级

1. **PlatformConfig.get_value(key)**：数据库中存在则返回
2. **os.environ.get(env_key)**：数据库无或异常时，使用环境变量
3. **default**：以上均无则返回默认值

### 3.3 类型转换

`_coerce` 内部函数负责将值转换为 `value_type`，支持 `str`、`int`、`bool`、`float`。

### 3.4 在 settings.py 中的使用

为避免 settings 加载时数据库未就绪，使用 `SimpleLazyObject` 延迟读取：

```python
from django.utils.functional import SimpleLazyObject
from config.platform_config import get_config

def _lazy_config(key, env_key, default, value_type=str):
    return SimpleLazyObject(lambda: get_config(key, env_key, default, value_type))

MQTT_BROKER = _lazy_config("mqtt_broker", "MQTT_BROKER", "127.0.0.1")
MQTT_PORT = _lazy_config("mqtt_port", "MQTT_PORT", 1883, int)
```

**注意**：MQTT 服务等使用 `str(settings.MQTT_PORT)` 或 `int(str(...))` 解析 LazyObject，因 LazyObject 在首次访问时才求值。

---

## 四、seed_platform_config 管理命令

### 4.1 职责

将 `.env` 或环境变量中的配置作为默认值写入 `platform_settings`，**仅当 key 不存在时创建**，已存在的配置默认不覆盖。

### 4.2 配置项定义

| platform_key | env_key | 默认值 | category | 说明 |
|-------------|---------|--------|----------|------|
| mqtt_broker | MQTT_BROKER | 127.0.0.1 | mqtt | MQTT/EMQX 服务器地址 |
| mqtt_port | MQTT_PORT | 1883 | mqtt | MQTT 端口 |
| mqtt_keepalive | MQTT_KEEPALIVE | 60 | mqtt | MQTT 保活间隔（秒） |
| mqtt_username | MQTT_USERNAME | "" | mqtt | MQTT 用户名（可选） |
| mqtt_password | MQTT_PASSWORD | "" | mqtt | MQTT 密码（可选） |
| device_offline_timeout | DEVICE_OFFLINE_TIMEOUT | 300 | devices | 设备离线判定超时（秒） |
| device_reconnect_attempts | DEVICE_RECONNECT_ATTEMPTS | 3 | devices | 设备重连尝试次数 |
| device_reconnect_interval | DEVICE_RECONNECT_INTERVAL | 10 | devices | 设备重连间隔（秒） |

### 4.3 命令用法

```bash
# 默认：从项目根目录 .env 加载，仅创建不存在的 key
python manage.py seed_platform_config

# 强制更新已存在的配置（用 env 值覆盖）
python manage.py seed_platform_config --force

# 指定 .env 路径
python manage.py seed_platform_config --env /path/to/.env
```

### 4.4 Docker 部署

Docker Compose 通过 `env_file: .env` 将变量注入容器，`seed_platform_config` 从 `os.environ` 读取，无需容器内存在 `.env` 文件。启动命令中在 `migrate` 之后执行：

```yaml
command: >
  sh -c "python manage.py migrate --noinput &&
    python manage.py seed_platform_config &&
    gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 1"
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

- 首次启动：若未执行 `seed_platform_config`，则使用环境变量或默认值
- 修改 platform_settings 后：需重启 Django 进程才能生效（因 settings 在启动时已求值，LazyObject 仅首次访问时求值）

若需**运行时热更新** MQTT 配置，需在 mqtt_service 内部直接调用 `get_config`，而非通过 settings。当前实现为启动时读取，修改后需重启。

---

## 七、文件结构

```
config/
├── platform_config.py          # get_config 函数
├── permissions.py              # IsSuperuser（platform_settings 写权限依赖）
└── settings.py                 # _lazy_config、MQTT_* 等

platform_settings/
├── models.py                   # PlatformConfig
├── views.py                    # PlatformConfigViewSet
├── serializers.py              # PlatformConfigSerializer
└── management/commands/
    └── seed_platform_config.py # 初始化命令
```

---

## 八、设计要点总结

1. **数据库优先**：平台配置优先从数据库读取，便于前端管理、无需改 .env
2. **环境变量回退**：数据库无或异常时回退到环境变量，兼容 Docker、传统部署
3. **延迟加载**：settings 使用 SimpleLazyObject，避免启动时 DB 未就绪
4. **seed 幂等**：默认仅创建不存在的 key，`--force` 可覆盖已有配置
5. **权限隔离**：仅超级用户可增删改平台配置，普通用户只读
