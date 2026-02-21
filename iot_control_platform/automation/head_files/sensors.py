"""
自动化脚本可用的 sensors 模块
提供 sensors.get(device_id) 获取传感器包装对象，含 current_state（最新 SensorData.data）
脚本设计风格参考 Arduino：setup/loop，通过 sensors.get() 获取传感器
"""
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _get_sensor_current_state(sensor) -> dict:
    """获取传感器最新数据（来自 SensorData.data）"""
    if not sensor:
        return {}
    latest = sensor.data_records.order_by('-timestamp').first()
    return latest.data if latest and latest.data else {}


def build_sensors(device_list: List[Dict]) -> Any:
    """
    根据 device_list 构建 sensors 对象，供脚本通过 sensors.get(device_id) 使用。

    Args:
        device_list: 设备列表，格式 [{"device_id": "xxx", "device_type": "Sensor", ...}, ...]

    Returns:
        具有 get(device_id) 方法的对象，get 返回的包装对象含：
        - device_id
        - current_state: 最新 SensorData.data
        - model: Sensor 模型实例（不存在时为 None）
    """
    from sensors.models import Sensor

    registry: Dict[str, Any] = {}

    if not isinstance(device_list, list):
        return _make_sensors_proxy(registry)

    for item in device_list:
        if not isinstance(item, dict):
            continue
        device_id = item.get('device_id')
        device_type_str = (item.get('device_type') or '').strip()
        if not device_id or device_type_str.lower() != 'sensor':
            continue

        try:
            sensor = Sensor.objects.get(sensor_id=device_id)
            state = _get_sensor_current_state(sensor)
            registry[device_id] = type('SensorWrapper', (), {
                'device_id': device_id,
                'current_state': state,
                'model': sensor,
            })()
        except Sensor.DoesNotExist:
            logger.warning("自动化规则：未找到传感器 %s", device_id)
            registry[device_id] = type('SensorWrapper', (), {
                'device_id': device_id,
                'current_state': {},
                'model': None,
            })()

    return _make_sensors_proxy(registry)


def _make_sensors_proxy(registry: Dict[str, Any]) -> Any:
    """构造具有 get(device_id) 方法的 sensors 代理对象"""
    def get(_self, device_id: str) -> Optional[Any]:
        return registry.get(device_id)

    return type('Sensors', (), {'get': get})()
