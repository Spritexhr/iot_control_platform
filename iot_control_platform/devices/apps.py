"""
devices 应用配置
负责设备模型、设备类型及设备数据
MQTT 连接与设备状态处理由 sensors 应用统一启动和注册
"""
from django.apps import AppConfig


class DevicesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = "devices"
    verbose_name = '设备管理'

    def ready(self):
        """
        应用启动时执行
        MQTT 与设备状态处理器由 sensors.apps.SensorsConfig 负责启动
        """
        pass
