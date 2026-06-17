"""
EB 装置 WebSocket consumer。

订阅 group:
- plugins.EB    本插件传感器采样流
- devices.all   主层全量设备状态流（设备状态直接复用主层 DeviceStatusCollection 信号，
                本插件不另写设备信号；这里按已绑定设备过滤后转发）

事件：
- 建连时 _send_initial 发一个 snapshot 事件（含已绑定传感器最新值 + 已绑定设备最新状态）
- 传感器新样本：ingest_sensor_data → dispatch.publish_plugin_sample("EB", ...)
  → broadcast.plugin.sample → 转发为 {event: "sample", data: PointSample}
- 设备新状态：DeviceStatusCollection post_save → dispatch.publish_device_status
  → broadcast.device.status → 过滤已绑定后转发为 {event: "device.status", data: ...}
"""
from __future__ import annotations

from channels.db import database_sync_to_async

from services.realtime.consumers import _BaseAuthedConsumer

PLUGIN_CODE = "EB"


class EBPlantConsumer(_BaseAuthedConsumer):
    groups_to_join = [f"plugins.{PLUGIN_CODE}", "devices.all"]

    # 已绑定且可见的设备 id 集合，建连时查一次用于过滤 devices.all 广播。
    # 类级默认空集，避免 _send_initial 之前的极短窗口里收到广播报 AttributeError。
    _bound_device_ids: frozenset = frozenset()

    async def _send_initial(self):
        snap = await database_sync_to_async(self._build_snapshot)()
        self._bound_device_ids = frozenset(d["device_id"] for d in snap.get("devices", []))
        await self.send_json({"event": "snapshot", "data": snap})

    @staticmethod
    def _build_snapshot() -> dict:
        # 复用 views.py 现有的快照逻辑（回填 + 过滤可见 binding）
        # 插件内部 import，不跨包污染
        from services.realtime.latest_values import latest_values

        from .views import (
            _backfill_missing_from_db,
            _bound_point_ids,
            _device_states,
            _refresh_online_status,
        )

        _backfill_missing_from_db()
        bound = _bound_point_ids()
        samples = [
            s.to_dict()
            for s in latest_values.snapshot(PLUGIN_CODE)
            if s.sensor_id in bound
        ]
        # 跟 HTTP snapshot 端点一样：is_online 现查现算，不用缓存里冻住的旧值，
        # 否则每次切页面重连 WS 都会先闪一下错误状态，等下一帧数据来才跳回正确值
        _refresh_online_status(samples)
        return {"plugin_code": PLUGIN_CODE, "samples": samples, "devices": _device_states()}

    async def broadcast_plugin_sample(self, event):
        await self.send_json({"event": "sample", "data": event["payload"]})

    async def broadcast_device_status(self, event):
        payload = event["payload"]
        # 只转发已绑定到大屏的设备；其余设备的状态广播在此丢弃
        if payload.get("device_id") in self._bound_device_ids:
            await self.send_json({"event": "device.status", "data": payload})
