"""
平台配置模型 - Key-Value 存储非敏感、可调配置
使用 JSON 格式存储，支持字符串、数字、列表、字典等
"""
from django.db import models


class PlatformConfig(models.Model):
    """
    平台配置 - Key-Value 结构，value 为 JSON 格式
    仅存储非敏感、可运行时调整的配置
    value 支持：str、int、float、list、dict、bool、None
    """
    key = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="配置键",
        help_text="唯一标识，如 mqtt_broker、site_name",
    )
    value = models.JSONField(
        default=None,
        null=True,
        blank=True,
        verbose_name="配置值",
        help_text="JSON 格式，支持字符串、数字、列表、字典等，如 \"127.0.0.1\"、1883、[\"DHT11-001\"]、{\"host\":\"x\",\"port\":1883}",
    )
    category = models.CharField(
        max_length=50,
        default="general",
        verbose_name="分类",
        help_text="如 mqtt、general、ui 等，便于分组管理",
    )
    description = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="说明",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "平台配置"
        verbose_name_plural = "平台配置"
        ordering = ["category", "key"]

    def __str__(self):
        val_str = str(self.value)
        return f"{self.key}={val_str[:50]}..." if len(val_str) > 50 else f"{self.key}={val_str}"

    @classmethod
    def get_value(cls, key: str, default=None):
        """
        获取配置值，不存在时返回 default
        value 为 JSON 解析后的 Python 对象（str、int、list、dict 等）
        可配合缓存使用以减少数据库查询
        """
        try:
            obj = cls.objects.get(key=key)
            return obj.value
        except cls.DoesNotExist:
            return default
