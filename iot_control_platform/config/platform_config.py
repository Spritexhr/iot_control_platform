"""
配置读取辅助模块
优先从 platform_settings 读取，不存在或异常时回退到环境变量
"""
import os
from typing import Any, Optional, TypeVar

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


def get_config(
    key: str,
    env_key: str,
    default: T,
    value_type: type = str,
) -> T:
    """
    获取配置：优先 platform_settings，回退到环境变量

    Args:
        key: PlatformConfig 的 key
        env_key: 环境变量名
        default: 默认值
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

    env_val = os.environ.get(env_key)
    if env_val is None or env_val == "":
        return default
    return _coerce(env_val, value_type, default)
