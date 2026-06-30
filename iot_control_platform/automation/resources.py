"""自动化脚本资源清单的格式校验与项目房间隔离。"""

from rest_framework import serializers


RESOURCE_TYPES = {"sensor": "Sensor", "device": "Device"}


class RuleResourceUnavailable(ValueError):
    """项目脚本引用了当前房间中已不可用的资源。"""


def normalize_device_list(device_list):
    """规范化脚本资源清单，并拒绝模糊或重复条目。"""
    if not isinstance(device_list, list):
        raise serializers.ValidationError("必须是资源条目数组")

    normalized = []
    seen = set()
    for index, item in enumerate(device_list):
        if not isinstance(item, dict):
            raise serializers.ValidationError(f"第 {index + 1} 项必须是对象")
        device_id = str(item.get("device_id") or "").strip()
        raw_type = str(item.get("device_type") or "").strip().lower()
        device_type = RESOURCE_TYPES.get(raw_type)
        if not device_id:
            raise serializers.ValidationError(f"第 {index + 1} 项缺少 device_id")
        if not device_type:
            raise serializers.ValidationError(f"第 {index + 1} 项 device_type 只能是 Sensor 或 Device")
        key = (device_type, device_id)
        if key in seen:
            raise serializers.ValidationError(f"资源 {device_id} 重复")
        seen.add(key)
        normalized.append({
            "device_id": device_id,
            "device_type": device_type,
            "name": str(item.get("name") or "").strip(),
        })
    return normalized


def unavailable_resources(device_list, section):
    """返回不属于指定房间的资源描述。"""
    if section is None:
        return []

    sensor_ids = set(
        section.sensor_members.values_list("sensor__sensor_id", flat=True)
    )
    device_ids = set(
        section.device_members.values_list("device__device_id", flat=True)
    )
    unavailable = []
    for item in device_list or []:
        device_id = item.get("device_id")
        device_type = item.get("device_type")
        allowed = sensor_ids if device_type == "Sensor" else device_ids
        if device_id not in allowed:
            unavailable.append(f"{device_type}:{device_id}")
    return unavailable


def validate_scoped_resources(device_list, section):
    """校验资源均已导入项目脚本所属房间。"""
    unavailable = unavailable_resources(device_list, section)
    if unavailable:
        raise serializers.ValidationError(
            "以下资源未导入当前房间：" + "、".join(unavailable)
        )


def effective_device_list(rule):
    """执行时重新核对成员，防止资源移出房间后脚本继续访问。"""
    device_list = rule.device_list if isinstance(rule.device_list, list) else []
    if not rule.section_id:
        return device_list
    unavailable = unavailable_resources(device_list, rule.section)
    if unavailable:
        raise RuleResourceUnavailable(
            "以下资源已不属于规则所在房间：" + "、".join(unavailable)
        )
    return device_list
