"""
进程内最新点位值缓存 + 发布订阅广播器。

设计要点
- 仅在单进程内有效。多进程部署时需要换 Redis pub/sub，但单机 demo 单进程足够。
- 写入方（插件 signal handler）调用 ingest_sensor_data(...)，更新缓存并向所有订阅队列 put。
- 读取方（SSE 请求线程）调用 subscribe() 拿到一个 queue.Queue，循环 get 即可。
- 队列大小有限（256），满了直接丢最旧——SSE 慢客户端不能拖垮发布方。
- 主模型(Sensor/Device)对本模块零依赖；展示元数据由插件 binding 对象按鸭子类型传入。
"""
from __future__ import annotations

import logging
import queue
import threading
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)


@dataclass
class PointSample:
    """单个监测点的最新值。"""

    sensor_id: str
    plugin_code: str
    tag: str  # 仪表位号，例如 TT-101
    value: Optional[float]
    unit: str = ""
    ts: float = 0.0
    status: str = "normal"  # normal / warn_high / warn_low / alarm_high / alarm_low
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


class LatestValuesCache:
    """线程安全的最新点位值缓存，按 sensor_id 索引。"""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._values: Dict[str, PointSample] = {}

    def update(self, sample: PointSample) -> None:
        with self._lock:
            self._values[sample.sensor_id] = sample

    def get(self, sensor_id: str) -> Optional[PointSample]:
        with self._lock:
            return self._values.get(sensor_id)

    def snapshot(self, plugin_code: Optional[str] = None) -> List[PointSample]:
        with self._lock:
            if plugin_code is None:
                return list(self._values.values())
            return [s for s in self._values.values() if s.plugin_code == plugin_code]

    def clear(self) -> None:
        with self._lock:
            self._values.clear()


class Broadcaster:
    """
    发布-订阅广播器。
    每个 SSE 连接 subscribe() 一次拿到独立队列，断开时 unsubscribe()。
    """

    QUEUE_MAX = 256

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._subscribers: List[queue.Queue] = []

    def subscribe(self) -> queue.Queue:
        q: queue.Queue = queue.Queue(maxsize=self.QUEUE_MAX)
        with self._lock:
            self._subscribers.append(q)
        log.debug("[realtime] 新订阅者，当前数 %d", len(self._subscribers))
        return q

    def unsubscribe(self, q: queue.Queue) -> None:
        with self._lock:
            try:
                self._subscribers.remove(q)
            except ValueError:
                pass
        log.debug("[realtime] 订阅者退出，剩余 %d", len(self._subscribers))

    def publish(self, event: dict) -> None:
        """非阻塞广播。队列满时丢弃该订阅者的此次消息（保留最新策略）。"""
        with self._lock:
            subs = list(self._subscribers)
        for q in subs:
            try:
                q.put_nowait(event)
            except queue.Full:
                try:
                    q.get_nowait()
                    q.put_nowait(event)
                except (queue.Empty, queue.Full):
                    pass


def classify_status(value: Optional[float], hi: Any, lo: Any, severity: str) -> str:
    """根据 binding 上的阈值判定状态。"""
    if value is None:
        return "normal"
    try:
        sev = (severity or "mid").lower()
        if hi is not None and value > float(hi):
            return "alarm_high" if sev in ("high", "critical") else "warn_high"
        if lo is not None and value < float(lo):
            return "alarm_low" if sev in ("high", "critical") else "warn_low"
    except (TypeError, ValueError):
        pass
    return "normal"


latest_values = LatestValuesCache()
broadcaster = Broadcaster()


def ingest_sensor_data(
    sensor_id: str,
    data: dict,
    timestamp: Optional[float],
    *,
    plugin_code: str,
    binding: Any,
) -> Optional[PointSample]:
    """
    把一次传感器数据上报转成 PointSample 写入缓存并广播。

    binding 是插件自有的绑定对象（鸭子类型），需具备以下属性：
      tag / unit / data_key / hi_threshold / lo_threshold / severity /
      area (可选) / normal_value (可选)
    """
    tag = getattr(binding, "tag", "") or sensor_id
    unit = getattr(binding, "unit", "") or ""
    data_key = getattr(binding, "data_key", "") or ""
    hi = getattr(binding, "hi_threshold", None)
    lo = getattr(binding, "lo_threshold", None)
    severity = getattr(binding, "severity", "mid") or "mid"

    value: Optional[float] = None
    if isinstance(data, dict):
        if data_key and data_key in data:
            raw = data[data_key]
        elif len(data) == 1:
            raw = next(iter(data.values()))
        else:
            raw = data.get("value") or data.get("temperature") or data.get("pressure") \
                or data.get("flow_rate") or data.get("level")
        try:
            value = float(raw) if raw is not None else None
        except (TypeError, ValueError):
            value = None

    sample = PointSample(
        sensor_id=sensor_id,
        plugin_code=plugin_code or "",
        tag=tag,
        value=value,
        unit=unit,
        ts=float(timestamp) if timestamp else time.time(),
        status=classify_status(value, hi, lo, severity),
        metadata={
            "area": getattr(binding, "area", "") or "",
            "normal_value": getattr(binding, "normal_value", None),
            "hi_threshold": hi,
            "lo_threshold": lo,
            "severity": severity,
        },
    )
    latest_values.update(sample)
    broadcaster.publish({"type": "sample", "data": sample.to_dict()})
    return sample
