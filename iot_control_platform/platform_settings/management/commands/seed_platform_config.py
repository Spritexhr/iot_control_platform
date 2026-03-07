"""
从 default_config.json 读取默认配置，与 .env 中的必备项合并后写入 platform_settings
.env 仅保留启动必备信息（DB、MQTT 连接等），其他配置在 JSON 中定义默认值
"""
import json
import logging
import os
from pathlib import Path

from django.core.management.base import BaseCommand

from platform_settings.models import PlatformConfig

logger = logging.getLogger("platform_settings")


def _get_default_config_path() -> Path:
    """获取 default_config.json 路径"""
    return Path(__file__).resolve().parent.parent.parent / "default_config.json"


def load_default_config() -> list:
    """
    加载 default_config.json，返回 configs 列表
    每项: {key, default, env_key, category, description}
    """
    path = _get_default_config_path()
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("configs", [])


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
                if key:
                    os.environ.setdefault(key, value)


def _to_value(raw, default, value_type: type):
    """将值转换为目标类型"""
    if raw is None or raw == "":
        return default
    if value_type == int:
        try:
            return int(raw)
        except (ValueError, TypeError):
            return default
    if value_type == bool:
        return str(raw).lower() in ("true", "1", "yes")
    return str(raw)


def _infer_value_type(default) -> type:
    """从默认值推断类型"""
    if isinstance(default, bool):
        return bool
    if isinstance(default, int):
        return int
    if isinstance(default, float):
        return float
    return str


class Command(BaseCommand):
    help = "从 default_config.json 与 .env 合并配置，写入 platform_settings"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="强制更新已存在的配置",
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

        # 加载 default_config.json
        configs = load_default_config()
        if not configs:
            msg = "未找到 default_config.json 或 configs 为空"
            logger.error(msg)
            self.stdout.write(self.style.ERROR(msg))
            return

        logger.info(f"已加载 {len(configs)} 项默认配置")
        self.stdout.write(f"已加载 {len(configs)} 项默认配置")

        # 加载 .env
        if env_path:
            env_file = Path(env_path)
        else:
            base = Path(__file__).resolve().parent.parent.parent.parent.parent
            env_file = base / ".env"

        logger.info(f"加载 .env: {env_file}")
        self.stdout.write(f"加载 .env: {env_file}")
        _load_dotenv(env_file)

        created = 0
        updated = 0

        for item in configs:
            key = item.get("key")
            if not key:
                continue

            default = item.get("default")
            env_key = item.get("env_key")
            category = item.get("category", "general")
            description = item.get("description", "")
            value_type = _infer_value_type(default)

            # 优先使用 env，否则用 JSON 默认值
            if env_key:
                raw = os.environ.get(env_key)
                value = _to_value(raw, default, value_type)
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
                logger.info(f"  创建: {key} = {value}")
                self.stdout.write(self.style.SUCCESS(f"  创建: {key} = {value}"))
            elif force:
                obj.value = value
                obj.category = category
                obj.description = description
                obj.save()
                updated += 1
                logger.info(f"  更新: {key} = {value}")
                self.stdout.write(self.style.WARNING(f"  更新: {key} = {value}"))
            else:
                logger.debug(f"  跳过（已存在）: {key}")
                self.stdout.write(f"  跳过（已存在）: {key}")

        summary = f"完成: 创建 {created} 条, 更新 {updated} 条"
        logger.info(summary)
        self.stdout.write(self.style.SUCCESS(f"\n{summary}"))
