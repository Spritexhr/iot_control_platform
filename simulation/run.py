"""
虚拟节点统一启动器

读取 config.yaml 拿 broker 配置，按 --manifest 加载一个或多个清单（manifests/*.yaml），
为每个节点起一个线程，每个节点有独立 MQTT client（client_id 唯一）。
节点 .py 也可单独 `python simulation/sensors/xxx.py --id ...` 运行。

节点模块由 common/registry.py 自动发现（扫描 sensors/ devices/ 子目录），
新增节点不再需要修改本文件。

用法：
  python run.py                                # 加载 manifests/default.yaml
  python run.py -m default -m eb_plant         # 同时加载多份清单
  python run.py -m ./path/to/custom.yaml       # 直接指定清单文件路径
  python run.py --check -m default             # 只校验清单不启动
"""
import argparse
import logging
import os
import signal
import sys
import threading
from typing import List, Tuple

import yaml

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MANIFEST_DIR = os.path.join(BASE_DIR, "manifests")

sys.path.insert(0, BASE_DIR)

from common.mqtt_node import MqttNode
from common.registry import DISCOVERY_ERRORS, discover_registry, registry_summary
from common.schema import validate_entry

log = logging.getLogger(__name__)

# 节点模块注册表：清单里 module 字段 -> 类（自动发现，键 = 目录名）
REGISTRY = discover_registry()


def build_node(entry: dict, broker: dict) -> MqttNode:
    module = entry.get("module")
    cls = REGISTRY.get(module)
    if cls is None:
        raise ValueError(f"未知节点模块 '{module}'，可选: {list(REGISTRY.keys())}")

    node_id = entry.get("id")
    if not node_id:
        raise ValueError(f"节点配置缺少 id 字段: {entry}")

    # 鉴权：节点级覆盖 > broker 级默认（复刻每台 .ino 独立 credentials 的能力）
    username = entry.get("username", broker.get("username", ""))
    password = entry.get("password", broker.get("password", ""))

    # 其余字段作为构造参数透传（剔除已显式处理的字段，避免重复传参）
    reserved = {"module", "id", "username", "password"}
    extra_kwargs = {k: v for k, v in entry.items() if k not in reserved}

    return cls(
        node_id=node_id,
        broker=broker["host"],
        port=broker.get("port", 1883),
        username=username,
        password=password,
        **extra_kwargs,
    )


def _resolve_manifest_path(name: str) -> str:
    """`default` -> manifests/default.yaml；带 / 或 .yaml 后缀的当成文件路径。"""
    if os.sep in name or name.endswith((".yaml", ".yml")):
        return name if os.path.isabs(name) else os.path.join(BASE_DIR, name)
    return os.path.join(MANIFEST_DIR, f"{name}.yaml")


def _load_manifest(path: str) -> dict:
    if not os.path.isfile(path):
        raise FileNotFoundError(f"清单文件不存在: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if "nodes" not in data or not isinstance(data["nodes"], list):
        raise ValueError(f"清单 {path} 缺少 nodes 列表")
    return data


def collect_nodes(manifest_names: List[str]) -> List[Tuple[str, dict]]:
    """
    加载并合并所有清单的 nodes，返回 [(origin, entry), ...]。
    origin 形如 "清单 'st_plant' 第 3 个节点"，供校验错误定位。
    同名 (module, id) 组合检测重复并报错。
    """
    all_nodes: List[Tuple[str, dict]] = []
    seen = {}  # (module, id) -> manifest_name
    for name in manifest_names:
        path = _resolve_manifest_path(name)
        manifest = _load_manifest(path)
        display = manifest.get("name") or os.path.basename(path)
        desc = manifest.get("description", "")
        node_count = len(manifest["nodes"])
        log.info(f"加载清单: {display} ({node_count} 节点) {('- ' + desc) if desc else ''}")
        for i, entry in enumerate(manifest["nodes"], start=1):
            key = (entry.get("module"), entry.get("id"))
            if key in seen:
                raise ValueError(
                    f"清单 '{display}' 与 '{seen[key]}' 包含重复节点 module={key[0]} id={key[1]}"
                )
            seen[key] = display
            all_nodes.append((f"清单 '{display}' 第 {i} 个节点", entry))
    return all_nodes


def validate_entries(entries: List[Tuple[str, dict]]) -> bool:
    """
    逐节点按 PARAMS_SCHEMA 聚合校验，一次性输出所有错误。
    返回是否全部通过（warning 不算失败）。
    """
    ok = True
    for origin, entry in entries:
        module = entry.get("module")
        node_id = entry.get("id") or "?"
        where = f"{origin} ({module} / {node_id})"

        if not module:
            log.error(f"✗ {where}: 缺少 module 字段")
            ok = False
            continue
        if not entry.get("id"):
            log.error(f"✗ {where}: 缺少 id 字段")
            ok = False

        cls = REGISTRY.get(module)
        if cls is None:
            if module in DISCOVERY_ERRORS:
                log.error(
                    f"✗ {where}: 模块 '{module}' 导入失败 — {DISCOVERY_ERRORS[module]}"
                )
            else:
                log.error(
                    f"✗ {where}: 未知节点模块 '{module}'，可选: {list(REGISTRY.keys())}"
                )
            ok = False
            continue

        errors, warnings = validate_entry(cls, entry)
        for w in warnings:
            log.warning(f"⚠ {where}: {w}")
        for e in errors:
            log.error(f"✗ {where}: {e}")
        if errors:
            ok = False
    return ok


def main():
    parser = argparse.ArgumentParser(description="批量启动虚拟 IoT 节点")
    parser.add_argument(
        "--config",
        default=os.path.join(BASE_DIR, "config.yaml"),
        help="broker 配置文件（包含 broker 段）。默认: simulation/config.yaml",
    )
    parser.add_argument(
        "--manifest", "-m",
        action="append",
        default=None,
        help="清单名（manifests/<name>.yaml）或文件路径，可重复指定。默认: default",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="只校验清单（不连 broker、不启动节点），校验失败退出码 1",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    log.info(registry_summary(REGISTRY))

    manifest_names = args.manifest if args.manifest else ["default"]
    try:
        entries = collect_nodes(manifest_names)
    except (FileNotFoundError, ValueError) as e:
        log.error(f"加载清单失败: {e}")
        sys.exit(1)

    if not entries:
        log.error("清单中没有任何节点，退出")
        sys.exit(1)

    if not validate_entries(entries):
        log.error("清单校验未通过，请修正以上错误后重试")
        sys.exit(1)

    if args.check:
        log.info(f"✓ 校验通过：共 {len(entries)} 个节点")
        return

    with open(args.config, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    broker = cfg.get("broker") or {}
    if not broker.get("host"):
        log.error(f"{args.config} 缺少 broker.host")
        sys.exit(1)

    # 向后兼容：旧 config.yaml 里若仍残留 nodes 段，给出迁移提示但不再使用
    if cfg.get("nodes"):
        log.warning(
            f"{args.config} 仍包含 nodes 段，但现在节点列表由 manifests/*.yaml 管理；"
            f"该段已被忽略。请将节点搬到 manifests/ 下并删除 config.yaml 的 nodes。"
        )

    nodes: List[MqttNode] = []
    threads: List[threading.Thread] = []

    for _origin, entry in entries:
        try:
            node = build_node(entry, broker)
        except Exception as e:
            log.error(f"✗ 构建节点失败: {entry} -> {e}")
            continue
        t = threading.Thread(target=node.run, name=f"node-{node.node_id}", daemon=True)
        nodes.append(node)
        threads.append(t)
        t.start()
        log.info(f"已启动: {entry['module']} id={node.node_id}")

    if not nodes:
        log.error("没有任何节点启动，退出")
        sys.exit(1)

    log.info(f"共启动 {len(nodes)} 个虚拟节点。Ctrl-C 退出。")

    stop_event = threading.Event()

    def _shutdown(signum, frame):
        log.info(f"收到信号 {signum}，停止所有节点…")
        stop_event.set()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    stop_event.wait()
    for n in nodes:
        n.stop()
    for t in threads:
        t.join(timeout=5)


if __name__ == "__main__":
    main()
