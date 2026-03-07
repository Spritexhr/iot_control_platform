"""
配置读取辅助模块
仅从 platform_settings 数据库读取，防止多来源混乱
"""
from typing import Any, TypeVar

T = TypeVar("T")


def _coerce(value: Any, target_type: type, default: T) -> T:
    """将值转换为目标类型"""
    if value is None or value == "":
        return default
    if target_type == bool:
        if isinstance(value, bool):
            return value
        return str(value).lower() in ("true", "1", "yes")
    if target_type == int:
        return int(value) if value is not None else default
    if target_type == float:
        return float(value) if value is not None else default
    return str(value) if target_type == str else value


def get_config(key: str, default: T, value_type: type = str) -> T:
    """
    仅从 platform_settings 数据库读取配置，不存在时返回 default

    Args:
        key: PlatformConfig 的 key
        default: 默认值（数据库无此 key 时返回）
        value_type: 目标类型 str/int/bool/float

    Returns:
        配置值
    """
    try:
        from platform_settings.models import PlatformConfig

        val = PlatformConfig.get_value(key)
        if val is not None:
            return _coerce(val, value_type, default)
    except Exception:
        pass

    return default
