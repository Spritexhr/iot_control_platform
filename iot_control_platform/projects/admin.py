from django.contrib import admin

from .models import (
    Project,
    ProjectDeviceMember,
    ProjectSection,
    ProjectSensorMember,
    ProjectView,
)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "scene_type", "is_active", "sort_order", "updated_at")
    list_filter = ("scene_type", "is_active")
    search_fields = ("code", "name")


@admin.register(ProjectSection)
class ProjectSectionAdmin(admin.ModelAdmin):
    list_display = ("project", "name", "sort_order")
    list_filter = ("project",)


@admin.register(ProjectSensorMember)
class ProjectSensorMemberAdmin(admin.ModelAdmin):
    list_display = ("project", "tag", "sensor", "data_key", "section", "is_visible", "sort_order")
    list_filter = ("project", "is_visible", "severity")
    search_fields = ("tag", "sensor__sensor_id", "sensor__name")


@admin.register(ProjectDeviceMember)
class ProjectDeviceMemberAdmin(admin.ModelAdmin):
    list_display = ("project", "tag", "device", "section", "is_visible", "sort_order")
    list_filter = ("project", "is_visible")
    search_fields = ("tag", "device__device_id", "device__name")


@admin.register(ProjectView)
class ProjectViewAdmin(admin.ModelAdmin):
    list_display = ("project", "name", "view_type", "is_default", "sort_order")
    list_filter = ("project", "view_type")
