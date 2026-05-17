from django.apps import AppConfig


class RealtimeConfig(AppConfig):
    """实时数据服务 app —— 集中承载主层 WebSocket consumer / dispatch / signals。"""

    name = "services.realtime"
    label = "services_realtime"
    verbose_name = "Realtime (WebSocket)"

    def ready(self):
        # 注册主模型 post_save → WS 广播的 handler。
        # 必须在 ready() 内 import，不能放模块顶层（顶层 import 会在 apps populate
        # 完成前触发 models 的 import，引发 AppRegistryNotReady）。
        from . import signals  # noqa: F401
        return None
