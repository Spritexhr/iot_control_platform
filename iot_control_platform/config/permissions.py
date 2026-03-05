"""
自定义权限类
"""
from rest_framework.permissions import BasePermission


class IsSuperuser(BasePermission):
    """仅超级用户（is_superuser）可访问"""

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_superuser
