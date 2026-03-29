"""
OpenClaw 技能：设备控制 (基于 API 请求)
通过网络调用 IoT 平台的 REST 接口执行操作
"""
import logging
from ..api_client import api_client

logger = logging.getLogger(__name__)

def control_device(device_name, command_name, params=None):
    """
    通过 API 控制设备动作
    :param device_name: 设备名称或 ID 的关键词
    :param command_name: 动作名称（如 "turn_on"）
    :param params: 命令参数（字典）
    :return: 结果描述字符串
    """
    try:
        # 1. 搜索设备以获取 ID (lookup_field 为 device_id)
        response = api_client.get("/devices/", params={"search": device_name})
        
        # 兼容分页逻辑
        search_results = response.get("results") if isinstance(response, dict) and "results" in response else response

        if not search_results or len(search_results) == 0:
            return f"API 查询不到名为 '{device_name}' 的设备。"
        
        # 匹配最接近的一个
        device_data = search_results[0]
        device_id = device_data["device_id"]
        actual_name = device_data["name"]

        # 2. 发送 POST 指令到 /api/devices/{device_id}/command/
        endpoint = f"/devices/{device_id}/command/"
        payload = {
            "command_name": command_name,
            "params": params or {}
        }
        
        response = api_client.post(endpoint, data=payload)
        
        if response and response.get("success"):
            return f"已成功通过网络为 {actual_name} 发送 {command_name} 指令。"
        else:
            detail = response.get("detail", "未知错误") if response else "无法连接 API"
            return f"为 {actual_name} 发送指令失败: {detail}"

    except Exception as e:
        logger.error(f"OpenClaw 技能异常: {e}")
        return f"执行网络操作时出错: {str(e)}"

# 意图定义 (供 OpenClaw 核心框架进行 Tool Discovery)
SKILL_INTENTS = {
    "device_control": {
        "function": control_device,
        "name": "iot_device_control",
        "description": "控制物联网设备的开关、引脚电平或上报频率。支持模糊搜索设备名称。",
        "parameters": {
            "device_name": {
                "type": "string",
                "description": "设备名称或 ID，例如 'potential_controler_001' 或 '灯'"
            },
            "command_name": {
                "type": "string",
                "description": "动作指令。常用指令包括：'high'(拉高引脚), 'low'(拉低引脚), 'high_all'(开启全部), 'low_all'(关闭全部), 'set_status_interval'(设置心跳间隔)"
            },
            "params": {
                "type": "object",
                "description": "指令参数字典。'high'/'low' 指令需传 {'pin': 'D5/D6/D7'}；'set_status_interval' 指令需传 {'val': 30-600}"
            }
        },
        "examples": [
            "帮我把 potential_controler_001 的 D5 灯打开",
            "关闭所有的灯光",
            "将控制器的上报间隔设置为 60 秒"
        ]
    }
}
