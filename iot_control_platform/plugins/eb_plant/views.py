"""
乙苯(EB)装置大屏 API。

GET  /api/plugins/eb_plant/snapshot     当前所有点位的快照（JSON）
GET  /api/plugins/eb_plant/stream       SSE 流，server 持续推 sample/alert 事件
POST /api/plugins/eb_plant/disturbance  下发扰动场景到模拟器
"""
from __future__ import annotations

import json
import logging
import queue
import time

from django.http import JsonResponse, StreamingHttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from services.mqtt_service import mqtt_service
from services.realtime.latest_values import broadcaster, latest_values

log = logging.getLogger(__name__)

# EB 装置代号 —— 数据库 sensor 表里仍按 plant_code 区分，
# 插件只关心 EB 这一个装置；以后做其他装置再拆新插件。
PLANT_CODE = "EB"

VALID_SCENARIOS = {
    "none", "ethylene_overfeed", "cooling_failure", "deb_snowball",
}
CONTROL_TOPIC = "plant/EB/disturbance/control"

# SSE 心跳间隔（秒）。即使没数据也要定期下发，避免代理超时断连。
_KEEPALIVE_SECONDS = 15
# 单次 queue.get 的等待超时——太长则心跳不准；太短则空转
_QUEUE_GET_TIMEOUT = 5.0


def _sse_pack(event_type: str, data: dict) -> bytes:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event_type}\ndata: {payload}\n\n".encode("utf-8")


def _event_stream():
    """SSE 生成器：先发快照，再循环消费广播队列。"""
    q = broadcaster.subscribe()
    last_keepalive = time.time()
    try:
        snapshot = [s.to_dict() for s in latest_values.snapshot(PLANT_CODE)]
        yield _sse_pack("snapshot", {"plant_code": PLANT_CODE, "samples": snapshot})

        while True:
            try:
                event = q.get(timeout=_QUEUE_GET_TIMEOUT)
            except queue.Empty:
                event = None

            now = time.time()
            if event is not None:
                data = event.get("data", {})
                if event.get("type") == "sample" and data.get("plant_code") == PLANT_CODE:
                    yield _sse_pack("sample", data)
                    last_keepalive = now
                elif event.get("type") == "alert":
                    yield _sse_pack("alert", data)
                    last_keepalive = now

            if now - last_keepalive >= _KEEPALIVE_SECONDS:
                yield b": keepalive\n\n"
                last_keepalive = now
    except GeneratorExit:
        pass
    finally:
        broadcaster.unsubscribe(q)


@api_view(["GET"])
@permission_classes([AllowAny])
def stream(request):
    """SSE 流式端点。"""
    response = StreamingHttpResponse(
        _event_stream(),
        content_type="text/event-stream",
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    response["Connection"] = "keep-alive"
    return response


@api_view(["GET"])
@permission_classes([AllowAny])
def snapshot(request):
    """当前快照，前端可不依赖 SSE 也能加载一次最新值。"""
    samples = [s.to_dict() for s in latest_values.snapshot(PLANT_CODE)]
    return JsonResponse({"plant_code": PLANT_CODE, "samples": samples})


@api_view(["POST"])
@permission_classes([AllowAny])
def disturbance(request):
    """下发扰动场景给模拟器。"""
    scenario = (request.data.get("scenario") or "").strip()
    if scenario not in VALID_SCENARIOS:
        return Response(
            {"detail": f"未知 scenario,有效值: {sorted(VALID_SCENARIOS)}"},
            status=400,
        )
    ok = mqtt_service.publish(CONTROL_TOPIC, {"scenario": scenario}, qos=1)
    if not ok:
        return Response({"detail": "MQTT 未连接,无法下发"}, status=503)
    log.info("已下发扰动场景: %s", scenario)
    return Response({"scenario": scenario, "delivered": True})
