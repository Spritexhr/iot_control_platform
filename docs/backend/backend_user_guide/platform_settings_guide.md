# 平台配置使用指南

本文档介绍如何在开发与部署中使用平台配置（platform_settings），包括 Shell 操作、管理命令、API 调用及前端集成。架构说明见 [platform_settings_design.md](../backend_design/platform_settings_design.md)。

---

## 一、概述与前置条件

### 1.1 平台配置的作用

| 场景 | 说明 |
|-----|------|
| MQTT 连接参数 | 服务器地址、端口、用户名、密码等，可在前端修改 |
| 设备离线检测 | 离线超时、重连次数、重连间隔等 |
| 运行时调整 | 修改后需重启 Django 进程生效（MQTT 等启动时读取） |

### 1.2 配置来源优先级

1. **platform_settings 数据库**（优先）
2. **环境变量**（回退）
3. **默认值**（最后）

### 1.3 权限说明

| 操作 | 权限 |
|-----|------|
| 查看配置列表、详情 | 已认证用户 |
| 新增、编辑、删除配置 | 超级用户（is_superuser） |

---

## 二、Django Shell 操作

### 2.1 启动 Shell 并导入

```bash
python manage.py shell
```

```python
from platform_settings.models import PlatformConfig
from config.platform_config import get_config
```

### 2.2 查询配置

```python
# 全部配置
PlatformConfig.objects.all()

# 按 key 查询
cfg = PlatformConfig.objects.get(key='mqtt_broker')
cfg.value   # 配置值，如 "127.0.0.1"
cfg.category  # 如 "mqtt"
cfg.description  # 如 "MQTT/EMQX 服务器地址"

# 按分类筛选
PlatformConfig.objects.filter(category='mqtt')
PlatformConfig.objects.filter(category='devices')
```

### 2.3 创建配置

```python
PlatformConfig.objects.create(
    key='mqtt_broker',
    value='116.62.68.29',
    category='mqtt',
    description='MQTT/EMQX 服务器地址'
)

# value 支持多种类型
PlatformConfig.objects.create(key='mqtt_port', value=1883, category='mqtt', description='MQTT 端口')
PlatformConfig.objects.create(key='some_list', value=['a', 'b'], category='general', description='示例列表')
```

### 2.4 更新配置

```python
cfg = PlatformConfig.objects.get(key='mqtt_broker')
cfg.value = '192.168.1.100'
cfg.save()
```

### 2.5 使用 get_value 类方法

```python
# 获取单个配置，不存在时返回 default
val = PlatformConfig.get_value('mqtt_broker', default='127.0.0.1')
# 返回数据库中的 value，或 default
```

### 2.6 使用 get_config 统一读取

```python
from config.platform_config import get_config

# 优先 platform_settings，回退环境变量，再回退默认值
broker = get_config('mqtt_broker', 'MQTT_BROKER', '127.0.0.1')
port = get_config('mqtt_port', 'MQTT_PORT', 1883, int)
timeout = get_config('device_offline_timeout', 'DEVICE_OFFLINE_TIMEOUT', 300, int)
```

---

## 三、seed_platform_config 管理命令

### 3.1 首次初始化

将 `.env` 或环境变量中的默认值写入 platform_settings，**仅创建不存在的 key**：

```bash
python manage.py seed_platform_config
```

输出示例：

```
加载 .env: /path/to/project/.env
  创建: mqtt_broker = 116.62.68.29
  创建: mqtt_port = 1883
  跳过（已存在）: mqtt_keepalive
  ...

完成: 创建 5 条, 更新 0 条
```

### 3.2 强制更新已有配置

使用 `.env` 中的值覆盖数据库中已存在的配置：

```bash
python manage.py seed_platform_config --force
```

### 3.3 指定 .env 路径

```bash
python manage.py seed_platform_config --env /custom/path/.env
```

### 3.4 Docker 部署

Docker 通过 `env_file` 注入环境变量，容器内无需 `.env` 文件。`seed_platform_config` 从 `os.environ` 读取，在 `migrate` 之后执行即可：

```yaml
command: >
  sh -c "python manage.py migrate --noinput &&
    python manage.py seed_platform_config &&
    gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 1"
```

---

## 四、API 调用

### 4.1 获取配置列表

```bash
# 需携带 JWT Token
curl -H "Authorization: Bearer <access_token>" \
  http://localhost:8000/api/platform-configs/
```

响应示例：

```json
[
  {"key": "mqtt_broker", "value": "116.62.68.29", "category": "mqtt", "description": "MQTT/EMQX 服务器地址"},
  {"key": "mqtt_port", "value": 1883, "category": "mqtt", "description": "MQTT 端口"}
]
```

### 4.2 获取单个配置

```bash
curl -H "Authorization: Bearer <access_token>" \
  http://localhost:8000/api/platform-configs/mqtt_broker/
```

### 4.3 创建配置（仅超级用户）

```bash
curl -X POST -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"key":"custom_key","value":"custom_value","category":"general","description":"自定义配置"}' \
  http://localhost:8000/api/platform-configs/
```

### 4.4 更新配置（仅超级用户）

```bash
curl -X PATCH -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"value":"192.168.1.100"}' \
  http://localhost:8000/api/platform-configs/mqtt_broker/
```

### 4.5 删除配置（仅超级用户）

```bash
curl -X DELETE -H "Authorization: Bearer <access_token>" \
  http://localhost:8000/api/platform-configs/custom_key/
```

---

## 五、前端集成

### 5.1 系统设置页

前端「系统设置」页包含「平台配置」区块，超级用户可：

- 查看配置列表（按 category 分组）
- 编辑配置值
- 新增配置（key 需唯一）
- 删除配置

### 5.2 API 模块

`frontend/src/api/platformConfig.js` 提供：

- `getPlatformConfigs()`：获取列表
- `getPlatformConfig(key)`：获取单个
- `createPlatformConfig(data)`：创建
- `updatePlatformConfig(key, data)`：更新
- `deletePlatformConfig(key)`：删除

### 5.3 权限控制

- `isSuperuser` 为 true 时显示新增、编辑、删除按钮
- 非超级用户仅可查看列表

---

## 六、配置项速查表

| key | 环境变量 | 默认值 | 类型 | 说明 |
|-----|---------|--------|------|------|
| mqtt_broker | MQTT_BROKER | 127.0.0.1 | str | MQTT 服务器地址 |
| mqtt_port | MQTT_PORT | 1883 | int | MQTT 端口 |
| mqtt_keepalive | MQTT_KEEPALIVE | 60 | int | MQTT 保活间隔（秒） |
| mqtt_username | MQTT_USERNAME | "" | str | MQTT 用户名 |
| mqtt_password | MQTT_PASSWORD | "" | str | MQTT 密码 |
| device_offline_timeout | DEVICE_OFFLINE_TIMEOUT | 300 | int | 设备离线超时（秒） |
| device_reconnect_attempts | DEVICE_RECONNECT_ATTEMPTS | 3 | int | 重连尝试次数 |
| device_reconnect_interval | DEVICE_RECONNECT_INTERVAL | 10 | int | 重连间隔（秒） |

---

## 七、常见问题

### Q1：修改平台配置后 MQTT 未生效？

**原因**：MQTT 连接参数在 Django 启动时读取，修改数据库后需**重启 Django 进程**（如 `runserver`、`gunicorn`）才能生效。

### Q2：Docker 部署时 seed_platform_config 找不到 .env？

**说明**：Docker 通过 `env_file` 将变量注入容器环境，`seed_platform_config` 从 `os.environ` 读取，无需容器内存在 `.env` 文件。只要 `docker-compose.yml` 中配置了 `env_file: .env` 即可。

### Q3：如何添加新的配置项？

1. 在 `seed_platform_config.py` 的 `CONFIG_ITEMS` 中添加 `(platform_key, env_key, default, category, description, value_type)`
2. 若需在 settings 中使用，在 `config/settings.py` 中添加 `_lazy_config(...)` 或直接调用 `get_config`
3. 执行 `python manage.py seed_platform_config` 初始化

### Q4：敏感信息（如 MQTT 密码）应放哪里？

建议仍通过环境变量管理，不写入 platform_settings。若写入，需确保仅超级用户可访问 API，并做好生产环境 HTTPS 与访问控制。
