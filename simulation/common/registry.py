"""
节点模块自动发现 —— 取代 run.py 中手写的 import + REGISTRY 字典

约定：simulation/sensors/ 和 simulation/devices/ 下，每个子目录就是一个节点模块，
目录名 == 模块文件名（如 sensors/flow_sensor/flow_sensor.py），模块内定义恰好
一个 MqttNode 具体子类（NODE_TYPE 非空）。满足约定即被自动注册，注册键 = 目录名。

新增节点只需两步：建目录写类 → 在 manifest/webui 里引用，无需再改 run.py。

导入失败的模块不会拖垮整个发现过程：记入 DISCOVERY_ERRORS，
当 manifest 真正引用到它时再报具体的 import 错误。
"""
import importlib
import logging
import os
import sys
from typing import Dict, Tuple, Type

SIMULATION_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SIMULATION_DIR not in sys.path:
    sys.path.insert(0, SIMULATION_DIR)

from common.mqtt_node import MqttNode

log = logging.getLogger(__name__)

NODE_PACKAGES = ("sensors", "devices")

# 最近一次 discover_registry() 中导入失败的模块：{目录名: 错误描述}
DISCOVERY_ERRORS: Dict[str, str] = {}


def _find_node_class(module, module_path: str) -> Type[MqttNode]:
    """在模块中找出定义于该模块（而非 import 进来）的 MqttNode 具体子类"""
    candidates = [
        obj for obj in vars(module).values()
        if isinstance(obj, type)
        and issubclass(obj, MqttNode)
        and obj is not MqttNode
        and obj.__module__ == module_path
        and getattr(obj, "NODE_TYPE", "")
    ]
    if not candidates:
        raise ValueError("模块中没有定义 MqttNode 子类（NODE_TYPE 非空）")
    if len(candidates) > 1:
        names = [c.__name__ for c in candidates]
        log.warning(f"模块 {module_path} 定义了多个节点类 {names}，使用第一个 {names[0]}")
    return candidates[0]


def discover_registry() -> Dict[str, Type[MqttNode]]:
    """扫描 sensors/ devices/ 子目录，返回 {目录名: 节点类}"""
    registry: Dict[str, Type[MqttNode]] = {}
    DISCOVERY_ERRORS.clear()

    for pkg in NODE_PACKAGES:
        pkg_dir = os.path.join(SIMULATION_DIR, pkg)
        if not os.path.isdir(pkg_dir):
            continue
        for name in sorted(os.listdir(pkg_dir)):
            sub_dir = os.path.join(pkg_dir, name)
            module_file = os.path.join(sub_dir, f"{name}.py")
            if not os.path.isfile(module_file):
                continue
            module_path = f"{pkg}.{name}.{name}"
            try:
                module = importlib.import_module(module_path)
                cls = _find_node_class(module, module_path)
            except Exception as e:
                DISCOVERY_ERRORS[name] = f"{type(e).__name__}: {e}"
                log.warning(f"✗ 跳过节点模块 {module_path}: {e}")
                continue
            if name in registry:
                log.warning(f"⚠ 节点模块名重复: {name}（{pkg} 覆盖了先前的注册）")
            registry[name] = cls

    return registry


def registry_summary(registry: Dict[str, Type[MqttNode]]) -> str:
    """启动日志用：按类型分组列出已发现的模块"""
    parts: Tuple[list, list] = ([], [])
    for name, cls in registry.items():
        parts[0 if cls.NODE_TYPE == "sensor" else 1].append(name)
    return (
        f"已发现 {len(registry)} 个节点模块 — "
        f"传感器: {', '.join(parts[0]) or '无'}；设备: {', '.join(parts[1]) or '无'}"
    )
