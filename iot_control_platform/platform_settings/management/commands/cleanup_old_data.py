"""
按 platform_settings 配置的数据留存天数清理过期数据
从 platform_config 读取 sensor_data_retention_days、device_data_retention_days
可配合 cron 定时执行，或通过 API 触发
"""
import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from config.platform_config import get_config

logger = logging.getLogger("platform_settings")


class Command(BaseCommand):
    help = "按 platform_settings 配置清理过期的传感器/设备数据"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="仅统计将删除的数量，不实际删除",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        if dry_run:
            msg = "【试运行模式】不会实际删除数据"
            logger.info(msg)
            self.stdout.write(self.style.WARNING(msg))

        sensor_days = get_config("sensor_data_retention_days", 30, int)
        device_days = get_config("device_data_retention_days", 30, int)

        sensor_cutoff = timezone.now() - timedelta(days=sensor_days)
        device_cutoff = timezone.now() - timedelta(days=device_days)

        from sensors.models import SensorData
        from devices.models import DeviceData

        sensor_qs = SensorData.objects.filter(timestamp__lt=sensor_cutoff)
        device_qs = DeviceData.objects.filter(timestamp__lt=device_cutoff)

        sensor_count = sensor_qs.count()
        device_count = device_qs.count()

        logger.info(f"传感器数据保留 {sensor_days} 天，将清理 {sensor_count} 条")
        logger.info(f"设备数据保留 {device_days} 天，将清理 {device_count} 条")
        self.stdout.write(f"传感器数据保留 {sensor_days} 天，将清理 {sensor_count} 条")
        self.stdout.write(f"设备数据保留 {device_days} 天，将清理 {device_count} 条")

        if not dry_run:
            if sensor_count > 0:
                sensor_qs.delete()
                logger.info(f"  已删除 {sensor_count} 条传感器数据")
                self.stdout.write(self.style.SUCCESS(f"  已删除 {sensor_count} 条传感器数据"))
            if device_count > 0:
                device_qs.delete()
                logger.info(f"  已删除 {device_count} 条设备数据")
                self.stdout.write(self.style.SUCCESS(f"  已删除 {device_count} 条设备数据"))
            if sensor_count == 0 and device_count == 0:
                msg = "  无过期数据需要清理"
                logger.info(msg)
                self.stdout.write(msg)
