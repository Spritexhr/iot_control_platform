from rest_framework import serializers
from .models import AutomationRule


class AutomationRuleListSerializer(serializers.ModelSerializer):
    """自动化规则列表序列化器"""
    device_count = serializers.SerializerMethodField()

    class Meta:
        model = AutomationRule
        fields = [
            'id', 'name', 'description', 'script_id',
            'device_list', 'device_count',
            'is_launched', 'poll_interval', 'process_status', 'error_message',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'device_count',
                            'is_launched', 'process_status', 'error_message']

    def get_device_count(self, obj):
        return obj.get_device_count()


class AutomationRuleDetailSerializer(AutomationRuleListSerializer):
    """自动化规则详情序列化器（含脚本内容）"""
    class Meta(AutomationRuleListSerializer.Meta):
        fields = AutomationRuleListSerializer.Meta.fields + ['script']


class AutomationRuleCreateUpdateSerializer(serializers.ModelSerializer):
    """自动化规则创建/更新序列化器"""
    class Meta:
        model = AutomationRule
        fields = [
            'id', 'name', 'description', 'script_id',
            'script', 'device_list', 'poll_interval',
        ]
        read_only_fields = ['id']
