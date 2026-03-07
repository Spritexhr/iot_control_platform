# 平台配置使用指南

本文档介绍如何在开发与部署中使用平台配置（platform_settings），包括 Shell 操作、管理命令、API 调用及前端集成。架构说明见 [platform_settings_design.md](../backend_design/platform_settings_design.md)。

---

## 一、概述与前置条件

### 1.1 平台配置的作用

| 场景 | 说明 |
|-----|------|
| MQTT 连接参数 | 服务器地址、端口、用户名、密码等，可在前端修改 |
| 设备离线检测 | 离线超时、重连次数、重连间隔等 |
| 数据留存时间 | 传感器/设备数据保留天数，`cleanup_old_data` 按此清理 |
| 运行时生效 | 修改后调用 `POST /api/platform-configs/reload/` 即可生效，**无需重启服务** |

### 1.2 配置来源与职责分离

| 来源 | 职责 |
|-----|------|
| **.env** | 仅保留启动必备项：DB 密码、MQTT 地址、SECRET_KEY 等 |
| **default_config.json** | 平台配置默认值（数据留存、设备离线等），位于 `platform_settings/` |
| **platform_settings 数据库** | 运行时配置，由 seed 将 .env + JSON 合并写入，可在线修改 |

### 1.3 配置读取（get_config）

**仅从 platform_settings 数据库读取**，不存在时返回传入的 default，防止多来源混乱。

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

# 仅从 platform_settings 数据库读取，不存在时返回 default
broker = get_config('mqtt_broker', '127.0.0.1')
port = get_config('mqtt_port', 1883, int)
timeout = get_config('device_offline_timeout', 300, int)
```

---

## 三、default_config.json 与 seed_platform_config

### 3.1 配置文件说明

`platform_settings/default_config.json` 定义所有平台配置的默认值：

- **env_key 非空**：该配置可由 .env 覆盖（如 mqtt_broker、mqtt_port）
- **env_key 为空**：仅使用 JSON 中的默认值（如 sensor_data_retention_days）

新增配置时，在 JSON 的 `configs` 数组中添加一项即可。

### 3.2 首次初始化

将 `default_config.json` 与 `.env` 合并后写入 platform_settings，**仅创建不存在的 key**：

```bash
python manage.py seed_platform_config
```

输出示例：

```
已加载 10 项默认配置
加载 .env: /path/to/project/.env
  创建: mqtt_broker = 116.62.68.29
  创建: mqtt_port = 1883
  跳过（已存在）: mqtt_keepalive
  ...

完成: 创建 5 条, 更新 0 条
```

### 3.3 强制更新已有配置

使用 `.env` 中的值覆盖数据库中已存在的配置：

```bash
python manage.py seed_platform_config --force
```

### 3.4 指定 .env 路径

```bash
python manage.py seed_platform_config --env /custom/path/.env
```

### 3.5 Docker 部署

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

### 4.6 使配置生效（reload，仅超级用户）

修改 MQTT、设备离线等配置后，调用此接口使修改**立即生效**，无需重启 Django 服务：

```bash
curl -X POST -H "Authorization: Bearer <access_token>" \
  http://localhost:8000/api/platform-configs/reload/
```

响应示例：

```json
{"message": "reload completed", "results": {"mqtt": "reconnected"}}
```

- **mqtt**：`reconnected` 表示 MQTT 已重连并应用新配置；`not_running` 表示 MQTT 未启动
- 数据留存配置（`sensor_data_retention_days` 等）在 `cleanup_old_data` 执行时自动读取最新值，无需 reload

---

## 五、数据清理（cleanup_old_data）

### 5.1 按配置清理过期数据

根据 `sensor_data_retention_days`、`device_data_retention_days` 清理超期数据：

```bash
python manage.py cleanup_old_data
```

### 5.2 试运行（仅统计不删除）

```bash
python manage.py cleanup_old_data --dry-run
```

### 5.3 定时执行（cron 示例）

```cron
0 2 * * * cd /path/to/project && python manage.py cleanup_old_data
```

---

## 六、前端集成

### 6.1 系统设置页

前端「系统设置」页包含「平台配置」区块，超级用户可：

- 查看配置列表（按 category 分组）
- 编辑配置值
- 新增配置（key 需唯一）
- 删除配置
- 点击「使配置生效」调用 reload 接口

### 6.2 API 模块

`frontend/src/api/platformConfig.js` 提供：

- `getPlatformConfigs()`：获取列表
- `getPlatformConfig(key)`：获取单个
- `createPlatformConfig(data)`：创建
- `updatePlatformConfig(key, data)`：更新
- `deletePlatformConfig(key)`：删除
- `reloadPlatformConfig()`：使配置生效（MQTT 重连等）

### 6.3 权限控制

- `isSuperuser` 为 true 时显示新增、编辑、删除、reload 按钮
- 非超级用户仅可查看列表

---

## 七、配置项速查表

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
| sensor_data_retention_days | - | 30 | int | 传感器数据保留天数 |
| device_data_retention_days | - | 30 | int | 设备数据保留天数 |

---

## 八、常见问题

### Q1：修改平台配置后 MQTT 未生效？

**解决**：调用 `POST /api/platform-configs/reload/`，MQTT 会自动重连并应用新配置，**无需重启服务**。

### Q2：数据留存配置修改后何时生效？

**说明**：`sensor_data_retention_days`、`device_data_retention_days` 在每次执行 `cleanup_old_data` 时从数据库读取，无需 reload。修改后下次执行清理即生效。

### Q3：Docker 部署时 seed_platform_config 找不到 .env？

**说明**：Docker 通过 `env_file` 将变量注入容器环境，`seed_platform_config` 从 `os.environ` 读取，无需容器内存在 `.env` 文件。只要 `docker-compose.yml` 中配置了 `env_file: .env` 即可。

### Q4：如何添加新的配置项？

1. 在 `platform_settings/default_config.json` 的 `configs` 数组中添加一项，如：
   ```json
   {"key": "new_key", "default": "value", "env_key": null, "category": "general", "description": "说明"}
   ```
2. 若需从 .env 覆盖，设置 `env_key` 为环境变量名
3. 执行 `python manage.py seed_platform_config` 初始化

### Q5：敏感信息（如 MQTT 密码）应放哪里？

建议仍通过环境变量管理，不写入 platform_settings。若写入，需确保仅超级用户可访问 API，并做好生产环境 HTTPS 与访问控制。
