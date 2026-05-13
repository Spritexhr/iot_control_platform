"""
实时数据服务（用于 EB 装置等 P&ID 大屏场景）。

提供：
- latest_values：进程内最新点位值缓存（线程安全）
- broadcaster：基于队列的发布-订阅，给 SSE 连接推送增量
- sse_views：StreamingHttpResponse 形式的 SSE endpoint
"""
from .latest_values import latest_values, broadcaster

__all__ = ["latest_values", "broadcaster"]
