"""
设备控制服务模块
基于 BaseCommandSendService，提供设备级命令发送与校验码确认
"""
import logging

from devices.models import Device
from services.base_command_send_service import BaseCommandSendService

logger = logging.getLogger(__name__)


class DeviceCommandSendService(BaseCommandSendService):
    """设备控制服务类，向执行器设备发送控制命令"""

    model_class = Device
    id_field_name = 'device_id'
    type_field_name = 'device_type'

    def show_device_control_commands(self, device: Device) -> dict:
        """获取设备的可用控制命令（来自 DeviceType.commands）"""
        return self._get_commands(device)


# 全局单例
device_command_send_service = DeviceCommandSendService()
