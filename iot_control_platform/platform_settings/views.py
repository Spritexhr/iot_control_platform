"""
平台配置 API - 仅超级用户可写，已认证用户可读
"""
import logging

from rest_framework import viewsets, status

logger = logging.getLogger("platform_settings")
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from config.permissions import IsSuperuser
from .models import PlatformConfig
from .serializers import PlatformConfigSerializer


class PlatformConfigViewSet(viewsets.ModelViewSet):
    """
    平台配置 CRUD
    - 列表、详情：已认证用户可读
    - 创建、更新、删除：仅超级用户
    - reload：使配置修改生效（MQTT 重连等），无需重启服务
    """
    queryset = PlatformConfig.objects.all()
    serializer_class = PlatformConfigSerializer
    lookup_field = "key"

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy", "reload", "cleanup_old_data"):
            return [IsAuthenticated(), IsSuperuser()]
        return [IsAuthenticated()]

    @action(detail=False, methods=["post"], url_path="reload")
    def reload(self, request):
        """
        使 platform_config 修改生效，无需重启服务
        - MQTT：断开并重连，使用最新 broker/port 等配置
        - 数据留存等：cleanup_old_data 每次执行时读取最新配置
        """
        results = {}
        try:
            from services.mqtt_service import mqtt_service
            from sensors.apps import SensorsConfig

            if SensorsConfig.mqtt_service_started and mqtt_service.client:
                ok = mqtt_service.reconnect(timeout=5)
                results["mqtt"] = "reconnected" if ok else "reconnect_failed"
            else:
                results["mqtt"] = "not_running"
        except Exception as e:
            results["mqtt"] = f"error: {e}"
            logger.warning(f"reload MQTT 异常: {e}")

        logger.info(f"reload 完成: {results}")
        return Response({"message": "reload completed", "results": results}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="cleanup-old-data")
    def cleanup_old_data(self, request):
        """
        执行 cleanup_old_data：按配置的留存天数清理过期传感器/设备数据
        仅超级用户可调用
        """
        try:
            from django.core.management import call_command
            from io import StringIO

            out = StringIO()
            call_command("cleanup_old_data", stdout=out)
            output = out.getvalue().strip()
            logger.info(f"API 触发 cleanup_old_data: {output}")
            return Response(
                {"message": "cleanup completed", "output": output},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.exception("cleanup_old_data 执行失败")
            return Response(
                {"detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
