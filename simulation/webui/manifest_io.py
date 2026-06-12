"""
DB ↔ manifest YAML 双向转换 —— 四条路径共用本模块：
  1. 导入：上传 manifests/*.yaml → 建组 + 节点（含校验报告）
  2. 导出：组 → manifest YAML 下载（可直接 `python run.py -m <文件>` 跑）
  3. 启动渲染：组 → runtime/manifest_run_<id>.yaml + config_run_<id>.yaml，spawn run.py
  4. 校验：节点 entry 复用 run.py 同款 schema 校验
"""
import os
import sys
from typing import List, Optional, Tuple

import yaml

SIMULATION_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SIMULATION_DIR not in sys.path:
    sys.path.insert(0, SIMULATION_DIR)

from common.registry import DISCOVERY_ERRORS, discover_registry
from common.schema import RESERVED_ENTRY_KEYS, module_meta, validate_entry

# 进程级注册表（webui 启动时发现一次）
REGISTRY = discover_registry()


def modules_meta() -> List[dict]:
    """/api/meta/modules 输出"""
    return [module_meta(name, cls) for name, cls in REGISTRY.items()]


def node_to_entry(node: dict) -> dict:
    """DB 节点行 → manifest entry"""
    entry = {"module": node["module"], "id": node["node_id"]}
    if node.get("username"):
        entry["username"] = node["username"]
    if node.get("password"):
        entry["password"] = node["password"]
    entry.update(node.get("params") or {})
    return entry


def entry_to_node(entry: dict) -> dict:
    """manifest entry → DB 节点字段（create_node 的 data 参数）"""
    params = {k: v for k, v in entry.items() if k not in RESERVED_ENTRY_KEYS}
    return {
        "module": entry.get("module", ""),
        "node_id": entry.get("id", ""),
        "username": entry.get("username"),
        "password": entry.get("password"),
        "params": params,
        "enabled": True,
    }


def validate_node(module: str, entry: dict) -> Tuple[List[str], List[str]]:
    """校验一条 entry，返回 (errors, warnings)；模块不存在也算 error"""
    cls = REGISTRY.get(module)
    if cls is None:
        if module in DISCOVERY_ERRORS:
            return [f"模块 '{module}' 导入失败 — {DISCOVERY_ERRORS[module]}"], []
        return [f"未知节点模块 '{module}'，可选: {list(REGISTRY.keys())}"], []
    return validate_entry(cls, entry)


def groups_to_manifest(groups: List[dict], nodes_by_group: dict) -> dict:
    """多个组（含各自节点）合并渲染成一份 manifest dict（enabled=False 的节点跳过）"""
    names = [g["name"] for g in groups]
    descs = [g["description"] for g in groups if g.get("description")]
    nodes = []
    for g in groups:
        for n in nodes_by_group.get(g["id"], []):
            if n.get("enabled", True):
                nodes.append(node_to_entry(n))
    return {
        "name": "+".join(names),
        "description": "；".join(descs),
        "nodes": nodes,
    }


def parse_manifest_yaml(text: str) -> dict:
    """解析上传的 manifest 文本，结构性错误抛 ValueError"""
    try:
        data = yaml.safe_load(text) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"YAML 解析失败: {e}")
    if not isinstance(data, dict) or not isinstance(data.get("nodes"), list):
        raise ValueError("清单缺少 nodes 列表")
    return data


def dump_manifest_yaml(manifest: dict) -> str:
    return yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False)


def dump_config_yaml(broker: dict) -> str:
    """broker profile → run.py --config 用的 config.yaml 内容"""
    return yaml.safe_dump({
        "broker": {
            "host": broker["host"],
            "port": broker.get("port", 1883),
            "username": broker.get("username", ""),
            "password": broker.get("password", ""),
        }
    }, allow_unicode=True, sort_keys=False)


def read_legacy_config() -> Optional[dict]:
    """读 simulation/config.yaml 的 broker 段（导入旧配置用），不存在返回 None"""
    path = os.path.join(SIMULATION_DIR, "config.yaml")
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    broker = cfg.get("broker")
    if not broker or not broker.get("host"):
        return None
    return broker
