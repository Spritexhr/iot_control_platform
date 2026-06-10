from engine import sensors, devices
from typing import Optional


class HumidityAlert:
    """湿度告警控制器：湿度 > 70% 时向 SG_80_001 发送 high 命令"""

    SENSOR_ID = 'DHT11-WEMOS-001'
    DEVICE_ID = 'SG_80_001'
    HUMIDITY_THRESHOLD = 70.0

    def loop(self) -> bool:
        sensor = sensors.get(self.SENSOR_ID)
        device = devices.get(self.DEVICE_ID)
        if not sensor or not device:
            return False

        state = sensor.current_state or {}
        humidity = state.get('humidity')
        if humidity is None:
            return False

        try:
            humidity = float(humidity)
        except (TypeError, ValueError):
            return False

        if humidity > self.HUMIDITY_THRESHOLD:
            device.send_command('high', {})
            return True
        else:
            device.send_command('low', {})
            return True
