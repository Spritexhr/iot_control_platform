"""
EB 装置 WebSocket consumer。

订阅 group: plugins.EB
- 建连时 _send_initial 发一个 snapshot 事件（含全部已绑定点位的最新值）
- 每条新样本由 services/realtime/latest_values.ingest_sensor_data
  → dispatch.publish_plugin_sample("EB", ...)
  → broadcast.plugin.sample → 这里转发为 {event: "sample", data: PointSample}
"""
from __future__ import annotations

from channels.db import database_sync_to_async

from services.realtime.consumers import _BaseAuthedConsumer

PLUGIN_CODE = "EB"


class EBPlantConsumer(_BaseAuthedConsumer):
    groups_to_join = [f"plugins.{PLUGIN_CODE}"]

    async def _send_initial(self):
        snap = await database_sync_to_async(self._build_snapshot)()
        await self.send_json({"event": "snapshot", "data": snap})

    @staticmethod
    def _build_snapshot() -> dict:
        # 复用 views.py 现有的快照逻辑（回填 + 过滤可见 binding）
        # 插件内部 import，不跨包污染
        from services.realtime.latest_values import latest_values

        from .views import _backfill_missing_from_db, _bound_point_ids

        _backfill_missing_from_db()
        bound = _bound_point_ids()
        samples = [
            s.to_dict()
            for s in latest_values.snapshot(PLUGIN_CODE)
            if s.sensor_id in bound
        ]
        return {"plugin_code": PLUGIN_CODE, "samples": samples}

    async def broadcast_plugin_sample(self, event):
        await self.send_json({"event": "sample", "data": event["payload"]})
