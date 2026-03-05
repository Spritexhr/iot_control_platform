"""
将 .env 中的配置作为默认值写入 platform_settings
仅当 key 不存在时创建，已存在的配置不会被覆盖
"""
import os
from pathlib import Path

from django.core.management.base import BaseCommand

from platform_settings.models import PlatformConfig


# 配置项定义：(platform_key, env_key, default, category, description, value_type)
CONFIG_ITEMS = [
    ("mqtt_broker", "MQTT_BROKER", "127.0.0.1", "mqtt", "MQTT/EMQX 服务器地址", str),
    ("mqtt_port", "MQTT_PORT", 1883, "mqtt", "MQTT 端口", int),
    ("mqtt_keepalive", "MQTT_KEEPALIVE", 60, "mqtt", "MQTT 保活间隔（秒）", int),
    ("mqtt_username", "MQTT_USERNAME", "", "mqtt", "MQTT 用户名（可选）", str),
    ("mqtt_password", "MQTT_PASSWORD", "", "mqtt", "MQTT 密码（可选）", str),
    ("device_offline_timeout", "DEVICE_OFFLINE_TIMEOUT", 300, "devices", "设备离线判定超时（秒）", int),
    ("device_reconnect_attempts", "DEVICE_RECONNECT_ATTEMPTS", 3, "devices", "设备重连尝试次数", int),
    ("device_reconnect_interval", "DEVICE_RECONNECT_INTERVAL", 10, "devices", "设备重连间隔（秒）", int),
]


def _load_dotenv(env_path: Path) -> None:
    """简单解析 .env 文件并注入 os.environ"""
    if not env_path.exists():
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip("'\"").strip()
                if key and value:
                    os.environ.setdefault(key, value)


def _to_value(raw: str, value_type: type):
    """将字符串转换为目标类型"""
    if value_type == int:
        try:
            return int(raw)
        except (ValueError, TypeError):
            return 0
    if value_type == bool:
        return str(raw).lower() in ("true", "1", "yes")
    return str(raw)


class Command(BaseCommand):
    help = "将 .env 中的配置作为默认值写入 platform_settings（仅创建不存在的 key）"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="强制更新已存在的配置（使用 env 值覆盖）",
        )
        parser.add_argument(
            "--env",
            type=str,
            default=None,
            help=".env 文件路径，默认查找项目根目录",
        )

    def handle(self, *args, **options):
        force = options["force"]
        env_path = options["env"]

        # 查找 .env 文件
        if env_path:
            env_file = Path(env_path)
        else:
            # 项目根目录：manage.py 所在目录的父级
            base = Path(__file__).resolve().parent.parent.parent.parent.parent
            env_file = base / ".env"

        self.stdout.write(f"加载 .env: {env_file}")
        _load_dotenv(env_file)

        created = 0
        updated = 0

        for key, env_key, default, category, description, value_type in CONFIG_ITEMS:
            raw = os.environ.get(env_key)
            if raw is not None and raw != "":
                value = _to_value(raw, value_type)
            else:
                value = default

            obj, was_created = PlatformConfig.objects.get_or_create(
                key=key,
                defaults={
                    "value": value,
                    "category": category,
                    "description": description,
                },
            )
            if was_created:
                created += 1
                self.stdout.write(self.style.SUCCESS(f"  创建: {key} = {value}"))
            elif force:
                obj.value = value
                obj.category = category
                obj.description = description
                obj.save()
                updated += 1
                self.stdout.write(self.style.WARNING(f"  更新: {key} = {value}"))
            else:
                self.stdout.write(f"  跳过（已存在）: {key}")

        self.stdout.write(self.style.SUCCESS(f"\n完成: 创建 {created} 条, 更新 {updated} 条"))
