"""
平台配置管理命令——PlatformConfig 表的唯一写入入口。

用法：
  python manage.py configure                    # 交互式 wizard
  python manage.py configure --init             # 仅补缺失的 key（首次部署 / 升级）
  python manage.py configure --set k=v          # 单键写入
  python manage.py configure --unset key        # 恢复默认值（不删除条目）
  python manage.py configure --list             # 列出所有当前值
  python manage.py configure --no-reload        # 写完不调用 reload API

写入后默认会调用 reload，让 MQTT 等服务无感重连。
"""
import getpass
import json
import logging
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from platform_settings.defaults import DEFAULT_CONFIGS, get_meta
from platform_settings.models import PlatformConfig

logger = logging.getLogger("platform_settings")


def _coerce(raw: str, default: Any) -> Any:
    """按 default 的类型把字符串转成对应 Python 类型"""
    if isinstance(default, bool):
        return str(raw).lower() in ("true", "1", "yes", "y", "on")
    if isinstance(default, int):
        try:
            return int(raw)
        except (TypeError, ValueError):
            raise CommandError(f"期望整数，得到: {raw!r}")
    if isinstance(default, float):
        try:
            return float(raw)
        except (TypeError, ValueError):
            raise CommandError(f"期望浮点数，得到: {raw!r}")
    if isinstance(default, (list, dict)):
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise CommandError(f"期望 JSON {type(default).__name__}: {e}")
    return raw


def _format_value(value: Any, secret: bool = False) -> str:
    """显示用：密码打码，列表/字典 JSON 化"""
    if secret and value:
        return "***"
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _upsert(key: str, value: Any, meta: dict) -> str:
    """写入或更新一条 PlatformConfig，返回 'created' / 'updated' / 'unchanged'"""
    obj, created = PlatformConfig.objects.get_or_create(
        key=key,
        defaults={
            "value": value,
            "category": meta.get("category", "general"),
            "description": meta.get("description", ""),
        },
    )
    if created:
        return "created"
    if obj.value == value and obj.category == meta.get("category", obj.category):
        return "unchanged"
    obj.value = value
    obj.category = meta.get("category", obj.category)
    obj.description = meta.get("description", obj.description)
    obj.save()
    return "updated"


def _trigger_reload(stdout) -> None:
    """直接调用 reload 逻辑（不走 HTTP），让 MQTT 等服务重连"""
    try:
        from services.mqtt_service import mqtt_service
        from sensors.apps import SensorsConfig

        if SensorsConfig.mqtt_service_started and mqtt_service.client:
            ok = mqtt_service.reconnect(timeout=5)
            stdout.write(
                f"  MQTT: {'reconnected' if ok else 'reconnect_failed'}"
            )
        else:
            stdout.write("  MQTT: not_running (启动后会用最新配置连接)")
    except Exception as e:
        stdout.write(f"  MQTT: reload skipped ({e})")
        logger.warning(f"configure reload 异常: {e}")


def _print_banner(stdout, style) -> None:
    """首次种子完成后打出醒目提示"""
    stdout.write("")
    stdout.write(style.SUCCESS("=" * 64))
    stdout.write(style.SUCCESS("✅ 平台配置已用默认值初始化"))
    stdout.write("")
    stdout.write("默认 MQTT broker: 127.0.0.1:1883（仅占位，请按实际 EMQX 地址修改）")
    stdout.write("首次部署请运行交互式 wizard 完成配置：")
    stdout.write(style.WARNING(
        "  docker compose exec backend python manage.py configure"
    ))
    stdout.write("")
    stdout.write("或单键设置：")
    stdout.write(
        "  docker compose exec backend python manage.py configure "
        "--set mqtt_broker=192.168.1.10"
    )
    stdout.write(style.SUCCESS("=" * 64))
    stdout.write("")


class Command(BaseCommand):
    help = "PlatformConfig 写入入口（wizard / --set / --unset / --init / --list）"

    def add_arguments(self, parser):
        parser.add_argument(
            "--init",
            action="store_true",
            help="补齐 DEFAULT_CONFIGS 中缺失的 key，已有 key 不动；用于首次部署和升级",
        )
        parser.add_argument(
            "--set",
            dest="set_pairs",
            action="append",
            default=[],
            metavar="KEY=VALUE",
            help="单键设置，可重复。例：--set mqtt_broker=192.168.1.10",
        )
        parser.add_argument(
            "--unset",
            dest="unset_keys",
            action="append",
            default=[],
            metavar="KEY",
            help="把 key 重置为 DEFAULT_CONFIGS 中的默认值",
        )
        parser.add_argument(
            "--list",
            action="store_true",
            help="列出所有当前配置",
        )
        parser.add_argument(
            "--no-reload",
            action="store_true",
            help="写完不调用 reload（不让 MQTT 重连）",
        )

    def handle(self, *args, **options):
        if options["list"]:
            self._handle_list()
            return

        if options["init"]:
            self._handle_init()
            return

        if options["set_pairs"] or options["unset_keys"]:
            self._handle_set_unset(options["set_pairs"], options["unset_keys"])
            if not options["no_reload"]:
                self.stdout.write("\n触发 reload:")
                _trigger_reload(self.stdout)
            return

        # 默认行为：交互式 wizard
        self._handle_wizard()
        if not options["no_reload"]:
            self.stdout.write("\n触发 reload:")
            _trigger_reload(self.stdout)

    # ---------- 各模式实现 ----------

    def _handle_list(self) -> None:
        """列出所有当前配置（密码打码）"""
        self.stdout.write(self.style.HTTP_INFO("当前 PlatformConfig 内容："))
        configs = PlatformConfig.objects.order_by("category", "key")
        if not configs.exists():
            self.stdout.write("  （空，可执行 configure --init 写入默认值）")
            return
        last_cat = None
        for cfg in configs:
            if cfg.category != last_cat:
                self.stdout.write(f"\n[{cfg.category}]")
                last_cat = cfg.category
            meta = get_meta(cfg.key)
            secret = meta.get("secret", False)
            self.stdout.write(
                f"  {cfg.key} = {_format_value(cfg.value, secret)}"
                f"   {self.style.HTTP_INFO('# ' + (cfg.description or ''))}"
            )

    def _handle_init(self) -> None:
        """首次部署 / 升级：仅补缺失的 key"""
        existing_keys = set(PlatformConfig.objects.values_list("key", flat=True))
        is_first_run = len(existing_keys) == 0
        created = 0
        skipped = 0

        for item in DEFAULT_CONFIGS:
            key = item["key"]
            if key in existing_keys:
                skipped += 1
                continue
            _upsert(key, item["default"], item)
            created += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f"  + {key} = {_format_value(item['default'], item.get('secret', False))}"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(f"\n完成: 新增 {created} 项, 跳过 {skipped} 项")
        )

        if is_first_run and created > 0:
            _print_banner(self.stdout, self.style)

    def _handle_set_unset(self, set_pairs: list, unset_keys: list) -> None:
        """处理 --set / --unset"""
        for pair in set_pairs:
            if "=" not in pair:
                raise CommandError(f"--set 格式错误，需 KEY=VALUE: {pair!r}")
            key, raw = pair.split("=", 1)
            key = key.strip()
            meta = get_meta(key)
            if not meta:
                raise CommandError(
                    f"未知配置项: {key!r}。可用 key: "
                    f"{', '.join(c['key'] for c in DEFAULT_CONFIGS)}"
                )
            value = _coerce(raw, meta["default"])
            result = _upsert(key, value, meta)
            self.stdout.write(self.style.SUCCESS(
                f"  [{result}] {key} = {_format_value(value, meta.get('secret', False))}"
            ))

        for key in unset_keys:
            meta = get_meta(key)
            if not meta:
                raise CommandError(f"未知配置项: {key!r}")
            result = _upsert(key, meta["default"], meta)
            self.stdout.write(self.style.WARNING(
                f"  [{result}] {key} = {_format_value(meta['default'], meta.get('secret', False))} (重置为默认)"
            ))

    def _handle_wizard(self) -> None:
        """交互式 wizard：按 DEFAULT_CONFIGS 顺序询问，回车保留当前值"""
        self.stdout.write(self.style.HTTP_INFO(
            "\n=== 平台配置 wizard ==="
        ))
        self.stdout.write("直接回车保留当前值；按 Ctrl+C 中止。\n")

        last_cat = None
        for item in DEFAULT_CONFIGS:
            key = item["key"]
            description = item.get("description", "")
            secret = item.get("secret", False)
            category = item["category"]
            default = item["default"]

            if category != last_cat:
                self.stdout.write(self.style.HTTP_INFO(f"\n[{category}]"))
                last_cat = category

            current = PlatformConfig.get_value(key, default)
            display_current = _format_value(current, secret)
            prompt = f"  {key} ({description}) [{display_current}]: "

            try:
                if secret:
                    raw = getpass.getpass(prompt)
                else:
                    raw = input(prompt)
            except EOFError:
                self.stdout.write("\n（无 stdin，跳过 wizard，使用 --set 或 --init 代替）")
                return

            raw = raw.strip()
            if raw == "":
                continue

            try:
                value = _coerce(raw, default)
            except CommandError as e:
                self.stdout.write(self.style.ERROR(f"    × {e}, 保留原值"))
                continue

            result = _upsert(key, value, item)
            self.stdout.write(self.style.SUCCESS(
                f"    [{result}] {key} = {_format_value(value, secret)}"
            ))

        self.stdout.write(self.style.SUCCESS("\n配置完成。"))
