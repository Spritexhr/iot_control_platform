"""
IoT 控制平台 - 日志配置

将日志按模块分离到不同文件，支持按天轮转与持久化。
默认保留 2 天日志（TimedRotatingFileHandler backupCount=1）
详见 docs/backend/backend_design/logsystem_design.md
"""

from pathlib import Path

# config/ 的父目录 = iot_control_platform/
BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# 按天轮转，保留 2 天（当前 + 1 个备份）
LOG_RETENTION_DAYS = 1  # backupCount，当前日 + 1 备份 = 2 天


def get_logging_config() -> dict:
    """返回 Django LOGGING 配置字典。"""
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "verbose": {
                "format": "{levelname} {asctime} [{name}] {message}",
                "style": "{",
            },
            "simple": {
                "format": "{levelname} {message}",
                "style": "{",
            },
        },
        "filters": {
            "ignore_browser_extensions": {
                "()": "django.utils.log.CallbackFilter",
                "callback": lambda record: "/hybridaction/" not in record.getMessage(),
            },
        },
        "handlers": {
            # 控制台（开发时保留）
            "console": {
                "level": "INFO",
                "class": "logging.StreamHandler",
                "formatter": "verbose",
            },
            "console_filtered": {
                "level": "INFO",
                "class": "logging.StreamHandler",
                "formatter": "verbose",
                "filters": ["ignore_browser_extensions"],
            },
            # 主应用日志（按天轮转，保留 2 天）
            "file_app": {
                "level": "INFO",
                "class": "logging.handlers.TimedRotatingFileHandler",
                "filename": str(LOG_DIR / "app.log"),
                "when": "midnight",
                "interval": 1,
                "backupCount": LOG_RETENTION_DAYS,
                "formatter": "verbose",
                "encoding": "utf-8",
            },
            # MQTT 专用
            "file_mqtt": {
                "level": "DEBUG",
                "class": "logging.handlers.TimedRotatingFileHandler",
                "filename": str(LOG_DIR / "mqtt.log"),
                "when": "midnight",
                "interval": 1,
                "backupCount": LOG_RETENTION_DAYS,
                "formatter": "verbose",
                "encoding": "utf-8",
            },
            # 传感器
            "file_sensors": {
                "level": "DEBUG",
                "class": "logging.handlers.TimedRotatingFileHandler",
                "filename": str(LOG_DIR / "sensors.log"),
                "when": "midnight",
                "interval": 1,
                "backupCount": LOG_RETENTION_DAYS,
                "formatter": "verbose",
                "encoding": "utf-8",
            },
            # 设备
            "file_devices": {
                "level": "DEBUG",
                "class": "logging.handlers.TimedRotatingFileHandler",
                "filename": str(LOG_DIR / "devices.log"),
                "when": "midnight",
                "interval": 1,
                "backupCount": LOG_RETENTION_DAYS,
                "formatter": "verbose",
                "encoding": "utf-8",
            },
            # 自动化
            "file_automation": {
                "level": "DEBUG",
                "class": "logging.handlers.TimedRotatingFileHandler",
                "filename": str(LOG_DIR / "automation.log"),
                "when": "midnight",
                "interval": 1,
                "backupCount": LOG_RETENTION_DAYS,
                "formatter": "verbose",
                "encoding": "utf-8",
            },
            # 平台配置（seed、cleanup 等）
            "file_platform_settings": {
                "level": "INFO",
                "class": "logging.handlers.TimedRotatingFileHandler",
                "filename": str(LOG_DIR / "platform_settings.log"),
                "when": "midnight",
                "interval": 1,
                "backupCount": LOG_RETENTION_DAYS,
                "formatter": "verbose",
                "encoding": "utf-8",
            },
            # 错误汇总
            "file_error": {
                "level": "ERROR",
                "class": "logging.handlers.TimedRotatingFileHandler",
                "filename": str(LOG_DIR / "error.log"),
                "when": "midnight",
                "interval": 1,
                "backupCount": LOG_RETENTION_DAYS,
                "formatter": "verbose",
                "encoding": "utf-8",
            },
        },
        "loggers": {
            # Django 请求（过滤浏览器扩展 404）
            "django.request": {
                "handlers": ["console_filtered", "file_app", "file_error"],
                "level": "WARNING",
                "propagate": False,
            },
            # Django 服务器
            "django.server": {
                "handlers": ["console_filtered", "file_app"],
                "level": "INFO",
                "propagate": False,
            },
            # Django 框架
            "django": {
                "handlers": ["console", "file_app"],
                "level": "INFO",
                "propagate": False,
            },
            # MQTT 服务
            "services.mqtt_service": {
                "handlers": ["console", "file_mqtt", "file_app", "file_error"],
                "level": "DEBUG",
                "propagate": False,
            },
            # 传感器服务（含数据、状态、命令）
            "services.sensors_service": {
                "handlers": ["console", "file_sensors", "file_app", "file_error"],
                "level": "DEBUG",
                "propagate": False,
            },
            # 设备服务
            "services.devices_service": {
                "handlers": ["console", "file_devices", "file_app", "file_error"],
                "level": "DEBUG",
                "propagate": False,
            },
            # 自动化
            "automation": {
                "handlers": ["console", "file_automation", "file_app", "file_error"],
                "level": "DEBUG",
                "propagate": False,
            },
            # sensors 应用（启动时 MQTT 初始化）
            "sensors": {
                "handlers": ["console", "file_mqtt", "file_app", "file_error"],
                "level": "DEBUG",
                "propagate": False,
            },
            "sensors.apps": {
                "handlers": ["console", "file_mqtt", "file_app", "file_error"],
                "level": "DEBUG",
                "propagate": False,
            },
            # 平台配置（seed_platform_config、cleanup_old_data）
            "platform_settings": {
                "handlers": ["console", "file_platform_settings", "file_app", "file_error"],
                "level": "INFO",
                "propagate": False,
            },
        },
        "root": {
            "handlers": ["console", "file_app", "file_error"],
            "level": "INFO",
        },
    }


# 供 settings.py 导入
LOGGING = get_logging_config()

