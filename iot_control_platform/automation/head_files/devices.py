"""
自动化脚本可用的 devices 模块
提供 devices.get(device_id) 获取设备包装对象，含：
  .current_state              — 最新 DeviceStatusCollection.data（首次访问时查询，本次循环内缓存）
  .refresh()                  — 从数据库重新读取，刷新缓存
  .send_command(name, params) — 发送控制命令（阻塞等待确认，timeout=3s）
  .is_online                  — 是否在线（3 分钟内有数据上报）
  .model                      — 原始 Device 模型实例
"""
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DeviceWrapper:
    """设备包装对象，每次执行周期构建一次；current_state 首次访问时惰性加载。"""

    def __init__(self, device_id: str, device_model, send_command_fn):
        self.device_id = device_id
        self._device = device_model
        self._send_command_fn = send_command_fn
        self._state_cache: Optional[dict] = None

    @property
    def model(self):
        return self._device

    @property
    def current_state(self) -> dict:
        """最新一条 DeviceStatusCollection.data（本次循环内缓存，调用 refresh() 可强制重读）"""
        if self._state_cache is None:
            self.refresh()
        return self._state_cache

    def refresh(self) -> dict:
        """从数据库重新读取最新状态，刷新缓存并返回"""
        if self._device:
            latest = self._device.status_records.order_by('-timestamp').first()
            self._state_cache = latest.data if latest and latest.data else {}
        else:
            self._state_cache = {}
        return self._state_cache

    def send_command(self, name: str, params: Optional[Dict] = None) -> Any:
        """发送控制命令并等待确认（最多 3 秒）"""
        return self._send_command_fn(name, params)

    @property
    def is_online(self) -> bool:
        """是否在线：3 分钟内有数据上报"""
        if not self._device or not self._device.last_seen:
            return False
        from django.utils import timezone
        from datetime import timedelta
        return (timezone.now() - self._device.last_seen) < timedelta(minutes=3)


def _make_noop_send(device_id: str):
    """为未找到的设备返回空操作 send_command"""
    def _noop(name=None, params=None):
        logger.warning("自动化规则：设备 %s 不存在，忽略命令 %s", device_id, name)
        return False
    return _noop


def build_devices(device_list: List[Dict]) -> Any:
    """
    根据 device_list 构建 devices 对象，供脚本通过 devices.get(device_id) 使用。
    """
    from devices.models import Device
    from services.devices_service.device_command_send_service import device_command_send_service

    registry: Dict[str, DeviceWrapper] = {}

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
                def _send_cmd(name: str, params: Optional[Dict] = None):
                    return device_command_send_service.send_custom_command_with_make_sure(
                        object_id=did,
                        command_name=name,
                        params=params or {},
                        timeout=3,
                    )
                return _send_cmd

            registry[device_id] = DeviceWrapper(device_id, dev, _make_send_cmd(device_id))
        except Device.DoesNotExist:
            logger.warning("自动化规则：未找到设备 %s", device_id)
            registry[device_id] = DeviceWrapper(device_id, None, _make_noop_send(device_id))

    return _make_devices_proxy(registry)


def _make_devices_proxy(registry: Dict[str, DeviceWrapper]) -> Any:
    """构造具有 get(device_id) 方法的 devices 代理对象"""
    def get(_self, device_id: str) -> Optional[DeviceWrapper]:
        return registry.get(device_id)

    return type('Devices', (), {'get': get})()
