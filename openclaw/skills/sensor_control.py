"""
OpenClaw 技能：传感器控制 (基于 API 请求)
用于向传感器发送控制指令（如设置心跳间隔、校准等）
"""
import logging
from ..api_client import api_client

logger = logging.getLogger(__name__)

def control_sensor(sensor_name, command_name, params=None):
    """
    通过 API 向传感器发送控制指令
    :param sensor_name: 传感器名称或 ID 关键词
    :param command_name: 指令名称（需符合 SensorType 中定义的 commands）
    :param params: 指令参数字典（可选）
    :return: 结果描述字符串
    """
    try:
        # 1. 搜索传感器获取 ID
        response = api_client.get("/sensors/", params={"search": sensor_name})
        search_results = response.get("results") if isinstance(response, dict) and "results" in response else response

        if not search_results or len(search_results) == 0:
            return f"找不到名为 '{sensor_name}' 的传感器。"
        
        sensor_data = search_results[0]
        sensor_id = sensor_data["sensor_id"]
        actual_name = sensor_data["name"]

        # 2. 发送 POST 指令到 /api/sensors/{sensor_id}/command/
        endpoint = f"/sensors/{sensor_id}/command/"
        payload = {
            "command_name": command_name,
            "params": params or {}
        }
        
        response = api_client.post(endpoint, data=payload)
        
        if response and response.get("success"):
            return f"已成功为传感器 {actual_name} 下发指令: {command_name}。"
        else:
            detail = response.get("detail", "未知错误") if response else "无法连接 API"
            return f"向传感器 {actual_name} 下发指令失败: {detail}"

    except Exception as e:
        logger.error(f"OpenClaw 传感器控制异常: {e}")
        return f"执行传感器控制时出错: {str(e)}"

# 意图定义
SKILL_INTENTS = {
    "sensor_control": {
        "function": control_sensor,
        "name": "iot_sensor_control",
        "description": "控制传感器参数（如设置上报频率、校准等）。",
        "parameters": {
            "sensor_name": {
                "type": "string",
                "description": "传感器名称或 ID，例如 '旋转传感器001'"
            },
            "command_name": {
                "type": "string",
                "description": "指令名称，具体请查阅传感器支持的 commands 列表"
            },
            "params": {
                "type": "object",
                "description": "指令所需的参数字典"
            }
        }
    }
}
