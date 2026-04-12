"""
传感器控制服务模块
基于 BaseCommandSendService，提供传感器级命令发送与校验码确认
"""
import logging

from sensors.models import Sensor
from services.base_command_send_service import BaseCommandSendService

logger = logging.getLogger(__name__)


class SensorCommandSendService(BaseCommandSendService):
    """传感器控制服务类，向传感器发送控制命令"""

    model_class = Sensor
    id_field_name = 'sensor_id'
    type_field_name = 'sensor_type'

    def show_sensor_control_commands(self, sensor: Sensor) -> dict:
        """获取传感器的可用控制命令"""
        return self._get_commands(sensor)


# 全局单例
sensor_command_send_service = SensorCommandSendService()
