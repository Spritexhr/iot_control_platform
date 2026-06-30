from django.contrib import admin

from .models import ResourceFolder


@admin.register(ResourceFolder)
class ResourceFolderAdmin(admin.ModelAdmin):
    list_display = ("name", "resource_type", "parent", "sort_order", "updated_at")
    list_filter = ("resource_type",)
    search_fields = ("name",)

