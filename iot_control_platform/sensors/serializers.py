from rest_framework import serializers
from .models import SensorType, Sensor, SensorData, SensorStatusCollection


class SensorTypeSerializer(serializers.ModelSerializer):
    """传感器类型序列化器"""
    sensor_count = serializers.SerializerMethodField()

    class Meta:
        model = SensorType
        fields = [
            'id', 'SensorType_id', 'name', 'description',
            'data_fields', 'config_parameters', 'commands',
            'created_at', 'sensor_count',
        ]
        read_only_fields = ['id', 'created_at', 'sensor_count']

    def get_sensor_count(self, obj):
        return obj.sensors.count()


class SensorTypeBriefSerializer(serializers.ModelSerializer):
    """传感器类型简要序列化器（用于嵌套）"""
    class Meta:
        model = SensorType
        fields = ['id', 'SensorType_id', 'name', 'data_fields', 'config_parameters', 'commands']


class SensorListSerializer(serializers.ModelSerializer):
    """传感器列表序列化器（含类型信息和最新数据）"""
    sensor_type_info = SensorTypeBriefSerializer(source='sensor_type', read_only=True)
    latest_data = serializers.SerializerMethodField()
    is_online = serializers.SerializerMethodField()

    class Meta:
        model = Sensor
        fields = [
            'id', 'sensor_id', 'name', 'description', 'location',
            'mqtt_topic_data', 'mqtt_topic_control',
            'is_online', 'last_seen',
            'created_at', 'updated_at',
            'sensor_type', 'sensor_type_info', 'latest_data',
        ]

    def get_is_online(self, obj):
        """根据 last_seen 实时计算在线状态：3分钟内有数据视为在线"""
        if not obj.last_seen:
            return False
        from django.utils import timezone
        from datetime import timedelta
        timeout = timedelta(minutes=3)
        return (timezone.now() - obj.last_seen) < timeout

    def get_latest_data(self, obj):
        record = obj.data_records.order_by('-timestamp').first()
        if record:
            return {
                'data': record.data,
                'timestamp': record.timestamp,
            }
        return None


class SensorDetailSerializer(SensorListSerializer):
    """传感器详情序列化器"""
    data_count_24h = serializers.SerializerMethodField()

    class Meta(SensorListSerializer.Meta):
        fields = SensorListSerializer.Meta.fields + ['data_count_24h']

    def get_data_count_24h(self, obj):
        from django.utils import timezone
        from datetime import timedelta
        start = timezone.now() - timedelta(hours=24)
        return obj.data_records.filter(timestamp__gte=start).count()


class SensorCreateUpdateSerializer(serializers.ModelSerializer):
    """传感器创建/更新序列化器"""
    class Meta:
        model = Sensor
        fields = [
            'sensor_id', 'name', 'description', 'location', 'sensor_type',
        ]


class SensorDataSerializer(serializers.ModelSerializer):
    """传感器数据序列化器"""
    class Meta:
        model = SensorData
        fields = ['id', 'data', 'timestamp', 'received_at']


class SensorStatusSerializer(serializers.ModelSerializer):
    """传感器状态记录序列化器"""
    class Meta:
        model = SensorStatusCollection
        fields = ['id', 'data', 'timestamp', 'event_name', 'received_at']
