from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta
from .models import DeviceType, Device, DeviceData


class DeviceTypeSerializer(serializers.ModelSerializer):
    """设备类型序列化器"""
    device_count = serializers.SerializerMethodField()

    class Meta:
        model = DeviceType
        fields = [
            'id', 'DeviceType_id', 'name', 'description',
            'state_fields', 'config_parameters', 'commands',
            'created_at', 'device_count',
        ]
        read_only_fields = ['id', 'created_at', 'device_count']

    def get_device_count(self, obj):
        return obj.devices.count()


class DeviceTypeBriefSerializer(serializers.ModelSerializer):
    """设备类型简要序列化器（用于嵌套）"""
    class Meta:
        model = DeviceType
        fields = ['id', 'DeviceType_id', 'name', 'state_fields', 'config_parameters', 'commands']


class DeviceListSerializer(serializers.ModelSerializer):
    """设备列表序列化器（含类型信息和最新状态）"""
    device_type_info = DeviceTypeBriefSerializer(source='device_type', read_only=True)
    latest_data = serializers.SerializerMethodField()
    is_online = serializers.SerializerMethodField()

    class Meta:
        model = Device
        fields = [
            'id', 'device_id', 'name', 'description', 'location',
            'mqtt_topic_data', 'mqtt_topic_control',
            'is_online', 'last_seen',
            'created_at', 'updated_at',
            'device_type', 'device_type_info', 'latest_data',
        ]

    def get_is_online(self, obj):
        """根据 last_seen 和心跳间隔实时计算在线状态"""
        if not obj.last_seen:
            return False
        timeout = timedelta(seconds=obj.get_heartbeat_interval() * 3)
        return (timezone.now() - obj.last_seen) < timeout

    def get_latest_data(self, obj):
        record = obj.data_records.order_by('-timestamp').first()
        if record:
            return {
                'data': record.data,
                'timestamp': record.timestamp,
            }
        return None


class DeviceDetailSerializer(DeviceListSerializer):
    """设备详情序列化器"""
    data_count_24h = serializers.SerializerMethodField()

    class Meta(DeviceListSerializer.Meta):
        fields = DeviceListSerializer.Meta.fields + ['data_count_24h']

    def get_data_count_24h(self, obj):
        start = timezone.now() - timedelta(hours=24)
        return obj.data_records.filter(timestamp__gte=start).count()


class DeviceCreateUpdateSerializer(serializers.ModelSerializer):
    """设备创建/更新序列化器"""
    class Meta:
        model = Device
        fields = [
            'device_id', 'name', 'description', 'location', 'device_type',
        ]


class DeviceDataSerializer(serializers.ModelSerializer):
    """设备数据序列化器"""
    class Meta:
        model = DeviceData
        fields = ['id', 'data', 'timestamp', 'received_at']
