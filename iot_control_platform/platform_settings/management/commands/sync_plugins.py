"""
同步 plugins/ 目录到 platform_settings.Plugin 表
- 新发现的插件按清单 enabled 默认值登记
- 已登记的插件保留 enabled 状态，仅刷新 version/description
- --prune 选项移除文件系统中已不存在的插件登记
"""
import logging

from django.core.management.base import BaseCommand

from plugins import discover_plugins
from platform_settings.models import Plugin

logger = logging.getLogger("platform_settings")


class Command(BaseCommand):
    help = "扫描 plugins/ 目录并同步插件清单到 Plugin 表"

    def add_arguments(self, parser):
        parser.add_argument(
            "--prune",
            action="store_true",
            help="删除文件系统中不存在的插件登记记录",
        )

    def handle(self, *args, **options):
        prune = options["prune"]

        discovered = discover_plugins()
        discovered_names = {p.name for p in discovered}

        self.stdout.write(f"发现 {len(discovered)} 个插件: {sorted(discovered_names) or '（无）'}")

        created = 0
        refreshed = 0

        for meta in discovered:
            obj, was_created = Plugin.objects.get_or_create(
                name=meta.name,
                defaults={
                    "enabled": meta.enabled,
                    "version": meta.version,
                    "description": meta.description,
                },
            )
            if was_created:
                created += 1
                logger.info(f"插件登记: {meta.name} (enabled={meta.enabled})")
                self.stdout.write(self.style.SUCCESS(f"  + 登记: {meta.name} v{meta.version}"))
                continue

            # 已存在 - 仅同步 version/description，保留 enabled 用户决策
            changed = False
            if obj.version != meta.version:
                obj.version = meta.version
                changed = True
            if obj.description != meta.description:
                obj.description = meta.description
                changed = True
            if changed:
                obj.save(update_fields=["version", "description", "updated_at"])
                refreshed += 1
                self.stdout.write(self.style.WARNING(f"  ~ 刷新: {meta.name} v{meta.version}"))
            else:
                self.stdout.write(f"  = 已是最新: {meta.name}")

        pruned = 0
        if prune:
            stale = Plugin.objects.exclude(name__in=discovered_names)
            for obj in stale:
                self.stdout.write(self.style.ERROR(f"  - 移除: {obj.name}"))
                obj.delete()
                pruned += 1

        summary = f"完成: 新增 {created}，刷新 {refreshed}，移除 {pruned}"
        logger.info(summary)
        self.stdout.write(self.style.SUCCESS(f"\n{summary}"))
