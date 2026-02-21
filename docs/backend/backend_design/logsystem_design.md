# 日志系统设计文档

本文档描述物联网控制平台的日志架构，基于 Django `LOGGING` 配置，实现按模块分离、文件持久化与轮转。设计来源见 [docs/design/logging.md](../design/logging.md)。

---

## 一、架构概览

| 层级 | 说明 |
|-----|------|
| 配置入口 | `config/logging_config.py`，由 `settings.LOGGING` 导入 |
| 日志根目录 | `iot_control_platform/logs/`，启动时自动创建 |
| 输出方式 | 控制台（开发）+ 按模块分离的文件 |
| 轮转策略 | RotatingFileHandler，单文件 10MB，保留 5 个备份 |

---

## 二、目录与文件

```
iot_control_platform/
└── logs/                    # 日志根目录（自动创建，*.log 已 gitignore）
    ├── app.log              # 主应用日志（INFO+）
    ├── mqtt.log             # MQTT 连接/消息/订阅
    ├── sensors.log          # 传感器数据/状态/命令
    ├── devices.log          # 设备状态/命令
    ├── automation.log       # 自动化规则执行
    └── error.log            # 所有 ERROR 及以上汇总
```

---

## 三、Logger 与 Handler 对应关系

### 3.1 Logger 配置

| Logger 名称 | 模块范围 | handlers | 级别 |
|-------------|----------|----------|------|
| `django` | Django 框架 | console, file_app | INFO |
| `django.request` | HTTP 请求 | console_filtered, file_app, file_error | WARNING |
| `django.server` | runserver | console_filtered, file_app | INFO |
| `services.mqtt_service` | MQTT 服务 | console, file_mqtt, file_app, file_error | DEBUG |
| `services.sensors_service` | 传感器数据/状态/命令 | console, file_sensors, file_app, file_error | DEBUG |
| `services.devices_service` | 设备状态/命令 | console, file_devices, file_app, file_error | DEBUG |
| `automation` | 自动化引擎、规则、视图 | console, file_automation, file_app, file_error | DEBUG |
| `sensors` / `sensors.apps` | MQTT 自启动 | console, file_mqtt, file_app, file_error | DEBUG |
| root | 未明确指定的模块 | console, file_app, file_error | INFO |

### 3.2 Handler 与输出文件

| Handler | 文件名 | 级别 | 说明 |
|---------|--------|------|------|
| console | 标准输出 | INFO | 开发时便于调试 |
| console_filtered | 标准输出 | INFO | 过滤 browser extension 404 等噪音 |
| file_app | app.log | INFO | 主应用日志 |
| file_mqtt | mqtt.log | DEBUG | MQTT 专用 |
| file_sensors | sensors.log | DEBUG | 传感器专用 |
| file_devices | devices.log | DEBUG | 设备专用 |
| file_automation | automation.log | DEBUG | 自动化专用 |
| file_error | error.log | ERROR | 错误汇总 |

### 3.3 子模块继承

子模块使用 `logging.getLogger(__name__)` 时，会继承父 Logger 的配置。例如：

- `services.sensors_service.sensor_upload_data_handlers` → 使用 `services.sensors_service` 的配置
- `automation.engine` → 使用 `automation` 的配置

---

## 四、技术实现

### 4.1 配置文件

**路径**：`iot_control_platform/config/logging_config.py`

```python
def get_logging_config() -> dict:
    """返回 Django LOGGING 配置字典。"""
    # 创建 LOG_DIR
    # 定义 formatters、filters、handlers、loggers、root
```

**settings 引用**：

```python
# config/settings.py
from config.logging_config import LOGGING
```

### 4.2 日志格式

**verbose**（主格式）：

```
{levelname} {asctime} [{name}] {message}
```

示例：

```
INFO 2025-02-21 14:30:22 [services.mqtt_service] MQTT连接成功，已建立通信
INFO 2025-02-21 14:30:23 [services.sensors_service.sensor_upload_data_handlers] ✓ 数据保存成功 - 传感器: DHT11-WEMOS-001
ERROR 2025-02-21 14:35:10 [services.devices_service.device_command_send_service] ✗ 设备不存在: SG_80_01
```

### 4.3 轮转参数

| 参数 | 值 | 说明 |
|-----|-----|------|
| maxBytes | 10 * 1024 * 1024 (10MB) | 单文件最大容量 |
| backupCount | 5 | 保留备份数量 |
| encoding | utf-8 | 编码 |

超过 10MB 时自动轮转为 `app.log.1`、`app.log.2` 等。

### 4.4 Filter

**ignore_browser_extensions**：过滤 `django.request` 中包含 `/hybridaction/` 的 404 请求，减少浏览器扩展导致的噪音。

---

## 五、各模块 Logger 使用

| 模块 | 取得方式 | 示例 |
|-----|----------|------|
| mqtt_service | `logger = logging.getLogger(__name__)` | `logger.info("✓ 消息发布成功")` |
| sensor_upload_data_handlers | 同上 | `logger.error("✗ 传感器不存在")` |
| device_command_send_service | 同上 | `logger.warning("⚠ check_code 校验失败")` |
| automation.engine | 同上 | `logger.exception("自动化规则执行异常")` |
| sensors.apps | 同上 | `logger.info("✓ MQTT服务启动成功")` |

---

## 六、自动化规则执行时的日志捕获

`automation.views.AutomationRuleViewSet.execute` 在手动执行规则时，会临时挂载 `_LogCaptureHandler` 到以下 Logger：

- `automation`
- `services.devices_service`
- `services.sensors_service`

捕获 INFO 及以上级别日志，作为 API 响应中的 `logs` 字段返回，便于前端展示执行过程。

---

## 七、环境与扩展

### 7.1 开发 / 生产差异（设计预留）

| 配置项 | 开发 | 生产 |
|--------|------|------|
| 控制台 | 开启 | 可关闭或仅 ERROR |
| DEBUG 级别 | 写入各模块 log | 可关闭 |
| 单文件大小 | 10 MB | 可调大至 20 MB |

可通过环境变量或 `get_logging_config()` 内逻辑切换。

### 7.2 .gitignore

`iot_control_platform/.gitignore` 已包含 `*.log`，日志文件不纳入版本控制。

---

## 八、文件结构

```
config/
├── settings.py          # 导入 LOGGING
└── logging_config.py    # get_logging_config()、LOGGING

iot_control_platform/
└── logs/                # 运行时生成
    ├── app.log
    ├── mqtt.log
    ├── sensors.log
    ├── devices.log
    ├── automation.log
    └── error.log
```
