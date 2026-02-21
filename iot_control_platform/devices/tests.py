"""
Devices模块测试
测试设备模型和相关功能
参考 sensors 结构
"""
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from devices.models import DeviceType, Device, DeviceData


class DeviceTypeTest(TestCase):
    """设备类型模型测试"""

    def test_create_device_type(self):
        """测试创建设备类型"""
        device_type = DeviceType.objects.create(
            DeviceType_id="LED-01",
            name="LED灯",
            description="智能LED灯",
            state_fields=['power_state', 'brightness'],
            config_parameters=['heartbeat_interval']
        )

        self.assertEqual(device_type.name, "LED灯")
        self.assertIn('power_state', device_type.state_fields)

    def test_device_type_str(self):
        """测试字符串表示"""
        device_type = DeviceType.objects.create(
            DeviceType_id="TEST-01",
            name="测试设备"
        )
        self.assertEqual(str(device_type), "测试设备")


class DeviceModelTest(TestCase):
    """设备模型测试"""

    def setUp(self):
        """创建测试数据"""
        self.device_type = DeviceType.objects.create(
            DeviceType_id="LED-01",
            name="智能灯",
            state_fields=['power_state', 'brightness'],
            config_parameters=['heartbeat_interval']
        )

    def test_create_device(self):
        """测试创建设备"""
        device = Device.objects.create(
            device_id="LED-001",
            name="客厅灯",
            device_type=self.device_type,
            location="客厅"
        )

        self.assertEqual(device.device_id, "LED-001")
        self.assertEqual(device.name, "客厅灯")
        self.assertFalse(device.is_online)

    def test_auto_generate_mqtt_topics(self):
        """测试自动生成MQTT主题"""
        device = Device.objects.create(
            device_id="LED-001",
            name="测试灯",
            device_type=self.device_type
        )

        self.assertEqual(device.mqtt_topic_data, "iot/devices/LED-001/status")
        self.assertEqual(device.mqtt_topic_control, "iot/devices/LED-001/control")

    def test_check_online_status_online(self):
        """测试在线状态检查（在线）"""
        device = Device.objects.create(
            device_id="LED-001",
            name="测试灯",
            device_type=self.device_type
        )

        device.last_seen = timezone.now() - timedelta(seconds=60)
        device.is_online = True
        device.save()

        self.assertTrue(device.check_online_status())

    def test_check_online_status_offline(self):
        """测试在线状态检查（离线）"""
        device = Device.objects.create(
            device_id="LED-001",
            name="测试灯",
            device_type=self.device_type
        )

        device.last_seen = timezone.now() - timedelta(seconds=400)
        device.is_online = True
        device.save()

        self.assertFalse(device.check_online_status())
        device.refresh_from_db()
        self.assertFalse(device.is_online)

    def test_update_heartbeat(self):
        """测试更新心跳"""
        device = Device.objects.create(
            device_id="LED-001",
            name="测试灯",
            device_type=self.device_type,
            is_online=False
        )

        device.update_heartbeat()

        device.refresh_from_db()
        self.assertTrue(device.is_online)
        self.assertIsNotNone(device.last_seen)

    def test_device_str(self):
        """测试字符串表示"""
        device = Device.objects.create(
            device_id="LED-001",
            name="客厅灯",
            device_type=self.device_type
        )

        self.assertEqual(str(device), "客厅灯 (LED-001)")


class DeviceDataTest(TestCase):
    """设备数据记录测试"""

    def setUp(self):
        """创建测试设备"""
        device_type = DeviceType.objects.create(
            DeviceType_id="LED-01",
            name="智能灯"
        )
        self.device = Device.objects.create(
            device_id="LED-001",
            name="测试灯",
            device_type=device_type
        )

    def test_create_device_data(self):
        """测试创建设备数据"""
        data = DeviceData.objects.create(
            device=self.device,
            data={'power_state': True, 'brightness': 80},
            timestamp=timezone.now()
        )

        self.assertEqual(data.device, self.device)
        self.assertEqual(data.data['power_state'], True)
        self.assertEqual(data.data['brightness'], 80)
