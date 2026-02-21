"""
automation.head_files - 脚本可用的 sensors/devices 模块
Arduino 风格：sensors.get(device_id)、devices.get(device_id)
"""
from .sensors import build_sensors
from .devices import build_devices

__all__ = ['build_sensors', 'build_devices']
