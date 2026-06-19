"""
ASGI config for config project.

ProtocolTypeRouter：HTTP 仍走标准 Django，WebSocket 走 channels URLRouter。

WS 路由当前只挂 M1 联调用的 /ws/_ping/；后续 milestone 会按资源逐步追加。
"""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
# 必须先初始化 Django ASGI 应用，再 import 任何依赖 Django 配置的模块（含 channels）
django_asgi_app = get_asgi_application()

from importlib import import_module  # noqa: E402
import logging  # noqa: E402

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from django.urls import path  # noqa: E402

from plugins import discover_plugins, enabled_plugin_names  # noqa: E402
from projects.consumers import ProjectStreamConsumer  # noqa: E402
from services.realtime import consumers as core  # noqa: E402
from services.realtime.middleware import JwtAuthMiddleware  # noqa: E402

_log = logging.getLogger(__name__)

websocket_urlpatterns = [
    path("ws/_ping/", core.PingConsumer.as_asgi()),
    path("ws/sensors/", core.SensorListConsumer.as_asgi()),
    path("ws/sensors/<str:sensor_id>/", core.SensorStreamConsumer.as_asgi()),
    path("ws/devices/", core.DeviceListConsumer.as_asgi()),
    path("ws/devices/<str:device_id>/", core.DeviceStreamConsumer.as_asgi()),
    path("ws/automation/", core.AutomationConsumer.as_asgi()),
    path("ws/system/mqtt/", core.MqttSystemConsumer.as_asgi()),
    path("ws/projects/<int:project_id>/", ProjectStreamConsumer.as_asgi()),
]

# 动态挂载已启用插件的 WS 路由（与 config/urls.py 的 HTTP 路由发现机制对称）
_enabled = enabled_plugin_names()
for _meta in discover_plugins():
    if _meta.name not in _enabled or not _meta.ws_module:
        continue
    try:
        _mod = import_module(_meta.ws_module)
        _patterns = getattr(_mod, "websocket_urlpatterns", None)
        if _patterns:
            websocket_urlpatterns.extend(_patterns)
            _log.info("[plugins-ws] 已挂载 %s → %d 条路由", _meta.name, len(_patterns))
    except Exception as _exc:
        _log.warning("[plugins-ws] 挂载 %s 失败: %s", _meta.name, _exc)

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": JwtAuthMiddleware(URLRouter(websocket_urlpatterns)),
})
