from engine import sensors, devices

class RotationSensorControlSG90:
    """旋转传感器控制SG90舵机"""

    SENSOR_ID = 'Rotation-001'
    DEVICE_ID = 'sg90_001'

    def __init__(self):
        self.sensor = sensors.get(self.SENSOR_ID)
        self.device = devices.get(self.DEVICE_ID)
        print(f"System Initialized: Sensor={bool(self.sensor)}, Device={bool(self.device)}")

    def loop(self) -> bool:
        print("start")
        if not self.sensor or not self.device:
            return False
        angle = self.sensor.current_state.get('angle')
        print(f"angle: {angle}")
        if angle >= 0 or angle <= 180:
            self.device.send_command('set_angle', {'val': angle})
            return True

        return False