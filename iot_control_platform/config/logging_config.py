"""
IoT 控制平台 - 日志配置

将日志按模块分离到不同文件，支持按天轮转与持久化。
默认保留 2 天日志（TimedRotatingFileHandler backupCount=1）
详见 docs/backend/backend_design/logsystem_design.md

Windows 兼容：
1. TimedRotatingFileHandler 在 Windows 上轮转时会因文件被占用而 PermissionError，
   使用 WindowsTimedRotatingFileHandler 在轮转前关闭文件句柄。
2. Django runserver 的 autoreload 会启动父+子两进程，都会打开日志文件。
   父进程（RUN_MAIN 非 true）仅用控制台，避免双进程争用同一文件。
"""

import os
import sys
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler

# config/ 的父目录 = iot_control_platform/
BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# 按天轮转，保留 2 天（当前 + 1 个备份）
LOG_RETENTION_DAYS = 1  # backupCount，当前日 + 1 备份 = 2 天

# Django autoreload 父进程不写文件日志，避免与子进程争用（Windows PermissionError）
_IS_RELOADER_PARENT = os.environ.get("RUN_MAIN") != "true"


class WindowsTimedRotatingFileHandler(TimedRotatingFileHandler):
    """Windows 兼容的按天轮转 Handler，轮转前关闭文件避免 PermissionError。"""

    def doRollover(self):
        if sys.platform == "win32":
            if self.stream:
                self.stream.close()
                self.stream = None
        try:
            super().doRollover()
        except PermissionError:
            # 仍失败时（如多进程争用）跳过轮转，重新打开流以继续写入
            if self.stream is None and not self.delay:
                self.stream = self._open()


def get_logging_config() -> dict:
    """返回 Django LOGGING 配置字典。"""
    # 基础 handlers：控制台
    handlers = {
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
    }
    # autoreload 父进程不注册文件 handler，避免与子进程争用（Windows PermissionError）
    if not _IS_RELOADER_PARENT:
        handlers.update({
            "file_app": {
                "level": "INFO",
                "class": "config.logging_config.WindowsTimedRotatingFileHandler",
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
                "class": "config.logging_config.WindowsTimedRotatingFileHandler",
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
                "class": "config.logging_config.WindowsTimedRotatingFileHandler",
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
                "class": "config.logging_config.WindowsTimedRotatingFileHandler",
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
                "class": "config.logging_config.WindowsTimedRotatingFileHandler",
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
                "class": "config.logging_config.WindowsTimedRotatingFileHandler",
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
                "class": "config.logging_config.WindowsTimedRotatingFileHandler",
                "filename": str(LOG_DIR / "error.log"),
                "when": "midnight",
                "interval": 1,
                "backupCount": LOG_RETENTION_DAYS,
                "formatter": "verbose",
                "encoding": "utf-8",
            },
        })

    # 父进程仅用控制台
    _req = ["console_filtered"] if _IS_RELOADER_PARENT else ["console_filtered", "file_app", "file_error"]
    _srv = ["console_filtered"] if _IS_RELOADER_PARENT else ["console_filtered", "file_app"]
    _django = ["console"] if _IS_RELOADER_PARENT else ["console", "file_app"]
    _mqtt = ["console"] if _IS_RELOADER_PARENT else ["console", "file_mqtt", "file_app", "file_error"]
    _sensors_h = ["console"] if _IS_RELOADER_PARENT else ["console", "file_sensors", "file_app", "file_error"]
    _devices_h = ["console"] if _IS_RELOADER_PARENT else ["console", "file_devices", "file_app", "file_error"]
    _auto_h = ["console"] if _IS_RELOADER_PARENT else ["console", "file_automation", "file_app", "file_error"]
    _plat_h = ["console"] if _IS_RELOADER_PARENT else ["console", "file_platform_settings", "file_app", "file_error"]
    _root_h = ["console"] if _IS_RELOADER_PARENT else ["console", "file_app", "file_error"]

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
        "handlers": handlers,
        "loggers": {
            "django.request": {"handlers": _req, "level": "WARNING", "propagate": False},
            "django.server": {"handlers": _srv, "level": "INFO", "propagate": False},
            "django": {"handlers": _django, "level": "INFO", "propagate": False},
            "services.mqtt_service": {"handlers": _mqtt, "level": "DEBUG", "propagate": False},
            "services.sensors_service": {"handlers": _sensors_h, "level": "DEBUG", "propagate": False},
            "services.devices_service": {"handlers": _devices_h, "level": "DEBUG", "propagate": False},
            "automation": {"handlers": _auto_h, "level": "DEBUG", "propagate": False},
            "sensors": {"handlers": _mqtt, "level": "DEBUG", "propagate": False},
            "sensors.apps": {"handlers": _mqtt, "level": "DEBUG", "propagate": False},
            "platform_settings": {"handlers": _plat_h, "level": "INFO", "propagate": False},
        },
        "root": {"handlers": _root_h, "level": "INFO"},
    }


# 供 settings.py 导入
LOGGING = get_logging_config()

