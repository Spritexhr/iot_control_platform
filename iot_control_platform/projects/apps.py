"""
projects 应用配置 —— 平台原生「项目/场景」系统。

一个项目（场景）= 装置（传感器/设备成员）+ 控制（自动化规则）+ 展示（多视图）。
ready() 中挂载实时数据注入信号（按项目成员过滤 SensorData，参照 plugins/eb_plant/signals.py）。
"""
from django.apps import AppConfig


class ProjectsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "projects"
    verbose_name = "项目/场景"

    def ready(self):
        from . import signals  # noqa: F401
