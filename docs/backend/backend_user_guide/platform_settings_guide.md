# 平台配置使用指南

本文档介绍如何在开发与部署中使用平台配置（platform_settings），包括 `configure` 命令、Shell 操作、API 调用与前端集成。架构说明见 [platform_settings_design.md](../backend_design/platform_settings_design.md)。

---

## 一、概述与前置条件

### 1.1 平台配置的作用

| 场景 | 说明 |
|-----|------|
| MQTT 连接参数 | 服务器地址、端口、用户名、密码 |
| 设备离线检测 | 离线超时、重连次数、重连间隔 |
| 数据留存时间 | 传感器/设备数据保留天数，`cleanup_old_data` 按此清理 |
| 运行时生效 | 修改后调用 `POST /api/platform-configs/reload/` 即可生效，**无需重启服务** |

### 1.2 配置职责分工

| 来源 | 职责 |
|-----|------|
| **`.env`** | 仅进程级启动必备：`SECRET_KEY`、`DEBUG`、`ALLOWED_HOSTS`、`DB_*`、端口 |
| **`platform_settings/defaults.py`** | `DEFAULT_CONFIGS` 常量，定义所有运行期可调配置的默认值 |
| **`PlatformConfig` 表（数据库）** | 运行时唯一真源，由 `configure --init` 写入默认值，可通过 wizard / Admin / API 修改 |

`.env` 不再包含 MQTT 相关项；MQTT 服务地址、凭据等全部通过 `configure` 命令维护。

### 1.3 配置读取（get_config）

业务代码统一通过 `config.platform_config.get_config()` 从 `PlatformConfig` 表读取，不存在时返回传入的 default。

### 1.4 权限说明

| 操作 | 权限 |
|-----|------|
| 查看配置列表、详情 | 已认证用户 |
| 新增、编辑、删除配置（API） | 超级用户（is_superuser） |
| `configure` 命令 | 容器内执行（已通过 Docker 隔离） |

---

## 二、`configure` 管理命令（写入唯一入口）

### 2.1 交互式 wizard（推荐用于首次部署）

```bash
docker compose exec backend python manage.py configure
```

按 `DEFAULT_CONFIGS` 顺序逐项询问；直接回车保留当前值，密码字段不回显。

```
=== 平台配置 wizard ===
直接回车保留当前值；按 Ctrl+C 中止。

[mqtt]
  mqtt_broker (MQTT/EMQX 服务器地址) [127.0.0.1]: 192.168.1.10
    [updated] mqtt_broker = 192.168.1.10
  mqtt_port (MQTT 端口（默认 1883...）) [1883]: 1883
    [updated] mqtt_port = 1883
  mqtt_username (...) []:
  mqtt_password (...) []: ***
    [updated] mqtt_password = ***
...
触发 reload:
  MQTT: reconnected
```

写完默认会触发 `reload`，让 MQTT 等服务无感重连，无需重启容器。

### 2.2 单键设置（CI / 脚本化）

```bash
# 单条
docker compose exec backend python manage.py configure --set mqtt_broker=192.168.1.10

# 多条
docker compose exec backend python manage.py configure \
    --set mqtt_broker=192.168.1.10 \
    --set mqtt_port=1883
```

值会按 `DEFAULT_CONFIGS` 中 default 的类型自动转换：`int` 用 `int(...)`、`bool` 接受 `true/1/yes`、`list/dict` 解析为 JSON。

### 2.3 重置为默认

```bash
docker compose exec backend python manage.py configure --unset mqtt_password
```

把 `mqtt_password` 重置为 `defaults.py` 中的默认值（不会从 DB 删除条目）。

### 2.4 列出所有当前值

```bash
docker compose exec backend python manage.py configure --list
```

```
[mqtt]
  mqtt_broker = 192.168.1.10   # MQTT/EMQX 服务器地址
  mqtt_port = 1883
  mqtt_password = ***           # 密码已打码
[devices]
  device_offline_timeout = 300
  ...
```

### 2.5 首次/升级初始化

```bash
docker compose exec backend python manage.py configure --init
```

仅写入 `DEFAULT_CONFIGS` 中**当前 DB 缺失**的 key，已存在的 key 一律不动。Docker 启动 command 自动调用此模式。

### 2.6 跳过 reload

```bash
docker compose exec backend python manage.py configure --set xxx=yyy --no-reload
```

写完不调 MQTT reload（启动阶段会用到，因为此时 MQTT 服务还没起）。

---

## 三、Django Shell 操作（兜底）

```bash
python manage.py shell
```

```python
from platform_settings.models import PlatformConfig
from config.platform_config import get_config

# 查询
PlatformConfig.objects.filter(category='mqtt')
cfg = PlatformConfig.objects.get(key='mqtt_broker')

# 修改
cfg.value = '192.168.1.100'
cfg.save()

# 业务代码统一入口
broker = get_config('mqtt_broker', '127.0.0.1', str)
port = get_config('mqtt_port', 1883, int)
```

修改后同样需要触发 reload（API 或重启）才能让 MQTT 应用新值。

---

## 四、API 调用

### 4.1 获取配置列表

```bash
curl -H "Authorization: Bearer <access_token>" \
  http://localhost:8000/api/platform-configs/
```

### 4.2 更新配置（仅超级用户）

```bash
curl -X PATCH -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"value":"192.168.1.100"}' \
  http://localhost:8000/api/platform-configs/mqtt_broker/
```

### 4.3 reload（仅超级用户）

```bash
curl -X POST -H "Authorization: Bearer <access_token>" \
  http://localhost:8000/api/platform-configs/reload/
```

响应：

```json
{"message": "reload completed", "results": {"mqtt": "reconnected"}}
```

数据留存配置（`*_retention_days`）由 `cleanup_old_data` 每次执行时读取最新值，**不需要 reload**。

---

## 五、数据清理（cleanup_old_data）

```bash
# 立即执行
python manage.py cleanup_old_data

# 试运行
python manage.py cleanup_old_data --dry-run

# 自定义分批
python manage.py cleanup_old_data --batch-size 500
```

**注意**：从 0.7 起，`cleanup_old_data` 不再放在容器启动 command 里；建议挂宿主机 cron：

```cron
0 2 * * * docker compose exec -T backend python manage.py cleanup_old_data
```

或通过 API（仅超级用户）：

```bash
curl -X POST -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/platform-configs/cleanup-old-data/
```

---

## 六、前端集成

### 6.1 系统设置页

「系统设置」→「平台配置」区块（仅超级用户可见编辑控件）：

- 查看配置列表（按 category 分组）
- 编辑配置值
- 点击「使配置生效」调用 reload 接口

### 6.2 API 模块

`frontend/src/api/platformConfig.js` 提供 `getPlatformConfigs / updatePlatformConfig / reloadPlatformConfig` 等。

---

## 七、配置项速查表

`DEFAULT_CONFIGS` 在 `platform_settings/defaults.py` 中维护，新增一条即可：

| key | 默认值 | 类型 | 分类 | 说明 |
|-----|-------|------|------|------|
| mqtt_broker | 127.0.0.1 | str | mqtt | MQTT 服务器地址 |
| mqtt_port | 1883 | int | mqtt | MQTT 端口 |
| mqtt_keepalive | 60 | int | mqtt | 保活间隔（秒） |
| mqtt_username | "" | str | mqtt | MQTT 用户名 |
| mqtt_password | "" | str (secret) | mqtt | MQTT 密码 |
| device_offline_timeout | 300 | int | devices | 离线判定（秒） |
| device_reconnect_attempts | 3 | int | devices | 重连次数 |
| device_reconnect_interval | 10 | int | devices | 重连间隔（秒） |
| sensor_data_retention_days | 30 | int | data_retention | 传感器数据保留天数 |
| device_data_retention_days | 30 | int | data_retention | 设备数据保留天数 |

---

## 八、常见问题

### Q1：首次部署后 MQTT 连不上？

**预期行为**。`configure --init` 写入默认值 `127.0.0.1:1883` 仅作占位，**必须**通过 `configure` wizard 改为实际 EMQX 地址：

```bash
docker compose exec backend python manage.py configure
```

### Q2：修改 `.env` 中的 `MQTT_BROKER` 没生效？

`.env` 不再包含 MQTT 配置——相关项已迁移到 `PlatformConfig` 表。请改用 `configure --set mqtt_broker=...`。

### Q3：升级后多了几个新配置项怎么办？

`docker compose up -d` 启动时自动跑 `configure --init`，会**只补缺失的 key**，你已经设置过的值不会被覆盖。

### Q4：怎么把所有配置导出到文件 / 从文件批量恢复？

目前没有 `--from-file`，可以用：

```bash
# 导出
docker compose exec backend python manage.py configure --list > configs.txt

# 批量设置（手写 shell）
for line in mqtt_broker=192.168.1.10 mqtt_port=1883; do
  docker compose exec backend python manage.py configure --set "$line"
done
```

如果有强需求可以后续给 `configure` 加 `--from-file` 选项。

### Q5：MQTT 密码进 DB 安全吗？

`PlatformConfig.value` 是 `JSONField`，明文存储。本平台定位是**单团队/单家庭部署**，DB 在内网，能访问 DB 的人即拥有完整管理权。如果你的部署场景对此敏感，建议：
- 部署在内网独立机器
- 限制 MySQL 访问 IP
- Admin 页面用 HTTPS
- 或自行扩展 `PlatformConfig` 加密密码字段
