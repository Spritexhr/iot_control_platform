"""
projects（项目/场景）序列化器。

读接口嵌套返回主模型 Sensor / Device 的关键信息，便于前端展示；
可导入清单（bindable）按当前项目维度计算「已占用」，避免跨项目误判。
"""
from rest_framework import serializers

from devices.models import Device
from sensors.models import Sensor

from .models import (
    Project,
    ProjectDeviceMember,
    ProjectSection,
    ProjectSensorMember,
    ProjectView,
)


def public_command_schema(device) -> dict:
    """把 DeviceType.commands 转成前端 CommandPanel 需要的精简 schema：
    {name: {description, params, confirm?}}，剥掉内部的 mqtt_message。
    confirm=true 的命令前端会二次确认并以 make_sure 下发。"""
    if not device.device_type_id:
        return {}
    cmds = device.device_type.commands or {}
    if not isinstance(cmds, dict):
        return {}
    schema = {}
    for name, info in cmds.items():
        info = info if isinstance(info, dict) else {}
        schema[name] = {
            "description": info.get("description", ""),
            "params": info.get("params", []),
            "confirm": bool(info.get("confirm", False)),
        }
    return schema


class ProjectSerializer(serializers.ModelSerializer):
    section_count = serializers.SerializerMethodField()
    sensor_count = serializers.SerializerMethodField()
    device_count = serializers.SerializerMethodField()
    view_count = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "id", "code", "name", "description", "scene_type",
            "is_active", "sort_order", "view_settings",
            "section_count", "sensor_count", "device_count", "view_count",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "section_count", "sensor_count", "device_count", "view_count",
            "created_at", "updated_at",
        ]

    def get_section_count(self, obj):
        return obj.sections.count()

    def get_sensor_count(self, obj):
        return obj.sensor_members.count()

    def get_device_count(self, obj):
        return obj.device_members.count()

    def get_view_count(self, obj):
        return obj.views.count()


class ProjectSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectSection
        fields = ["id", "project", "name", "sort_order", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class ProjectSensorMemberSerializer(serializers.ModelSerializer):
    sensor_id = serializers.CharField(source="sensor.sensor_id", read_only=True)
    sensor_name = serializers.CharField(source="sensor.name", read_only=True)
    sensor_type = serializers.SerializerMethodField()
    data_fields = serializers.SerializerMethodField()
    point_id = serializers.CharField(read_only=True)
    section_name = serializers.CharField(source="section.name", read_only=True, default="")

    class Meta:
        model = ProjectSensorMember
        fields = [
            "id", "project", "sensor", "sensor_id", "sensor_name", "sensor_type", "data_fields",
            "point_id",
            "section", "section_name",
            "tag", "area", "data_key", "unit",
            "normal_value", "hi_threshold", "lo_threshold", "severity",
            "sort_order", "is_visible",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "sensor_id", "sensor_name", "sensor_type", "data_fields",
            "point_id", "section_name", "created_at", "updated_at",
        ]

    def get_sensor_type(self, obj):
        return obj.sensor.sensor_type.name if obj.sensor.sensor_type_id else ""

    def get_data_fields(self, obj):
        return obj.sensor.sensor_type.data_fields if obj.sensor.sensor_type_id else []


class ProjectDeviceMemberSerializer(serializers.ModelSerializer):
    device_id = serializers.CharField(source="device.device_id", read_only=True)
    device_name = serializers.CharField(source="device.name", read_only=True)
    device_type = serializers.SerializerMethodField()
    commands = serializers.SerializerMethodField()
    section_name = serializers.CharField(source="section.name", read_only=True, default="")

    class Meta:
        model = ProjectDeviceMember
        fields = [
            "id", "project", "device", "device_id", "device_name", "device_type", "commands",
            "section", "section_name",
            "tag", "area", "sort_order", "is_visible",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "device_id", "device_name", "device_type", "commands",
            "section_name", "created_at", "updated_at",
        ]

    def get_device_type(self, obj):
        return obj.device.device_type.name if obj.device.device_type_id else ""

    def get_commands(self, obj):
        return public_command_schema(obj.device)


class ProjectViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectView
        fields = [
            "id", "project", "name", "view_type", "config",
            "is_default", "sort_order", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class BindableSensorSerializer(serializers.ModelSerializer):
    """供「挑选要导入到本项目的传感器」下拉用。bound_data_keys 按当前项目过滤。"""

    sensor_type = serializers.CharField(source="sensor_type.name", read_only=True)
    data_fields = serializers.SerializerMethodField()
    bound_data_keys = serializers.SerializerMethodField()

    class Meta:
        model = Sensor
        fields = ["id", "sensor_id", "name", "location", "sensor_type", "data_fields", "bound_data_keys"]

    def get_data_fields(self, obj):
        return obj.sensor_type.data_fields if obj.sensor_type_id else []

    def get_bound_data_keys(self, obj):
        pid = self.context.get("project_id")
        qs = obj.project_members
        if pid is not None:
            qs = qs.filter(project_id=pid)
        return list(qs.values_list("data_key", flat=True))


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
        pid = self.context.get("project_id")
        qs = obj.project_members
        if pid is not None:
            qs = qs.filter(project_id=pid)
        return qs.exists()
