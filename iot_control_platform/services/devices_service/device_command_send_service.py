"""
设备控制服务模块
- send_command / send_custom_command: 发送命令，不包含校验码
- send_custom_command_with_make_sure: 发送带校验码的命令，等待设备回传确认（依赖 MQTT 注册 device status handler）
"""
import logging
import random
import threading
import time
from typing import Dict, Optional
from devices.models import Device

logger = logging.getLogger(__name__)

# send_custom_command_with_make_sure 专用：已发送的 check_code 缓存
_PENDING_CHECK_CODES: Dict[str, dict] = {}
_CHECK_CODE_TTL = 120
_WAITING_EVENTS: Dict[str, threading.Event] = {}


class DeviceCommandSendService:
    """设备控制服务类，向执行器设备发送控制命令"""

    def __init__(self, mqtt_service=None):
        self.mqtt_service = mqtt_service

    def set_mqtt_service(self, mqtt_service):
        """设置MQTT服务实例"""
        self.mqtt_service = mqtt_service

    def send_command(self, device_id: str, command_payload: Dict) -> bool:
        """发送命令到设备"""
        try:
            device = Device.objects.get(device_id=device_id)
        except Device.DoesNotExist:
            logger.error(f"✗ 设备不存在: {device_id}")
            return False

        if not self.mqtt_service:
            logger.error("✗ MQTT服务未初始化")
            return False

        if not device.mqtt_topic_control:
            logger.error(f"✗ 设备未配置控制主题: {device_id}")
            return False

        try:
            topic = device.mqtt_topic_control
            success = self.mqtt_service.publish(topic, command_payload, qos=1)
            if success:
                # 仅当 payload 含 check_code 时记录（用于 send_custom_command_with_make_sure）
                check_code = command_payload.get('check_code')
                if check_code:
                    _PENDING_CHECK_CODES[check_code] = {
                        'device_id': device_id,
                        'sent_at': time.time(),
                    }
                logger.info(f"✓ 命令发送成功 - {device_id} -> {command_payload.get('command', 'unknown')}")
            else:
                logger.error(f"✗ 命令发送失败 - {device_id}")
            return success
        except Exception as e:
            logger.error(f"✗ 命令发送异常 - {device_id}: {e}", exc_info=True)
            return False

    def show_device_control_commands(self, device: Device) -> Dict:
        """获取设备的可用控制命令（来自 DeviceType.commands）"""
        if not device or not device.device_type:
            return {}
        return device.device_type.commands or {}

    def _apply_params_to_message(self, msg: dict, params: Dict) -> dict:
        """将 mqtt_message 中的占位符 {param_name} 替换为 params 中的实际值"""
        result = {}
        for key, value in msg.items():
            if isinstance(value, str):
                replaced = value
                for param_name, param_value in params.items():
                    placeholder = "{" + param_name + "}"
                    if placeholder in replaced:
                        if replaced == placeholder:
                            replaced = param_value
                            break
                        else:
                            replaced = replaced.replace(placeholder, str(param_value))
                result[key] = replaced
            elif isinstance(value, dict):
                result[key] = self._apply_params_to_message(value, params)
            else:
                result[key] = value
        return result

    def _inject_check_code(self, msg: dict) -> dict:
        """发送命令时自动注入 6 位随机 check_code，无需在 mqtt_message 中预先配置"""
        msg = msg.copy()
        msg['check_code'] = str(random.randint(100000, 999999))
        return msg

    def send_custom_command(
        self,
        device_id: str,
        command_name: str,
        params: Optional[Dict] = None
    ) -> bool:
        """根据 DeviceType 定义发送自定义命令"""
        try:
            device = Device.objects.get(device_id=device_id)
        except Device.DoesNotExist:
            logger.error(f"✗ 设备不存在: {device_id}")
            return False

        commands = self.show_device_control_commands(device)
        if command_name not in commands:
            logger.error(f"✗ 未定义的命令 '{command_name}' 对于设备类型 '{device.device_type.name}'")
            return False

        command_info = commands[command_name]
        mqtt_message = command_info['mqtt_message'].copy()
        if params:
            mqtt_message = self._apply_params_to_message(mqtt_message, params)
        return self.send_command(device.device_id, mqtt_message)

    def send_custom_command_with_make_sure(
        self,
        device_id: str,
        command_name: str,
        params: Optional[Dict] = None,
        *,
        time: int = 3,
    ) -> bool:
        """
        发送命令并等待设备回传带正确 check_code 的状态，确认命令被执行。
        需确保 MQTT 已注册 device status handler（mqtt_service.setup_device_status_handler）。

        Args:
            device_id: 设备 ID
            command_name: 命令名称
            params: 命令参数（可选）
            time: 等待秒数，默认 3 秒

        Returns:
            True: 在限制时间内收到正确 check_code
            False: 发送失败或超时未收到
        """
        try:
            device = Device.objects.get(device_id=device_id)
        except Device.DoesNotExist:
            logger.error(f"✗ 设备不存在: {device_id}")
            return False

        commands = self.show_device_control_commands(device)
        if command_name not in commands:
            logger.error(f"✗ 未定义的命令 '{command_name}' 对于设备类型 '{device.device_type.name}'")
            return False

        command_info = commands[command_name]
        mqtt_message = command_info['mqtt_message'].copy()
        if params:
            mqtt_message = self._apply_params_to_message(mqtt_message, params)
        mqtt_message = self._inject_check_code(mqtt_message)
        check_code = mqtt_message.get('check_code')

        if not check_code:
            return self.send_command(device.device_id, mqtt_message)

        evt = threading.Event()
        _WAITING_EVENTS[check_code] = evt

        if not self.send_command(device.device_id, mqtt_message):
            _WAITING_EVENTS.pop(check_code, None)
            return False

        logger.info(f"⏳ 等待设备 {device_id} 回传 check_code {check_code}，最多 {time} 秒...")
        try:
            signaled = evt.wait(timeout=time)
            if signaled:
                logger.info(f"✓ 设备 {device_id} 已确认执行命令「{command_name}」")
            else:
                logger.warning(
                    f"✗ 等待超时：{time} 秒内未收到设备 {device_id} 的正确回传。"
                    f"请检查：1) 是否已调用 mqtt_service.setup_device_status_handler() 2) 设备是否在线"
                )
            return signaled
        finally:
            _WAITING_EVENTS.pop(check_code, None)


def _cleanup_expired_check_codes():
    """清理过期的 check_code"""
    now = time.time()
    expired = [k for k, v in _PENDING_CHECK_CODES.items() if now - v['sent_at'] > _CHECK_CODE_TTL]
    for k in expired:
        del _PENDING_CHECK_CODES[k]


def _verify_device_status_check_code(device_id: str, check_code: str) -> bool:
    """
    校验设备回传的 check_code 是否与已发送命令的校验码一致
    返回 True 表示校验通过，False 表示校验失败或超时
    """
    if not check_code:
        return True  # 无 check_code 视为通过（如心跳）
    _cleanup_expired_check_codes()
    pending = _PENDING_CHECK_CODES.pop(check_code, None)
    if pending is None:
        logger.warning(f"⚠ check_code 校验失败 - 设备 {device_id} 回传的校验码 {check_code} 未找到或已过期")
        return False
    if pending['device_id'] != device_id:
        logger.warning(f"⚠ check_code 校验失败 - 设备 ID 不匹配: 期望 {pending['device_id']}, 收到 {device_id}")
        return False
    logger.info(f"✓ check_code 校验通过 - 设备 {device_id} 已正确执行命令")
    evt = _WAITING_EVENTS.pop(check_code, None)
    if evt is not None:
        evt.set()
    return True


def verify_device_status_check_code(device_id: str, check_code: str) -> bool:
    """供 device_upload_status_handlers 调用，校验回传的 check_code"""
    return _verify_device_status_check_code(device_id, check_code)


# 全局单例
device_command_send_service = DeviceCommandSendService()
