from django.contrib import admin

from .models import PlantDiagram


@admin.register(PlantDiagram)
class PlantDiagramAdmin(admin.ModelAdmin):
    list_display = ("name", "plant_code", "is_default", "sort_order", "updated_at")
    list_filter = ("plant_code", "is_default")
    search_fields = ("name", "plant_code", "description")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("plant_code", "sort_order")
