"""
平台默认配置常量
是 PlatformConfig 表的"种子值"——首次部署或新增配置项时，由 configure --init 写入。
所有运行期可调配置都列在这里，wizard 也以此为唯一信源。

字段语义：
- key:         PlatformConfig.key（小写下划线）
- default:     默认值，python 原生类型（str/int/float/list/dict/bool）
- category:    分组，便于 admin 列表排序
- description: 中文描述，wizard 提示也用它
- secret:      True 表示 wizard 输入时不回显（如密码）
- value_type:  显式声明类型，wizard 转换时使用；省略时按 default 推断
"""
from typing import Any, List, Dict


DEFAULT_CONFIGS: List[Dict[str, Any]] = [
    # ========== MQTT ==========
    {
        "key": "mqtt_broker",
        "default": "127.0.0.1",
        "category": "mqtt",
        "description": "MQTT/EMQX 服务器地址",
    },
    {
        "key": "mqtt_port",
        "default": 1883,
        "category": "mqtt",
        "description": "MQTT 端口（EMQX 标准端口 1883）",
    },
    {
        "key": "mqtt_keepalive",
        "default": 60,
        "category": "mqtt",
        "description": "MQTT 保活间隔（秒）",
    },
    {
        "key": "mqtt_username",
        "default": "",
        "category": "mqtt",
        "description": "MQTT 用户名（可选，留空表示匿名连接）",
    },
    {
        "key": "mqtt_password",
        "default": "",
        "category": "mqtt",
        "description": "MQTT 密码（可选，留空表示无密码）",
        "secret": True,
    },

    # ========== 设备 ==========
    {
        "key": "device_offline_timeout",
        "default": 300,
        "category": "devices",
        "description": "设备离线判定超时（秒），无心跳则视为离线",
    },
    {
        "key": "device_reconnect_attempts",
        "default": 3,
        "category": "devices",
        "description": "设备重连尝试次数",
    },
    {
        "key": "device_reconnect_interval",
        "default": 10,
        "category": "devices",
        "description": "设备重连间隔（秒）",
    },

    # ========== 数据留存 ==========
    {
        "key": "sensor_data_retention_days",
        "default": 30,
        "category": "data_retention",
        "description": "传感器数据保留天数，超过则清理",
    },
    {
        "key": "device_data_retention_days",
        "default": 30,
        "category": "data_retention",
        "description": "设备状态数据保留天数，超过则清理",
    },
]


def get_default(key: str, fallback: Any = None) -> Any:
    """根据 key 查找默认值"""
    for item in DEFAULT_CONFIGS:
        if item["key"] == key:
            return item["default"]
    return fallback


def get_meta(key: str) -> Dict[str, Any]:
    """根据 key 查找完整 meta（含 description / category / secret）"""
    for item in DEFAULT_CONFIGS:
        if item["key"] == key:
            return dict(item)
    return {}
