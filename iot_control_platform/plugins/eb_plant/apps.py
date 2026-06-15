from django.apps import AppConfig


class EBPlantConfig(AppConfig):
    name = "plugins.eb_plant"
    label = "plugin_eb_plant"
    verbose_name = "全厂设备辅助监控大屏（插件）"

    def ready(self):
        from . import signals  # noqa: F401
