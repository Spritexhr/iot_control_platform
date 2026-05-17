"""
EB 装置 WebSocket 路由。

由 config/asgi.py 在启动时通过 plugin.json 的 ws_module 字段动态收集。
"""
from django.urls import path

from .consumers import EBPlantConsumer

websocket_urlpatterns = [
    path("ws/plugins/eb_plant/", EBPlantConsumer.as_asgi()),
]
