from engine import sensors, devices


class RotationSensorControlSG90:
    """旋转传感器控制 SG90 舵机"""

    SENSOR_ID = 'Rotation-001'
    DEVICE_ID = 'sg90_001'

    def loop(self) -> bool:
        sensor = sensors.get(self.SENSOR_ID)
        device = devices.get(self.DEVICE_ID)
        if not sensor or not device:
            return False

        angle = sensor.current_state.get('angle')
        if angle is None:
            return False

        if 0 <= angle <= 180:
            device.send_command('set_angle', {'val': angle})
            return True

        return False
