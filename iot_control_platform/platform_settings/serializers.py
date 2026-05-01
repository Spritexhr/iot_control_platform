from rest_framework import serializers
from .models import PlatformConfig, Plugin


class PlatformConfigSerializer(serializers.ModelSerializer):
    """平台配置序列化器"""

    class Meta:
        model = PlatformConfig
        fields = ["id", "key", "value", "category", "description", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class PluginSerializer(serializers.ModelSerializer):
    """插件序列化器"""

    class Meta:
        model = Plugin
        fields = ["id", "name", "enabled", "version", "description", "installed_at", "updated_at"]
        read_only_fields = ["id", "name", "version", "description", "installed_at", "updated_at"]
