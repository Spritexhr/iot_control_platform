from django.db.models import Q
from rest_framework import serializers

from .models import ResourceFolder


class ResourceFolderSerializer(serializers.ModelSerializer):
    child_count = serializers.IntegerField(read_only=True)
    resource_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = ResourceFolder
        fields = [
            "id", "name", "resource_type", "parent", "sort_order",
            "child_count", "resource_count", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "child_count", "resource_count", "created_at", "updated_at"]

    def validate(self, attrs):
        instance = self.instance
        resource_type = attrs.get("resource_type", getattr(instance, "resource_type", None))
        parent = attrs.get("parent", getattr(instance, "parent", None))
        name = attrs.get("name", getattr(instance, "name", "")).strip()
        attrs["name"] = name
        if not name:
            raise serializers.ValidationError({"name": "文件夹名称不能为空"})
        if parent and parent.resource_type != resource_type:
            raise serializers.ValidationError({"parent": "父文件夹必须属于同一种资源类型"})
        current = parent
        while current is not None:
            if instance and current.pk == instance.pk:
                raise serializers.ValidationError({"parent": "不能移动到自身或其子文件夹中"})
            current = current.parent
        duplicate = ResourceFolder.objects.filter(
            resource_type=resource_type, parent=parent, name=name,
        )
        if instance:
            duplicate = duplicate.exclude(pk=instance.pk)
        if duplicate.exists():
            raise serializers.ValidationError({"name": "同级目录中已存在同名文件夹"})
        return attrs

    def validate_resource_type(self, value):
        if self.instance and value != self.instance.resource_type:
            raise serializers.ValidationError("创建后不能修改资源类型")
        return value

