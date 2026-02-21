"""
Sensors模块测试
测试传感器模型和相关功能
"""
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from sensors.models import SensorType, Sensor, SensorData


class SensorTypeTest(TestCase):
    """传感器类型模型测试"""
    
    def test_create_sensor_type(self):
        """测试创建传感器类型"""
        sensor_type = SensorType.objects.create(
            name="DHT11温湿度传感器",
            description="温湿度传感器",
            default_variables_schema={
                'temperature': {
                    'type': 'float',
                    'unit': '°C',
                    'range': [-40, 125],
                    'readonly': True
                },
                'humidity': {
                    'type': 'float',
                    'unit': '%',
                    'range': [0, 100],
                    'readonly': True
                }
            },
            icon="thermometer"
        )
        
        self.assertEqual(sensor_type.name, "DHT11温湿度传感器")
        self.assertIn('temperature', sensor_type.default_variables_schema)
        self.assertIn('humidity', sensor_type.default_variables_schema)
    
    def test_sensor_type_str(self):
        """测试字符串表示"""
        sensor_type = SensorType.objects.create(name="测试传感器")
        self.assertEqual(str(sensor_type), "测试传感器")


class SensorModelTest(TestCase):
    """传感器模型测试"""
    
    def setUp(self):
        """创建测试数据"""
        self.sensor_type = SensorType.objects.create(
            name="DHT11",
            default_variables_schema={
                'temperature': {
                    'type': 'float',
                    'unit': '°C',
                    'readonly': True
                },
                'humidity': {
                    'type': 'float',
                    'unit': '%',
                    'readonly': True
                }
            }
        )
    
    def test_create_sensor(self):
        """测试创建传感器"""
        sensor = Sensor.objects.create(
            sensor_id="DHT11-001",
            name="客厅温湿度传感器",
            sensor_type=self.sensor_type,
            location="客厅",
            data_pin="D5",
            sampling_interval=60
        )
        
        self.assertEqual(sensor.sensor_id, "DHT11-001")
        self.assertEqual(sensor.name, "客厅温湿度传感器")
        self.assertFalse(sensor.is_online)
        self.assertTrue(sensor.is_enabled)
    
    def test_auto_generate_mqtt_topics(self):
        """测试自动生成MQTT主题"""
        sensor = Sensor.objects.create(
            sensor_id="DHT11-001",
            name="测试传感器",
            sensor_type=self.sensor_type
        )
        
        self.assertEqual(sensor.mqtt_topic_data, "iot/sensors/DHT11-001/data")
        self.assertEqual(sensor.mqtt_topic_control, "iot/sensors/DHT11-001/control")
    
    def test_inherit_variables_schema_from_type(self):
        """测试从类型继承变量定义"""
        sensor = Sensor.objects.create(
            sensor_id="DHT11-001",
            name="测试传感器",
            sensor_type=self.sensor_type
        )
        
        self.assertEqual(sensor.variables_schema, self.sensor_type.default_variables_schema)
        self.assertIn('temperature', sensor.variables_schema)
        self.assertIn('humidity', sensor.variables_schema)
    
    def test_update_latest_data(self):
        """测试更新最新数据"""
        sensor = Sensor.objects.create(
            sensor_id="DHT11-001",
            name="测试传感器",
            sensor_type=self.sensor_type
        )
        
        data = {'temperature': 25.5, 'humidity': 60.0}
        sensor.update_latest_data(data)
        
        sensor.refresh_from_db()
        self.assertEqual(sensor.current_state, data)
        self.assertTrue(sensor.is_online)
        self.assertIsNotNone(sensor.last_seen)
    
    def test_check_online_status_online(self):
        """测试在线状态检查（在线）"""
        sensor = Sensor.objects.create(
            sensor_id="DHT11-001",
            name="测试传感器",
            sensor_type=self.sensor_type,
            sampling_interval=60
        )
        
        # 设置最近上报时间
        sensor.last_seen = timezone.now() - timedelta(seconds=30)
        sensor.is_online = True
        sensor.save()
        
        self.assertTrue(sensor.check_online_status())
    
    def test_check_online_status_offline(self):
        """测试在线状态检查（离线）"""
        sensor = Sensor.objects.create(
            sensor_id="DHT11-001",
            name="测试传感器",
            sensor_type=self.sensor_type,
            sampling_interval=60
        )
        
        # 设置很久之前的上报时间
        sensor.last_seen = timezone.now() - timedelta(seconds=200)
        sensor.is_online = True
        sensor.save()
        
        self.assertFalse(sensor.check_online_status())
        sensor.refresh_from_db()
        self.assertFalse(sensor.is_online)
    
    def test_get_offline_duration(self):
        """测试获取离线时长"""
        sensor = Sensor.objects.create(
            sensor_id="DHT11-001",
            name="测试传感器",
            sensor_type=self.sensor_type
        )
        
        sensor.last_seen = timezone.now() - timedelta(seconds=300)
        sensor.is_online = False
        sensor.save()
        
        duration = sensor.get_offline_duration()
        self.assertGreater(duration, 290)
        self.assertLess(duration, 310)
    
    def test_get_data_count(self):
        """测试获取数据记录数"""
        sensor = Sensor.objects.create(
            sensor_id="DHT11-001",
            name="测试传感器",
            sensor_type=self.sensor_type
        )
        
        # 创建一些数据记录
        now = timezone.now()
        for i in range(5):
            SensorData.objects.create(
                sensor=sensor,
                data={'temperature': 25.0 + i},
                timestamp=now - timedelta(hours=i)
            )
        
        count = sensor.get_data_count(hours=24)
        self.assertEqual(count, 5)
    
    def test_sensor_str(self):
        """测试字符串表示"""
        sensor = Sensor.objects.create(
            sensor_id="DHT11-001",
            name="客厅传感器",
            sensor_type=self.sensor_type
        )
        
        self.assertEqual(str(sensor), "客厅传感器 (DHT11-001)")


class SensorDataTest(TestCase):
    """传感器数据模型测试"""
    
    def setUp(self):
        """创建测试传感器"""
        sensor_type = SensorType.objects.create(
            name="DHT11",
            default_variables_schema={
                'temperature': {'type': 'float'},
                'humidity': {'type': 'float'}
            }
        )
        
        self.sensor = Sensor.objects.create(
            sensor_id="DHT11-001",
            name="测试传感器",
            sensor_type=sensor_type
        )
    
    def test_create_sensor_data(self):
        """测试创建传感器数据"""
        data = SensorData.objects.create(
            sensor=self.sensor,
            data={'temperature': 25.5, 'humidity': 60.0},
            timestamp=timezone.now()
        )
        
        self.assertEqual(data.temperature, 25.5)
        self.assertEqual(data.humidity, 60.0)
        self.assertTrue(data.is_valid)
        self.assertEqual(data.quality_score, 100)
    
    def test_auto_extract_common_fields(self):
        """测试自动提取常用字段"""
        data = SensorData.objects.create(
            sensor=self.sensor,
            data={
                'temperature': 26.5,
                'humidity': 65.0,
                'pressure': 1013.25
            },
            timestamp=timezone.now()
        )
        
        self.assertEqual(data.temperature, 26.5)
        self.assertEqual(data.humidity, 65.0)
        self.assertEqual(data.pressure, 1013.25)
    
    def test_update_sensor_latest_data_on_save(self):
        """测试保存时更新传感器最新数据"""
        data_dict = {'temperature': 27.0, 'humidity': 70.0}
        
        SensorData.objects.create(
            sensor=self.sensor,
            data=data_dict,
            timestamp=timezone.now()
        )
        
        self.sensor.refresh_from_db()
        self.assertEqual(self.sensor.current_state, data_dict)
    
    def test_get_statistics(self):
        """测试获取统计数据"""
        now = timezone.now()
        
        # 创建测试数据
        for i in range(10):
            SensorData.objects.create(
                sensor=self.sensor,
                data={'temperature': 20.0 + i, 'humidity': 50.0 + i},
                timestamp=now - timedelta(hours=i)
            )
        
        stats = SensorData.get_statistics(
            self.sensor,
            start_time=now - timedelta(hours=24),
            end_time=now
        )
        
        self.assertEqual(stats['count'], 10)
        self.assertIsNotNone(stats['avg_temperature'])
        self.assertIsNotNone(stats['max_temperature'])
        self.assertIsNotNone(stats['min_temperature'])
