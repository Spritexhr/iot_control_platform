"""
全局 API 视图（不属于特定 app 的接口）
"""
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta

from config.platform_config import get_config


@api_view(['GET'])
def mqtt_status(request):
    """获取 MQTT 连接状态（从 platform_config 读取当前配置）"""
    try:
        from services.mqtt_service import mqtt_service
        is_connected = mqtt_service.is_connected
    except Exception:
        is_connected = False

    return Response({
        'broker': get_config("mqtt_broker", "127.0.0.1", str),
        'port': get_config("mqtt_port", 1883, int),
        'is_connected': is_connected,
    })


@api_view(['GET'])
def dashboard_stats(request):
    """仪表盘统计数据"""
    from sensors.models import Sensor, SensorData
    from devices.models import Device, DeviceData
    from automation.models import AutomationRule

    now = timezone.now()
    online_threshold = now - timedelta(minutes=3)
    last_24h = now - timedelta(hours=24)

    # 传感器统计
    sensor_total = Sensor.objects.count()
    sensor_online = Sensor.objects.filter(last_seen__gte=online_threshold).count()

    # 设备统计
    device_total = Device.objects.count()
    device_online = Device.objects.filter(last_seen__gte=online_threshold).count()

    # 自动化规则统计
    rule_total = AutomationRule.objects.count()

    # 24小时数据量
    sensor_data_24h = SensorData.objects.filter(timestamp__gte=last_24h).count()
    device_data_24h = DeviceData.objects.filter(timestamp__gte=last_24h).count()

    # 最近传感器数据（每个传感器最新一条）
    recent_sensors = []
    for s in Sensor.objects.select_related('sensor_type').all()[:20]:
        latest = s.data_records.order_by('-timestamp').first()
        is_online = s.last_seen and (now - s.last_seen) < timedelta(minutes=3)
        recent_sensors.append({
            'sensor_id': s.sensor_id,
            'name': s.name,
            'type_name': s.sensor_type.name if s.sensor_type else '--',
            'is_online': is_online,
            'last_seen': s.last_seen,
            'latest_data': latest.data if latest else None,
            'latest_time': latest.timestamp if latest else None,
        })

    # 最近设备状态
    recent_devices = []
    for d in Device.objects.select_related('device_type').all()[:20]:
        latest = d.data_records.order_by('-timestamp').first()
        is_online = d.last_seen and (now - d.last_seen) < timedelta(minutes=3)
        recent_devices.append({
            'device_id': d.device_id,
            'name': d.name,
            'type_name': d.device_type.name if d.device_type else '--',
            'is_online': is_online,
            'last_seen': d.last_seen,
            'latest_data': latest.data if latest else None,
            'latest_time': latest.timestamp if latest else None,
        })

    # 自动化规则列表
    recent_rules = list(
        AutomationRule.objects.values('id', 'name', 'script_id', 'updated_at')
        .order_by('-updated_at')[:10]
    )

    return Response({
        'sensor_total': sensor_total,
        'sensor_online': sensor_online,
        'device_total': device_total,
        'device_online': device_online,
        'rule_total': rule_total,
        'sensor_data_24h': sensor_data_24h,
        'device_data_24h': device_data_24h,
        'recent_sensors': recent_sensors,
        'recent_devices': recent_devices,
        'recent_rules': recent_rules,
    })
