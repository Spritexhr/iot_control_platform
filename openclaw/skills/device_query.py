"""
OpenClaw 技能：设备状态查询 (基于 API 请求)
用于获取物联网执行器（如电位控制器、开关）上报的最新状态数据
"""
import logging
from ..api_client import api_client

logger = logging.getLogger(__name__)

def query_device_data(device_name):
    """
    通过 API 查询设备的最新状态数据
    :param device_name: 设备名称或 ID 关键词
    :return: 结果描述字符串
    """
    try:
        # 1. 在设备模块中搜索
        response = api_client.get("/devices/", params={"search": device_name})
        
        # 兼容分页逻辑
        search_results = response.get("results") if isinstance(response, dict) and "results" in response else response

        if not search_results or len(search_results) == 0:
            return f"API 在设备列表中找不到名为 '{device_name}' 的设备。"
        
        device_data = search_results[0]
        device_id = device_data["device_id"]
        actual_name = device_data["name"]

        # 2. 获取设备的状态记录 (GET /api/devices/{device_id}/status/)
        endpoint = f"/devices/{device_id}/status/"
        # 获取最近 1 小时的 1 条最新记录
        history = api_client.get(endpoint, params={"hours": 1, "limit": 1})

        if not history or len(history) == 0:
            return f"API 返回设备 {actual_name} 目前没有上报的状态数据。"

        latest = history[0]
        # 后端 DeviceStatusCollection 模型中的字段名为 'data'
        business_data = latest.get("data", {})
        time_str = latest.get("timestamp", "未知时间")
        
        if not business_data:
            # 如果 data 为空，显示设备的基础在线信息
            is_online = "在线" if device_data.get("is_online") else "离线"
            return f"设备 {actual_name} 目前在线状态为 [{is_online}]，但尚未上报具体的业务数据（最后上报时间: {time_str}）。"

        # 格式化数据内容
        data_info = " | ".join([f"{k}: {v}" for k, v in business_data.items()])
        return f"设备 {actual_name} 在 {time_str} 上报的状态参数如下：\n   >>> {data_info}"

    except Exception as e:
        logger.error(f"OpenClaw 设备查询异常: {e}")
        return f"执行设备 API 查询时出错: {str(e)}"

# 意图定义
SKILL_INTENTS = {
    "device_query": {
        "function": query_device_data,
        "name": "iot_device_status_query",
        "description": "查询执行器设备（如电位控制器、智能开关）当前的实时状态或上报参数。",
        "parameters": {
            "device_name": {
                "type": "string",
                "description": "设备名称或 ID，例如 'potential_controler_001'"
            }
        }
    }
}
