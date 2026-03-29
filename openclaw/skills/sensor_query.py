"""
OpenClaw 技能：传感器查询 (基于 API 请求)
通过网络调用 IoT 平台的 REST 接口获取环境数据
"""
import logging
from ..api_client import api_client

logger = logging.getLogger(__name__)

def query_sensor(sensor_name):
    """
    通过 API 查询传感器最新数值
    :param sensor_name: 传感器名称或 ID 关键词
    :return: 结果描述字符串
    """
    try:
        # 1. 搜索传感器以获取 ID
        response = api_client.get("/sensors/", params={"search": sensor_name})
        
        # 兼容分页逻辑
        search_results = response.get("results") if isinstance(response, dict) and "results" in response else response

        if not search_results or len(search_results) == 0:
            return f"API 查询不到名为 '{sensor_name}' 的传感器。"
        
        sensor_data = search_results[0]
        sensor_id = sensor_data["sensor_id"]
        actual_name = sensor_data["name"]

        # 2. 获取最新数据 (GET /api/sensors/{sensor_id}/data/)
        endpoint = f"/sensors/{sensor_id}/data/"
        # 获取最近 1 小时的 1 条数据
        history = api_client.get(endpoint, params={"hours": 1, "limit": 1})
        
        if not history or len(history) == 0:
            return f"API 返回传感器 {actual_name} 目前没有活跃数据。"

        latest = history[0]
        # 后端 SensorData 模型中的字段名为 'data'
        business_data = latest.get("data", {})
        time_str = latest.get("timestamp", "未知时间")
        
        data_info = ", ".join([f"{k}: {v}" for k, v in business_data.items()])
        return f"通过 API 获取到 {actual_name} 在 {time_str} 的数据: {data_info}。"

    except Exception as e:
        logger.error(f"OpenClaw 技能异常: {e}")
        return f"执行 API 查询时出错: {str(e)}"

# 意图定义
SKILL_INTENTS = {
    "sensor_query": {
        "function": query_sensor,
        "description": "通过 API 查询环境传感器的最新数值",
        "parameters": {
            "sensor_name": "string"
        }
    }
}
