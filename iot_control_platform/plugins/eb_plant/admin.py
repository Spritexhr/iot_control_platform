from django.contrib import admin

from .models import EBPlantConfig, EBPlantSensorBinding, EBPlantDeviceBinding


@admin.register(EBPlantConfig)
class EBPlantConfigAdmin(admin.ModelAdmin):
    list_display = ["name", "updated_at"]


@admin.register(EBPlantSensorBinding)
class EBPlantSensorBindingAdmin(admin.ModelAdmin):
    list_display = ["tag", "sensor", "area", "data_key", "unit", "hi_threshold", "lo_threshold", "severity", "is_visible", "sort_order"]
    list_filter = ["area", "severity", "is_visible"]
    search_fields = ["tag", "sensor__sensor_id", "sensor__name"]
    autocomplete_fields = ["sensor"]


@admin.register(EBPlantDeviceBinding)
class EBPlantDeviceBindingAdmin(admin.ModelAdmin):
    list_display = ["tag", "device", "area", "is_visible", "sort_order"]
    list_filter = ["area", "is_visible"]
    search_fields = ["tag", "device__device_id", "device__name"]
    autocomplete_fields = ["device"]
