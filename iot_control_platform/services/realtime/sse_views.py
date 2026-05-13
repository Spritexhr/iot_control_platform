"""
Server-Sent Events 端点。

GET /api/realtime/plant/<plant_code>/stream
    text/event-stream, 服务器持续推送 sample 事件。客户端用浏览器 EventSource 即可。

GET /api/realtime/plant/<plant_code>/snapshot
    返回当前所有点位的快照（JSON），用于前端初始化。
"""
from __future__ import annotations

import json
import logging
import queue
import time

from django.http import JsonResponse, StreamingHttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from .latest_values import broadcaster, latest_values

log = logging.getLogger(__name__)

# SSE 心跳间隔（秒）。即使没数据也要定期下发，避免代理超时断连。
_KEEPALIVE_SECONDS = 15
# 单次 queue.get 的等待超时——太长则心跳不准；太短则空转
_QUEUE_GET_TIMEOUT = 5.0


def _sse_pack(event_type: str, data: dict) -> bytes:
    """按 SSE 规范打包一条消息。"""
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event_type}\ndata: {payload}\n\n".encode("utf-8")


def _event_stream(plant_code: str):
    """SSE 生成器：先发快照，再循环消费广播队列。"""
    q = broadcaster.subscribe()
    last_keepalive = time.time()
    try:
        # 1) 初始快照
        snapshot = [s.to_dict() for s in latest_values.snapshot(plant_code)]
        yield _sse_pack("snapshot", {"plant_code": plant_code, "samples": snapshot})

        # 2) 增量循环
        while True:
            try:
                event = q.get(timeout=_QUEUE_GET_TIMEOUT)
            except queue.Empty:
                event = None

            now = time.time()
            if event is not None:
                # 按 plant_code 过滤
                data = event.get("data", {})
                if event.get("type") == "sample" and data.get("plant_code") == plant_code:
                    yield _sse_pack("sample", data)
                    last_keepalive = now
                elif event.get("type") == "alert":
                    # 报警事件不分 plant_code 都推（后续可以加过滤）
                    yield _sse_pack("alert", data)
                    last_keepalive = now

            if now - last_keepalive >= _KEEPALIVE_SECONDS:
                yield b": keepalive\n\n"  # 注释行，浏览器忽略但保活
                last_keepalive = now
    except GeneratorExit:
        # 客户端断开
        pass
    finally:
        broadcaster.unsubscribe(q)


@api_view(["GET"])
@permission_classes([AllowAny])
def plant_stream(request, plant_code: str):
    """SSE 流式端点。"""
    response = StreamingHttpResponse(
        _event_stream(plant_code),
        content_type="text/event-stream",
    )
    # 关闭缓冲，禁用代理缓存
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    response["Connection"] = "keep-alive"
    return response


@api_view(["GET"])
@permission_classes([AllowAny])
def plant_snapshot(request, plant_code: str):
    """当前快照，前端可不依赖 SSE 也能加载一次最新值。"""
    samples = [s.to_dict() for s in latest_values.snapshot(plant_code)]
    return JsonResponse({"plant_code": plant_code, "samples": samples})
