# Python 脚本，Arduino 风格：setup() / loop()
# sensors、devices 由引擎注入，无需 import

from engine import sensors, devices
from typing import Optional
import time

class HumidityAlert:
    """湿度告警控制器：湿度 > 70% 时向 SG_80_001 发送 high 命令"""

    SENSOR_ID = 'DHT11-WEMOS-001'
    DEVICE_ID = 'SG_80_001'
    HUMIDITY_THRESHOLD = 70.0

    def __init__(self):
        """相当于 Arduino 的 setup()"""
        self.sensor = sensors.get(self.SENSOR_ID)
        self.device = devices.get(self.DEVICE_ID)
        print(f"System Initialized: Sensor={bool(self.sensor)}, Device={bool(self.device)}")

    def _get_humidity(self) -> Optional[float]:
        """辅助方法：安全地获取当前湿度"""
        if not self.sensor:
            return None
        state = self.sensor.current_state or {}
        humidity = state.get('humidity')
        if humidity is None:
            return None
        try:
            return float(humidity)
        except (TypeError, ValueError):
            return None

    def loop(self) -> bool:
        """相当于 Arduino 的 loop()"""
        humidity = self._get_humidity()
        # 库导入测试
        time.sleep(1)
        print("已经停了1秒了")
        if humidity is None or not self.device:
            return False
        if humidity > self.HUMIDITY_THRESHOLD:
            self.device.send_command('high', {})
            return True
        if humidity <= self.HUMIDITY_THRESHOLD:
            self.device.send_command('low', {})
            return True
        return False
