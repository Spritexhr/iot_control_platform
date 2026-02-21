"""
自动化脚本可用的 devices 模块
提供 devices.get(device_id) 获取设备包装对象，含 current_state 与 send_command(name, params)
脚本设计风格参考 Arduino：setup/loop，通过 devices.get() 获取设备并发送命令
"""
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _get_device_current_state(device) -> dict:
    """获取设备最新状态（来自 DeviceData.data）"""
    if not device:
        return {}
    latest = device.data_records.order_by('-timestamp').first()
    return latest.data if latest and latest.data else {}


def build_devices(device_list: List[Dict]) -> Any:
    """
    根据 device_list 构建 devices 对象，供脚本通过 devices.get(device_id) 使用。

    Args:
        device_list: 设备列表，格式 [{"device_id": "xxx", "device_type": "Device", ...}, ...]

    Returns:
        具有 get(device_id) 方法的对象，get 返回的包装对象含：
        - device_id
        - current_state: 最新 DeviceData.data
        - send_command(name, params): 发送控制命令
        - model: Device 模型实例（不存在时为 None）
    """
    from devices.models import Device
    from services.devices_service.device_command_send_service import device_command_send_service

    registry: Dict[str, Any] = {}

    if not isinstance(device_list, list):
        return _make_devices_proxy(registry)

    for item in device_list:
        if not isinstance(item, dict):
            continue
        device_id = item.get('device_id')
        device_type_str = (item.get('device_type') or '').strip()
        if not device_id or device_type_str.lower() != 'device':
            continue

        try:
            dev = Device.objects.get(device_id=device_id)

            def _make_send_cmd(did: str):
                def _send_cmd(_self, name: str, params: Optional[Dict] = None):
                    return device_command_send_service.send_custom_command_with_make_sure(
                        device_id=did,
                        command_name=name,
                        params=params or {},
                        time=3,
                    )
                return _send_cmd

            state = _get_device_current_state(dev)
            registry[device_id] = type('DeviceWrapper', (), {
                'device_id': device_id,
                'current_state': state,
                'send_command': _make_send_cmd(device_id),
                'model': dev,
            })()
        except Device.DoesNotExist:
            logger.warning("自动化规则：未找到设备 %s", device_id)
            registry[device_id] = type('DeviceWrapper', (), {
                'device_id': device_id,
                'current_state': {},
                'send_command': lambda _self, n=None, p=None: False,
                'model': None,
            })()

    return _make_devices_proxy(registry)


def _make_devices_proxy(registry: Dict[str, Any]) -> Any:
    """构造具有 get(device_id) 方法的 devices 代理对象"""
    def get(_self, device_id: str) -> Optional[Any]:
        return registry.get(device_id)

    return type('Devices', (), {'get': get})()
