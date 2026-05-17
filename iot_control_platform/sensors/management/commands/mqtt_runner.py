"""
独立 MQTT 客户端进程入口。

部署：docker-compose 中 backend service 设 IOT_MQTT_RUNNER=false（不跑 MQTT），
单独跑一个 mqtt_runner service：`python manage.py mqtt_runner`。

启动流程：SensorsConfig.ready() 在 sys.argv 含 'mqtt_runner' 时会自动启动
MQTT 客户端（注册 handler、订阅主题）。本命令只负责让主线程保持存活，
paho-mqtt 的后台线程在 loop_start() 内自管消息收发。

进程内 MQTT 消息处理仍会调 Django ORM（写 SensorData/DeviceStatusCollection），
触发 services.realtime.signals → dispatch.publish_* → channel layer (redis)
→ backend worker 的 consumer → 浏览器。
"""
import logging
import signal
import time

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "运行独立 MQTT 客户端进程（与 web worker 分离）"

    def handle(self, *args, **options):
        # MQTT 客户端在 SensorsConfig.ready() 中已启动。这里只阻塞主线程。
        from services.mqtt_service import mqtt_service

        # SIGTERM / SIGINT 优雅退出
        stop = {"flag": False}

        def _shutdown(signum, frame):
            stop["flag"] = True

        signal.signal(signal.SIGTERM, _shutdown)
        signal.signal(signal.SIGINT, _shutdown)

        self.stdout.write(self.style.SUCCESS(
            f"MQTT runner started (connected={getattr(mqtt_service, 'is_connected', False)})"
        ))
        try:
            while not stop["flag"]:
                time.sleep(1)
        finally:
            self.stdout.write("Stopping MQTT runner...")
            try:
                mqtt_service.stop()
            except Exception:
                pass
            self.stdout.write(self.style.SUCCESS("MQTT runner stopped"))
