"""
sensors 应用配置
负责传感器模型、MQTT 连接及消息处理
"""
from django.apps import AppConfig
import logging
import os
import sys

logger = logging.getLogger(__name__)


class SensorsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = "sensors"
    verbose_name = '传感器管理'

    # 类变量，标记 MQTT 服务是否已启动（避免重复连接）
    mqtt_service_started = False

    def ready(self):
        """
        应用启动时执行。

        MQTT 客户端有两种模式：
        - subscribe=True（默认）：连接 broker、绑定 command publisher、订阅 topic、注册 handler
        - subscribe=False（IOT_MQTT_RUNNER=false）：只连接 + 绑定 publisher，不订阅
          backend web worker 走此模式：仍能发布命令（HTTP POST → MQTT publish），
          但不会重复处理上报消息（订阅由独立 mqtt_runner 容器负责）
        """
        if not self._should_run_mqtt():
            return

        if SensorsConfig.mqtt_service_started:
            return

        subscribe = not self._is_publisher_only()
        self._start_mqtt_service(subscribe=subscribe)

    def _should_run_mqtt(self) -> bool:
        """是否需要启动 MQTT 客户端（无论是否订阅）。"""
        if 'test' in sys.argv or 'migrate' in sys.argv or 'makemigrations' in sys.argv:
            return False

        if 'mqtt_runner' in sys.argv:
            return True

        if 'runserver' in sys.argv:
            return os.environ.get('RUN_MAIN') == 'true'

        # Gunicorn / uWSGI / Daphne 等 ASGI 服务器
        if any(x in sys.argv[0].lower() for x in ('gunicorn', 'uwsgi', 'daphne', 'uvicorn')):
            return True

        if 'shell' in sys.argv or 'runscript' in sys.argv:
            return True

        return False

    def _is_publisher_only(self) -> bool:
        """
        IOT_MQTT_RUNNER=false: backend web worker 走 publisher-only 模式
        （只连接发布命令，不订阅上报）。mqtt_runner 命令永远是 full subscribe。
        """
        if 'mqtt_runner' in sys.argv:
            return False
        return os.environ.get('IOT_MQTT_RUNNER', '').lower() in ('false', '0', 'no')

    def _start_mqtt_service(self, subscribe: bool = True) -> None:
        """启动 MQTT 服务。

        Args:
            subscribe: True 同时订阅 topic 注册 handler；False 仅连接 + 绑定 publisher
        """
        try:
            # configure --init 由 backend 容器启动命令负责（docker-compose.yml）。
            # mqtt_runner 不重复执行：避免与 MySQL 启动 race 时吞掉异常导致 MQTT 永不连接。
            if 'mqtt_runner' not in sys.argv:
                from django.core.management import call_command
                call_command("configure", "--init", "--no-reload")

            from services.mqtt_service import mqtt_service
            from services.sensors_service.sensor_command_send_service import sensor_command_send_service
            from services.devices_service.device_command_send_service import device_command_send_service

            mode_label = "完整模式（订阅+发布）" if subscribe else "仅发布模式（命令下发用，不订阅上报）"
            logger.info("=" * 60)
            logger.info(f"正在启动MQTT服务 - {mode_label}")

            # 连接MQTT服务器
            if not mqtt_service.connect(timeout=5):
                logger.error("MQTT连接失败，请检查配置")
                return

            # 设置控制服务的MQTT实例（无论是否订阅，命令下发都需要）
            sensor_command_send_service.set_mqtt_service(mqtt_service)
            device_command_send_service.set_mqtt_service(mqtt_service)
            logger.info("✓ 传感器/设备控制服务已初始化")

            if subscribe:
                # 数据处理器：自动注册并订阅
                mqtt_service.setup_sensor_data_handler()
                mqtt_service.setup_sensor_status_handler()
                mqtt_service.setup_device_status_handler()

            # 标记为已启动
            SensorsConfig.mqtt_service_started = True

            logger.info("✓ MQTT服务启动成功")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"启动MQTT服务失败: {e}", exc_info=True)
