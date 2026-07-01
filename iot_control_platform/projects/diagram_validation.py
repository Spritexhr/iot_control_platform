"""P&ID 画布 JSON 的结构与房间资源边界校验。"""
from __future__ import annotations

import math

from rest_framework import serializers


NODE_TYPES = {
    "instrument", "device_indicator", "control_indicator",
    "vessel", "storage_tank", "column", "pump", "compressor", "mixer",
    "heat_exchanger", "filter", "valve", "label", "stream_inlet", "stream_outlet",
}
HANDLE_IDS = {"left", "right", "top", "bottom"}
EDGE_KINDS = {"process", "utility", "signal"}
BINDING_NODE_TYPES = {
    "sensor": {"instrument"},
    "device": {"device_indicator"},
    "automation_rule": {"control_indicator"},
    "control_scheme": {"control_indicator"},
}


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _validate_point(point, label):
    if not isinstance(point, dict) or not _is_number(point.get("x")) or not _is_number(point.get("y")):
        raise serializers.ValidationError(f"{label}必须包含有限数值 x/y")


def _section_resource_ids(section):
    sensor_ids = set()
    for member in section.sensor_members.select_related("sensor"):
        sensor_ids.add(member.point_id)
    device_ids = set(section.device_members.values_list("device__device_id", flat=True))

    from automation.models import AutomationRule, ControlScheme

    automation_rule_ids = {
        str(value) for value in AutomationRule.objects.filter(
            project_id=section.project_id, section_id=section.id,
        ).values_list("id", flat=True)
    }
    control_scheme_ids = {
        str(value) for value in ControlScheme.objects.filter(
            project_id=section.project_id, section_id=section.id,
        ).values_list("id", flat=True)
    }
    return {
        "sensor": {str(value) for value in sensor_ids},
        "device": {str(value) for value in device_ids},
        "automation_rule": automation_rule_ids,
        "control_scheme": control_scheme_ids,
    }


def validate_diagram_config(config, section):
    """校验并返回 diagram canvas。空对象表示尚未编辑的新视图。"""
    if not isinstance(config, dict):
        raise serializers.ValidationError("P&ID config 必须是 JSON 对象")
    if not config:
        return config

    version = config.get("version", 1)
    if version != 1:
        raise serializers.ValidationError(f"不支持的 P&ID canvas version: {version}")
    nodes = config.get("nodes")
    edges = config.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        raise serializers.ValidationError("P&ID config.nodes/config.edges 必须是数组")
    viewport = config.get("viewport")
    if viewport is not None:
        if not isinstance(viewport, dict) or not all(
            _is_number(viewport.get(key)) for key in ("x", "y", "zoom")
        ):
            raise serializers.ValidationError("P&ID viewport 必须包含有限数值 x/y/zoom")
        if viewport["zoom"] <= 0:
            raise serializers.ValidationError("P&ID viewport.zoom 必须大于 0")

    resources = _section_resource_ids(section)
    node_ids = set()
    for index, node in enumerate(nodes):
        prefix = f"nodes[{index}]"
        if not isinstance(node, dict):
            raise serializers.ValidationError(f"{prefix}必须是对象")
        node_id = node.get("id")
        if not isinstance(node_id, str) or not node_id:
            raise serializers.ValidationError(f"{prefix}.id 必须是非空字符串")
        if node_id in node_ids:
            raise serializers.ValidationError(f"节点 id 重复: {node_id}")
        node_ids.add(node_id)
        node_type = node.get("type")
        if node_type not in NODE_TYPES:
            raise serializers.ValidationError(f"{prefix}.type 不受支持: {node_type}")
        _validate_point(node.get("position"), f"{prefix}.position")
        size = node.get("size")
        if size is not None and (
            not isinstance(size, dict)
            or not _is_number(size.get("w")) or not _is_number(size.get("h"))
            or size["w"] <= 0 or size["h"] <= 0
        ):
            raise serializers.ValidationError(f"{prefix}.size 必须包含正数 w/h")

        binding = node.get("binding") or {"kind": "none", "id": ""}
        if not isinstance(binding, dict):
            raise serializers.ValidationError(f"{prefix}.binding 必须是对象")
        kind = binding.get("kind", "none")
        if kind == "none":
            continue
        if kind not in BINDING_NODE_TYPES:
            raise serializers.ValidationError(f"{prefix}.binding.kind 不受支持: {kind}")
        if node_type not in BINDING_NODE_TYPES[kind]:
            raise serializers.ValidationError(f"{node_type} 不能绑定 {kind}")
        binding_id = str(binding.get("id", ""))
        if not binding_id or binding_id not in resources[kind]:
            raise serializers.ValidationError(f"{prefix}.binding 不属于当前房间: {kind}:{binding_id}")

    edge_ids = set()
    for index, edge in enumerate(edges):
        prefix = f"edges[{index}]"
        if not isinstance(edge, dict):
            raise serializers.ValidationError(f"{prefix}必须是对象")
        edge_id = edge.get("id")
        if not isinstance(edge_id, str) or not edge_id:
            raise serializers.ValidationError(f"{prefix}.id 必须是非空字符串")
        if edge_id in edge_ids:
            raise serializers.ValidationError(f"连线 id 重复: {edge_id}")
        edge_ids.add(edge_id)
        if edge.get("source") not in node_ids or edge.get("target") not in node_ids:
            raise serializers.ValidationError(f"{prefix}引用了不存在的节点")
        source_port = edge.get("sourcePort", edge.get("sourceHandle", "right"))
        target_port = edge.get("targetPort", edge.get("targetHandle", "left"))
        if source_port not in HANDLE_IDS or target_port not in HANDLE_IDS:
            raise serializers.ValidationError(f"{prefix}包含无效连接点")
        data = edge.get("data") or {}
        if not isinstance(data, dict) or data.get("kind", "process") not in EDGE_KINDS:
            raise serializers.ValidationError(f"{prefix}.data.kind 无效")

    return config
