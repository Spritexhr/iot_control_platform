"""
EB 大屏插件序列化器。
"""
from rest_framework import serializers

from devices.models import Device
from sensors.models import Sensor

from .models import EBPlantConfig, EBPlantDeviceBinding, EBPlantSensorBinding


class EBPlantConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = EBPlantConfig
        fields = ["id", "name", "view_settings", "updated_at"]
        read_only_fields = ["id", "name", "updated_at"]


class EBPlantSensorBindingSerializer(serializers.ModelSerializer):
    """读用：嵌套返回 sensor 的关键信息便于前端展示。"""

    sensor_id = serializers.CharField(source="sensor.sensor_id", read_only=True)
    sensor_name = serializers.CharField(source="sensor.name", read_only=True)
    sensor_type = serializers.SerializerMethodField()
    data_fields = serializers.SerializerMethodField()
    point_id = serializers.CharField(read_only=True)

    class Meta:
        model = EBPlantSensorBinding
        fields = [
            "id", "sensor", "sensor_id", "sensor_name", "sensor_type", "data_fields",
            "point_id",
            "tag", "area", "data_key", "unit",
            "normal_value", "hi_threshold", "lo_threshold", "severity",
            "sort_order", "is_visible",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "sensor_id", "sensor_name", "sensor_type", "data_fields",
            "point_id", "created_at", "updated_at",
        ]

    def get_sensor_type(self, obj):
        return obj.sensor.sensor_type.name if obj.sensor.sensor_type_id else ""

    def get_data_fields(self, obj):
        return obj.sensor.sensor_type.data_fields if obj.sensor.sensor_type_id else []


class EBPlantDeviceBindingSerializer(serializers.ModelSerializer):
    device_id = serializers.CharField(source="device.device_id", read_only=True)
    device_name = serializers.CharField(source="device.name", read_only=True)
    device_type = serializers.SerializerMethodField()
    commands = serializers.SerializerMethodField()

    class Meta:
        model = EBPlantDeviceBinding
        fields = [
            "id", "device", "device_id", "device_name", "device_type", "commands",
            "tag", "area", "sort_order", "is_visible",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "device_id", "device_name", "device_type", "commands", "created_at", "updated_at"]
        extra_kwargs = {"device": {"write_only": True}}

    def get_device_type(self, obj):
        return obj.device.device_type.name if obj.device.device_type_id else ""

    def get_commands(self, obj):
        if not obj.device.device_type_id:
            return []
        cmds = obj.device.device_type.commands or {}
        return list(cmds.keys()) if isinstance(cmds, dict) else []


class BindableSensorSerializer(serializers.ModelSerializer):
    """供"挑选要导入的传感器"下拉用，返回主模型基本信息。"""

    sensor_type = serializers.CharField(source="sensor_type.name", read_only=True)
    data_fields = serializers.SerializerMethodField()
    bound_data_keys = serializers.SerializerMethodField()

    class Meta:
        model = Sensor
        fields = ["id", "sensor_id", "name", "location", "sensor_type", "data_fields", "bound_data_keys"]

    def get_data_fields(self, obj):
        return obj.sensor_type.data_fields if obj.sensor_type_id else []

    def get_bound_data_keys(self, obj):
        """已被 EB 大屏占用的 data_key 列表（空字符串表示"未选字段"那条）。
        用于前端判断"还能不能再次导入 / 还能新增哪个字段"。
        """
        return list(obj.eb_bindings.values_list("data_key", flat=True))


class BindableDeviceSerializer(serializers.ModelSerializer):
    device_type = serializers.CharField(source="device_type.name", read_only=True)
    commands = serializers.SerializerMethodField()
    already_bound = serializers.SerializerMethodField()

    class Meta:
        model = Device
        fields = ["id", "device_id", "name", "location", "device_type", "commands", "already_bound"]

    def get_commands(self, obj):
        if not obj.device_type_id:
            return []
        cmds = obj.device_type.commands or {}
        return list(cmds.keys()) if isinstance(cmds, dict) else []

    def get_already_bound(self, obj):
        return hasattr(obj, "eb_device_binding")
