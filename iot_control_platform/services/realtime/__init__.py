"""
实时数据服务 —— 基础设施层。

提供：
- latest_values：进程内最新点位值缓存（线程安全；用于 snapshot/回填）
- ingest_sensor_data：把一次传感器上报转成 PointSample 写入缓存并通过 channel layer 广播
- dispatch.publish_*：信号 handler 用的业务级广播 API（与 consumers.py 的 broadcast_* 配套）

WebSocket 推送由 services.realtime.consumers + dispatch 接管。
（早期版本基于 SSE + 进程内 Broadcaster，0.8 起切换为 channels + Redis。）
"""
from .latest_values import ingest_sensor_data, latest_values

__all__ = ["latest_values", "ingest_sensor_data"]
