"""
命令发送服务基类
提供传感器和设备共用的命令发送、校验码确认等逻辑
子类只需指定 model_class 和 id_field_name 即可复用全部功能
"""
import logging
import random
import threading
import time
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class BaseCommandSendService:
    """
    命令发送服务基类
    子类必须设置:
        model_class: Django 模型类
        id_field_name: 模型中 ID 字段名（如 'sensor_id' 或 'device_id'）
        type_field_name: 模型中类型关联字段名（如 'sensor_type' 或 'device_type'）
    """

    model_class = None
    id_field_name = None
    type_field_name = None

    def __init__(self, mqtt_service=None):
        self.mqtt_service = mqtt_service
        self._pending_check_codes: Dict[str, dict] = {}
        self._check_code_ttl = 120
        self._waiting_events: Dict[str, threading.Event] = {}

    def set_mqtt_service(self, mqtt_service):
        """设置MQTT服务实例"""
        self.mqtt_service = mqtt_service

    def _get_object(self, object_id: str):
        """根据 ID 获取模型实例"""
        return self.model_class.objects.get(**{self.id_field_name: object_id})

    def _get_commands(self, obj) -> Dict:
        """获取对象的可用控制命令"""
        type_obj = getattr(obj, self.type_field_name, None)
        if not type_obj:
            return {}
        return getattr(type_obj, 'commands', None) or {}

    def send_command(self, object_id: str, command_payload: Dict) -> bool:
        """发送命令到设备/传感器"""
        try:
            obj = self._get_object(object_id)
        except self.model_class.DoesNotExist:
            logger.error(f"{self.id_field_name}={object_id} 不存在")
            return False

        if not self.mqtt_service:
            logger.error("MQTT服务未初始化")
            return False

        control_topic = obj.mqtt_topic_control
        if not control_topic:
            logger.error(f"{self.id_field_name}={object_id} 未配置控制主题")
            return False

        try:
            success = self.mqtt_service.publish(control_topic, command_payload, qos=1)
            if success:
                check_code = command_payload.get('check_code')
                if check_code:
                    self._pending_check_codes[check_code] = {
                        self.id_field_name: object_id,
                        'sent_at': time.time(),
                    }
                logger.info(f"命令发送成功 - {self.id_field_name}={object_id} -> {command_payload.get('command', 'unknown')}")
            else:
                logger.error(f"命令发送失败 - {self.id_field_name}={object_id}")
            return success
        except Exception as e:
            logger.error(f"命令发送异常 - {self.id_field_name}={object_id}: {e}", exc_info=True)
            return False

    @staticmethod
    def _apply_params_to_message(msg: dict, params: Dict) -> dict:
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
                result[key] = BaseCommandSendService._apply_params_to_message(value, params)
            else:
                result[key] = value
        return result

    @staticmethod
    def _inject_check_code(msg: dict) -> dict:
        """发送命令时自动注入 6 位随机 check_code"""
        msg = msg.copy()
        msg['check_code'] = str(random.randint(100000, 999999))
        return msg

    def send_custom_command(
        self,
        object_id: str,
        command_name: str,
        params: Optional[Dict] = None
    ) -> bool:
        """根据类型定义发送自定义命令"""
        try:
            obj = self._get_object(object_id)
        except self.model_class.DoesNotExist:
            logger.error(f"{self.id_field_name}={object_id} 不存在")
            return False

        commands = self._get_commands(obj)
        if command_name not in commands:
            type_obj = getattr(obj, self.type_field_name, None)
            type_name = getattr(type_obj, 'name', '未知') if type_obj else '未知'
            logger.error(f"未定义的命令 '{command_name}' 对于类型 '{type_name}'")
            return False

        command_info = commands[command_name]
        mqtt_message = command_info['mqtt_message'].copy()
        if params:
            mqtt_message = self._apply_params_to_message(mqtt_message, params)
        return self.send_command(object_id, mqtt_message)

    def send_custom_command_with_make_sure(
        self,
        object_id: str,
        command_name: str,
        params: Optional[Dict] = None,
        *,
        timeout: int = 3,
    ) -> bool:
        """
        发送命令并等待回传带正确 check_code 的状态，确认命令被执行。

        Args:
            object_id: 设备/传感器 ID
            command_name: 命令名称
            params: 命令参数（可选）
            timeout: 等待秒数，默认 3 秒

        Returns:
            True: 在限制时间内收到正确 check_code
            False: 发送失败或超时未收到
        """
        try:
            obj = self._get_object(object_id)
        except self.model_class.DoesNotExist:
            logger.error(f"{self.id_field_name}={object_id} 不存在")
            return False

        commands = self._get_commands(obj)
        if command_name not in commands:
            type_obj = getattr(obj, self.type_field_name, None)
            type_name = getattr(type_obj, 'name', '未知') if type_obj else '未知'
            logger.error(f"未定义的命令 '{command_name}' 对于类型 '{type_name}'")
            return False

        command_info = commands[command_name]
        mqtt_message = command_info['mqtt_message'].copy()
        if params:
            mqtt_message = self._apply_params_to_message(mqtt_message, params)
        mqtt_message = self._inject_check_code(mqtt_message)
        check_code = mqtt_message.get('check_code')

        if not check_code:
            return self.send_command(object_id, mqtt_message)

        evt = threading.Event()
        self._waiting_events[check_code] = evt

        if not self.send_command(object_id, mqtt_message):
            self._waiting_events.pop(check_code, None)
            return False

        logger.info(f"等待 {self.id_field_name}={object_id} 回传 check_code {check_code}，最多 {timeout} 秒...")
        try:
            signaled = evt.wait(timeout=timeout)
            if signaled:
                logger.info(f"{self.id_field_name}={object_id} 已确认执行命令「{command_name}」")
            else:
                logger.warning(
                    f"等待超时：{timeout} 秒内未收到 {self.id_field_name}={object_id} 的正确回传。"
                    f"请检查：1) 是否已注册对应的 status handler 2) 设备/传感器是否在线"
                )
            return signaled
        finally:
            self._waiting_events.pop(check_code, None)

    def _cleanup_expired_check_codes(self):
        """清理过期的 check_code"""
        now = time.time()
        expired = [k for k, v in self._pending_check_codes.items() if now - v['sent_at'] > self._check_code_ttl]
        for k in expired:
            del self._pending_check_codes[k]

    def verify_check_code(self, object_id: str, check_code: str) -> bool:
        """
        校验回传的 check_code 是否与已发送命令的校验码一致
        返回 True 表示校验通过，False 表示校验失败或超时
        """
        if not check_code:
            return True  # 无 check_code 视为通过（如心跳）
        self._cleanup_expired_check_codes()
        pending = self._pending_check_codes.pop(check_code, None)
        if pending is None:
            logger.warning(f"check_code 校验失败 - {self.id_field_name}={object_id} 回传的校验码 {check_code} 未找到或已过期")
            return False
        if pending[self.id_field_name] != object_id:
            logger.warning(f"check_code 校验失败 - ID 不匹配: 期望 {pending[self.id_field_name]}, 收到 {object_id}")
            return False
        logger.info(f"check_code 校验通过 - {self.id_field_name}={object_id} 已正确执行命令")
        evt = self._waiting_events.pop(check_code, None)
        if evt is not None:
            evt.set()
        return True
