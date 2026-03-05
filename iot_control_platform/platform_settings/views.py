"""
平台配置 API - 仅超级用户可写，已认证用户可读
"""
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from config.permissions import IsSuperuser
from .models import PlatformConfig
from .serializers import PlatformConfigSerializer


class PlatformConfigViewSet(viewsets.ModelViewSet):
    """
    平台配置 CRUD
    - 列表、详情：已认证用户可读
    - 创建、更新、删除：仅超级用户
    """
    queryset = PlatformConfig.objects.all()
    serializer_class = PlatformConfigSerializer
    lookup_field = "key"

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAuthenticated(), IsSuperuser()]
        return [IsAuthenticated()]
