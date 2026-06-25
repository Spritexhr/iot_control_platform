from django.apps import AppConfig


class AutomationConfig(AppConfig):
    name = "automation"

    def ready(self):
        # 调度器（自动化规则 + 控制方案）只在单一完整模式常驻进程启动，
        # 避免多 worker 重复执行 / 重复向设备下发命令（判定见 scheduler.scheduler_enabled）。
        from .scheduler import scheduler_enabled, start_scheduler
        if scheduler_enabled():
            start_scheduler()
