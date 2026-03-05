"""
平台配置 Admin - 仅管理员可管理
"""
from django.contrib import admin
from .models import PlatformConfig


@admin.register(PlatformConfig)
class PlatformConfigAdmin(admin.ModelAdmin):
    list_display = ["key", "value_short", "category", "description", "updated_at"]
    list_filter = ["category"]
    search_fields = ["key", "description"]
    ordering = ["category", "key"]

    def value_short(self, obj):
        val = obj.value
        if val is None:
            return "-"
        s = str(val)
        return s[:50] + "..." if len(s) > 50 else s

    value_short.short_description = "配置值"
