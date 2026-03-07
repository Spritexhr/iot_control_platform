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
        应用启动时执行
        在 shell / runscript / runserver 模式下自动启动 MQTT 服务
        """
        if not self._should_start_mqtt():
            return

        if SensorsConfig.mqtt_service_started:
            return

        self._start_mqtt_service()

    def _should_start_mqtt(self) -> bool:
        """
        判断当前命令是否需要在启动时自动连接 MQTT
        
        - runserver: 仅子进程启动（RUN_MAIN=true），避免 reloader 父进程重复连接
        - gunicorn / uwsgi: Docker 等生产环境使用，需要启动 MQTT
        - shell / runscript: 直接启动，便于在交互环境或脚本中使用 MQTT
        - test / migrate / makemigrations: 不启动
        """
        if 'test' in sys.argv or 'migrate' in sys.argv or 'makemigrations' in sys.argv:
            return False

        if 'runserver' in sys.argv:
            return os.environ.get('RUN_MAIN') == 'true'

        # Gunicorn / uWSGI：Docker 部署时使用，需启动 MQTT
        if any(x in sys.argv[0].lower() for x in ('gunicorn', 'uwsgi')):
            return True

        if 'shell' in sys.argv or 'runscript' in sys.argv:
            return True

        return False
    
    def _start_mqtt_service(self) -> None:
        """启动 MQTT 服务，绑定命令服务并注册设备状态处理器"""
        try:
            # 启动前自动执行 seed_platform_config，确保配置已写入数据库
            from django.core.management import call_command
            call_command("seed_platform_config")
            # 启动时执行一次数据清理
            call_command("cleanup_old_data")

            from services.mqtt_service import mqtt_service
            from services.sensors_service.sensor_command_send_service import sensor_command_send_service
            from services.devices_service.device_command_send_service import device_command_send_service
            
            logger.info("=" * 60)
            logger.info("正在启动MQTT服务...")
            
            # 连接MQTT服务器
            if not mqtt_service.connect(timeout=5):
                logger.error("MQTT连接失败，请检查配置")
                return
            
            # 设置控制服务的MQTT实例
            sensor_command_send_service.set_mqtt_service(mqtt_service)
            device_command_send_service.set_mqtt_service(mqtt_service)
            logger.info("✓ 传感器/设备控制服务已初始化")
            
            # 使用新的数据处理器（自动注册和订阅）
            mqtt_service.setup_sensor_data_handler()
            mqtt_service.setup_sensor_status_handler()
            mqtt_service.setup_device_status_handler()
            
            # 标记为已启动
            SensorsConfig.mqtt_service_started = True
            
            logger.info("✓ MQTT服务启动成功")
            logger.info("  Shell 中使用: from services.mqtt_service import mqtt_service")
            logger.info("  设备控制: from services.devices_service.device_command_send_service import device_command_send_service")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"启动MQTT服务失败: {e}", exc_info=True)
