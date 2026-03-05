from rest_framework import serializers
from .models import PlatformConfig


class PlatformConfigSerializer(serializers.ModelSerializer):
    """平台配置序列化器"""

    class Meta:
        model = PlatformConfig
        fields = ["id", "key", "value", "category", "description", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]
