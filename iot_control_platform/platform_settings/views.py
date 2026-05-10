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
from .defaults import DEFAULT_CONFIGS
from .models import PlatformConfig, Plugin
from .serializers import PlatformConfigSerializer, PluginSerializer


# 类型推断：value_type 字符串 -> 前端控件提示
_TYPE_NAMES = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "list",
    dict: "object",
}


def _infer_type(item: dict) -> str:
    """从 defaults.py 条目推断前端展示用的类型字符串"""
    explicit = item.get("value_type")
    if explicit is not None:
        return _TYPE_NAMES.get(explicit, "string")
    default = item.get("default")
    return _TYPE_NAMES.get(type(default), "string")


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
        if self.action in ("create", "update", "partial_update", "destroy", "reload", "cleanup_old_data", "test_mqtt"):
            return [IsAuthenticated(), IsSuperuser()]
        return [IsAuthenticated()]

    @action(detail=False, methods=["get"], url_path="schema")
    def schema(self, request):
        """
        返回 defaults.py 中预定义的配置项 schema，给前端按分类渲染表单
        """
        items = []
        for item in DEFAULT_CONFIGS:
            items.append({
                "key": item["key"],
                "category": item.get("category", "general"),
                "default": item.get("default"),
                "description": item.get("description", ""),
                "secret": bool(item.get("secret", False)),
                "type": _infer_type(item),
            })
        # 已知 key 集合也一并返回，方便前端区分预定义与自定义配置
        known_keys = [it["key"] for it in items]
        return Response({"items": items, "known_keys": known_keys})

    @action(detail=False, methods=["post"], url_path="test-mqtt")
    def test_mqtt(self, request):
        """
        测试 MQTT 连接：使用前端传入的 broker/port/username/password，
        或不传则用当前 PlatformConfig 中的值。返回成功/失败和错误消息。
        不会影响正在运行的 mqtt_service。
        """
        import os
        import threading

        import paho.mqtt.client as mqtt

        from .models import PlatformConfig

        def _cfg(key, default):
            v = PlatformConfig.get_value(key, default)
            return v if v is not None else default

        broker = request.data.get("broker") or _cfg("mqtt_broker", "127.0.0.1")
        port_raw = request.data.get("port", _cfg("mqtt_port", 1883))
        username = request.data.get("username")
        if username is None:
            username = _cfg("mqtt_username", "")
        password = request.data.get("password")
        if password is None:
            password = _cfg("mqtt_password", "")

        try:
            port = int(port_raw)
        except (TypeError, ValueError):
            return Response(
                {"success": False, "message": f"端口格式错误: {port_raw!r}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        connected = threading.Event()
        result = {"rc": None, "error": None}

        def _on_connect(client, userdata, flags, rc):
            result["rc"] = rc
            connected.set()

        client = mqtt.Client(client_id=f"iot_platform_test_{os.getpid()}")
        if username and password:
            client.username_pw_set(username, password)
        client.on_connect = _on_connect

        try:
            client.connect_async(broker, port, keepalive=10)
            client.loop_start()
            ok = connected.wait(timeout=5)
            client.loop_stop()
            try:
                client.disconnect()
            except Exception:
                pass

            if not ok:
                return Response(
                    {"success": False, "message": f"连接超时（{broker}:{port}）"},
                    status=status.HTTP_200_OK,
                )

            rc = result["rc"]
            if rc == 0:
                return Response(
                    {"success": True, "message": f"连接成功（{broker}:{port}）"},
                    status=status.HTTP_200_OK,
                )

            rc_msg = {
                1: "协议版本不支持",
                2: "客户端 ID 被拒绝",
                3: "服务器不可用",
                4: "用户名或密码错误",
                5: "未授权",
            }.get(rc, f"返回码 {rc}")
            return Response(
                {"success": False, "message": f"连接失败：{rc_msg}"},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            try:
                client.loop_stop()
            except Exception:
                pass
            return Response(
                {"success": False, "message": f"连接异常：{e}"},
                status=status.HTTP_200_OK,
            )

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


class PluginViewSet(viewsets.ReadOnlyModelViewSet):
    """
    插件登记表只读 + 启用切换
    - list / retrieve：已认证用户
    - sync / enable / disable：仅超级用户
    - 启用状态变更后需重启 Django 进程才会影响 URL 路由
    """
    queryset = Plugin.objects.all()
    serializer_class = PluginSerializer
    lookup_field = "name"

    def get_permissions(self):
        if self.action in ("sync", "enable", "disable"):
            return [IsAuthenticated(), IsSuperuser()]
        return [IsAuthenticated()]

    @action(detail=False, methods=["post"], url_path="sync")
    def sync(self, request):
        """触发 sync_plugins 管理命令，把文件系统插件同步到 DB"""
        try:
            from django.core.management import call_command
            from io import StringIO

            out = StringIO()
            call_command("sync_plugins", stdout=out)
            output = out.getvalue().strip()
            logger.info(f"API 触发 sync_plugins: {output}")
            return Response({"message": "sync completed", "output": output})
        except Exception as e:
            logger.exception("sync_plugins 失败")
            return Response(
                {"detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"], url_path="enable")
    def enable(self, request, name=None):
        plugin = self.get_object()
        plugin.enabled = True
        plugin.save(update_fields=["enabled", "updated_at"])
        return Response({
            "message": "enabled (restart required to take effect)",
            "plugin": PluginSerializer(plugin).data,
        })

    @action(detail=True, methods=["post"], url_path="disable")
    def disable(self, request, name=None):
        plugin = self.get_object()
        plugin.enabled = False
        plugin.save(update_fields=["enabled", "updated_at"])
        return Response({
            "message": "disabled (restart required to take effect)",
            "plugin": PluginSerializer(plugin).data,
        })
