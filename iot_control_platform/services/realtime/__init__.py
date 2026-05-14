"""
实时数据服务 —— 基础设施层。

提供：
- latest_values：进程内最新点位值缓存（线程安全）
- broadcaster：基于队列的发布-订阅，给 SSE 连接推送增量
- ingest_sensor_data：把一次传感器上报转成 PointSample 写入缓存并广播

API 层（SSE 流 / 快照 / 控制）按装置分散在 plugins/<plant>_plant/ 下，
例如 plugins/eb_plant 复用这里的缓存和广播器。
"""
from .latest_values import broadcaster, ingest_sensor_data, latest_values

__all__ = ["latest_values", "broadcaster", "ingest_sensor_data"]
