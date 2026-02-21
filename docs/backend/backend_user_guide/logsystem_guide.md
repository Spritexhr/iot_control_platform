# 日志系统使用指南

本文档介绍如何在项目中正确使用日志，包括 Logger 获取、级别选择、查看与排查。设计说明见 [logsystem_design.md](../backend_design/logsystem_design.md)。

---

## 一、基本用法

### 1.1 获取 Logger

在每个模块顶部使用 `__name__` 获取与模块路径对应的 Logger：

```python
import logging

logger = logging.getLogger(__name__)
```

这样会自动匹配 `logging_config.py` 中配置的 Logger 层级，例如：

- `services.mqtt_service` → 输出到 mqtt.log、app.log、error.log
- `services.sensors_service.xxx` → 输出到 sensors.log、app.log、error.log
- `automation.engine` → 输出到 automation.log、app.log、error.log

### 1.2 常用级别

```python
logger.debug("详细调试信息，仅 DEBUG 级别输出")
logger.info("正常流程：连接成功、命令发送、数据保存")
logger.warning("异常但不致命：设备不存在、校验失败")
logger.error("错误：连接失败、保存失败")
logger.exception("错误并自动附加 traceback")
```

### 1.3 避免使用 print

日志应统一通过 `logger` 输出，便于按模块分离和持久化。若为临时调试，可在排查后改回 `logger.debug`。

```python
# 不推荐
print("连接成功")

# 推荐
logger.info("✓ MQTT连接成功")
```

---

## 二、查看日志

### 2.1 日志文件位置

日志默认在 `iot_control_platform/logs/` 下：

```bash
# 项目根目录下
cd iot_control_platform/logs
ls
# app.log  mqtt.log  sensors.log  devices.log  automation.log  error.log
```

### 2.2 实时查看

```bash
# 主应用日志
tail -f iot_control_platform/logs/app.log

# 只看错误
tail -f iot_control_platform/logs/error.log

# MQTT 相关
tail -f iot_control_platform/logs/mqtt.log

# 传感器相关
tail -f iot_control_platform/logs/sensors.log

# 设备相关
tail -f iot_control_platform/logs/devices.log

# 自动化相关
tail -f iot_control_platform/logs/automation.log
```

### 2.3 搜索

```bash
# 按传感器 ID 搜索
grep "DHT11-WEMOS-001" iot_control_platform/logs/sensors.log

# 按设备 ID 搜索
grep "SG_80_01" iot_control_platform/logs/devices.log

# 按错误级别
grep "ERROR" iot_control_platform/logs/error.log
```

---

## 三、各模块日志来源

| 文件 | 主要来源 |
|-----|----------|
| app.log | Django、MQTT、传感器、设备、自动化、root |
| mqtt.log | services.mqtt_service、sensors.apps |
| sensors.log | services.sensors_service（数据、状态、命令） |
| devices.log | services.devices_service（状态、命令） |
| automation.log | automation（engine、views） |
| error.log | 所有 WARNING/ERROR 及以上 |

---

## 四、自动化规则脚本中的日志

自动化脚本运行在 `engine.execute_rule` 中，脚本内的 `print()` 会输出到标准输出；若通过 API 手动执行，会被 `automation.views.execute` 的 `stdout_capture` 捕获并返回。

建议在需要记录到日志时，在脚本中获取 Logger 并输出：

```python
# 在自动化脚本中（若需写入日志）
import logging
logger = logging.getLogger('automation.engine')  # 或 automation
logger.info("湿度超限，已发送告警")
```

注意：脚本通过 `exec` 执行，`__name__` 可能与预期不同，可直接使用 `logging.getLogger('automation')` 以确保写入 automation.log。

---

## 五、修改日志配置（高级）

### 5.1 调整轮转大小

编辑 `config/logging_config.py`：

```python
MAX_BYTES = 20 * 1024 * 1024  # 改为 20MB
BACKUP_COUNT = 10              # 保留 10 个备份
```

### 5.2 关闭控制台输出

将各 logger 的 `handlers` 中去掉 `"console"`，或新增一个 `console` 的 level 为 `ERROR` 的变体。

### 5.3 新增模块专用 Logger

在 `get_logging_config()` 的 `loggers` 中增加：

```python
"your_app.your_module": {
    "handlers": ["console", "file_app", "file_error"],
    "level": "DEBUG",
    "propagate": False,
},
```

并视需添加对应的 `file_yourmodule` handler。

---

## 六、常见问题

### 6.1 日志文件未生成

- 确认 `iot_control_platform/logs/` 目录有写权限
- `logging_config.py` 中 `LOG_DIR.mkdir(exist_ok=True)` 会自动创建目录

### 6.2 中文乱码

所有 Handler 已设置 `encoding='utf-8'`，若仍有乱码，检查终端或查看工具编码。

### 6.3 日志过多影响性能

- 生产环境可将 DEBUG 级关闭，仅保留 INFO 及以上
- 调整各 logger 的 `level` 为 `INFO` 或 `WARNING`

### 6.4 多进程写入

Django runserver 为单进程；使用 gunicorn 等多进程时，`RotatingFileHandler` 可能产生多进程竞争。可考虑按进程分文件或使用支持多进程的 Handler（如 `ConcurrentLogHandler`）。
