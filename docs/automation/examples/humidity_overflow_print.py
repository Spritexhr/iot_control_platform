# Python 脚本，Arduino 风格：setup() / loop()
# sensors、devices 由引擎注入，无需 import

from engine import sensors, devices
from typing import Optional


class HumidityOverflowPrint:
    """湿度超 80% 打印控制器"""

    SENSOR_ID = 'DHT11-WEMOS-001'
    HUMIDITY_THRESHOLD = 80.0

    def __init__(self):
        """相当于 Arduino 的 setup()"""
        self.sensor = sensors.get(self.SENSOR_ID)
        print(f"System Initialized: Sensor={bool(self.sensor)}")

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
        if humidity is None:
            return False
        if humidity > self.HUMIDITY_THRESHOLD:
            msg = "[湿度超 80%%] 传感器 %s 当前湿度: %s%%"
            print(msg % (self.SENSOR_ID, humidity))
            return True
        return False
