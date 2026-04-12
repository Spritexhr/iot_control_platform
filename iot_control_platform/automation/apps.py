import sys
from django.apps import AppConfig


class AutomationConfig(AppConfig):
    name = "automation"

    def ready(self):
        # 仅在非迁移、非收集静态文件、非测试的正常运行状态下启动调度器
        if "runserver" in sys.argv or "gunicorn" in sys.argv[0]:
            from .scheduler import start_scheduler
            start_scheduler()
