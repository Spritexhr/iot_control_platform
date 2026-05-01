"""
插件系统 - 自动发现 plugins/ 目录下的 Django app 形式插件

约定：
- 每个子目录是一个独立的 Django app
- 子目录根下需要一份 plugin.json 清单文件
- 子目录内需要标准的 Django app 结构（apps.py / urls.py 等）

启用规则：
- discover_plugins() 仅做文件系统扫描，不依赖数据库
- enabled_plugin_names() 优先读 platform_settings.Plugin 表；
  表不可用（首次 migrate 前）时回退到清单的 enabled 默认值
"""
import json
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

PLUGINS_DIR = Path(__file__).resolve().parent
MANIFEST_FILENAME = "plugin.json"


@dataclass
class PluginMeta:
    """插件清单 - 来自 plugin.json 的描述信息"""
    name: str           # 插件唯一标识，与目录名一致
    version: str        # 语义化版本，如 "0.1.0"
    description: str    # 简短描述
    enabled: bool       # 默认是否启用（首次 sync 时写入 DB）
    path: Path          # 插件目录绝对路径

    @property
    def app_label(self) -> str:
        """Django app 完整路径，用于 INSTALLED_APPS"""
        return f"plugins.{self.name}"

    @property
    def url_module(self) -> str:
        """插件的 urls 模块路径"""
        return f"plugins.{self.name}.urls"


def discover_plugins() -> list[PluginMeta]:
    """
    扫描 plugins/ 子目录，返回所有合法插件的清单
    合法条件：目录名不以 _ 或 . 开头，且包含 plugin.json
    """
    plugins: list[PluginMeta] = []
    if not PLUGINS_DIR.exists():
        return plugins

    for entry in sorted(PLUGINS_DIR.iterdir()):
        if not entry.is_dir():
            continue
        if entry.name.startswith(("_", ".")):
            continue
        manifest_path = entry / MANIFEST_FILENAME
        if not manifest_path.exists():
            continue

        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"插件 {entry.name} 的 plugin.json 解析失败: {e}")
            continue

        plugins.append(
            PluginMeta(
                name=str(data.get("name") or entry.name),
                version=str(data.get("version") or "0.0.0"),
                description=str(data.get("description") or ""),
                enabled=bool(data.get("enabled", True)),
                path=entry,
            )
        )
    return plugins


def enabled_plugin_names() -> set[str]:
    """
    返回当前启用的插件名集合
    优先读 DB；DB 不可用时使用清单默认值
    """
    discovered = discover_plugins()
    discovered_by_name = {p.name: p for p in discovered}

    try:
        # 延迟导入：settings 加载阶段不要触发 ORM
        from platform_settings.models import Plugin  # noqa: WPS433
        db_states = {p.name: p.enabled for p in Plugin.objects.all()}
    except Exception:
        # 表不存在 / DB 未就绪 / 应用未加载 - 回退到清单默认值
        return {p.name for p in discovered if p.enabled}

    enabled: set[str] = set()
    for name, meta in discovered_by_name.items():
        # DB 中有记录则以 DB 为准，否则用清单默认
        enabled_flag = db_states.get(name, meta.enabled)
        if enabled_flag:
            enabled.add(name)
    return enabled
