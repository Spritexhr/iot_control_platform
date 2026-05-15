"""
乙苯(EB)装置大屏 API。

接口列表
- GET/PUT  /api/plugins/eb_plant/config            读写大屏视图配置
- GET      /api/plugins/eb_plant/bindable_sources  列出主模型全量传感器/设备
- /api/plugins/eb_plant/sensor_bindings (CRUD)     传感器绑定
- /api/plugins/eb_plant/device_bindings (CRUD)     设备绑定
- GET      /api/plugins/eb_plant/snapshot          当前已绑定传感器的最新值
- GET      /api/plugins/eb_plant/stream            SSE 实时流（仅推送绑定的传感器）
"""
from __future__ import annotations

import json
import logging
import queue
import time

from django.http import JsonResponse, StreamingHttpResponse
from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from devices.models import Device
from sensors.models import Sensor
from services.realtime.latest_values import broadcaster, latest_values

from .models import EBPlantConfig, EBPlantDeviceBinding, EBPlantSensorBinding
from .serializers import (
    BindableDeviceSerializer,
    BindableSensorSerializer,
    EBPlantConfigSerializer,
    EBPlantDeviceBindingSerializer,
    EBPlantSensorBindingSerializer,
)

log = logging.getLogger(__name__)

PLUGIN_CODE = "EB"

_KEEPALIVE_SECONDS = 15
_QUEUE_GET_TIMEOUT = 5.0


# ---------- 配置 ----------

@api_view(["GET", "PUT"])
@permission_classes([IsAuthenticated])
def config_view(request):
    obj, _ = EBPlantConfig.objects.get_or_create(name="default")
    if request.method == "GET":
        return Response(EBPlantConfigSerializer(obj).data)
    if not request.user.is_staff:
        return Response({"detail": "需要管理员权限"}, status=status.HTTP_403_FORBIDDEN)
    serializer = EBPlantConfigSerializer(obj, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


# ---------- 可导入的主模型清单 ----------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def bindable_sources(request):
    sensors_qs = Sensor.objects.select_related("sensor_type").order_by("sort_order", "sensor_id")
    devices_qs = Device.objects.select_related("device_type").order_by("sort_order", "device_id")
    return Response({
        "sensors": BindableSensorSerializer(sensors_qs, many=True).data,
        "devices": BindableDeviceSerializer(devices_qs, many=True).data,
    })


# ---------- 绑定 CRUD ----------

class _AdminWritePermission:
    """读用 IsAuthenticated，写用 IsAdminUser。"""

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy", "bulk_create"):
            return [IsAuthenticated(), IsAdminUser()]
        return [IsAuthenticated()]


class EBPlantSensorBindingViewSet(_AdminWritePermission, viewsets.ModelViewSet):
    queryset = EBPlantSensorBinding.objects.select_related("sensor", "sensor__sensor_type").all()
    serializer_class = EBPlantSensorBindingSerializer

    def create(self, request, *args, **kwargs):
        """单条或批量导入：传 sensor_ids=[...] 走批量，否则走单条标准流程。"""
        sensor_ids = request.data.get("sensor_ids")
        if isinstance(sensor_ids, list):
            created = []
            sensors = Sensor.objects.filter(id__in=sensor_ids)
            existing = set(
                EBPlantSensorBinding.objects.filter(sensor_id__in=sensor_ids).values_list("sensor_id", flat=True)
            )
            for s in sensors:
                if s.id in existing:
                    continue
                b = EBPlantSensorBinding.objects.create(sensor=s, tag=s.sensor_id)
                created.append(b)
            data = EBPlantSensorBindingSerializer(created, many=True).data
            return Response({"created": data, "skipped": len(existing)}, status=status.HTTP_201_CREATED)
        return super().create(request, *args, **kwargs)


class EBPlantDeviceBindingViewSet(_AdminWritePermission, viewsets.ModelViewSet):
    queryset = EBPlantDeviceBinding.objects.select_related("device", "device__device_type").all()
    serializer_class = EBPlantDeviceBindingSerializer

    def create(self, request, *args, **kwargs):
        device_ids = request.data.get("device_ids")
        if isinstance(device_ids, list):
            created = []
            devices = Device.objects.filter(id__in=device_ids)
            existing = set(
                EBPlantDeviceBinding.objects.filter(device_id__in=device_ids).values_list("device_id", flat=True)
            )
            for d in devices:
                if d.id in existing:
                    continue
                b = EBPlantDeviceBinding.objects.create(device=d, tag=d.device_id)
                created.append(b)
            data = EBPlantDeviceBindingSerializer(created, many=True).data
            return Response({"created": data, "skipped": len(existing)}, status=status.HTTP_201_CREATED)
        return super().create(request, *args, **kwargs)


# ---------- 实时数据 ----------

def _sse_pack(event_type: str, data: dict) -> bytes:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event_type}\ndata: {payload}\n\n".encode("utf-8")


def _bound_sensor_ids() -> set:
    return set(
        EBPlantSensorBinding.objects.filter(is_visible=True)
        .values_list("sensor__sensor_id", flat=True)
    )


def _event_stream():
    """SSE 生成器：先发快照，再循环消费广播队列。"""
    q = broadcaster.subscribe()
    last_keepalive = time.time()
    try:
        bound = _bound_sensor_ids()
        snap = [s.to_dict() for s in latest_values.snapshot(PLUGIN_CODE) if s.sensor_id in bound]
        yield _sse_pack("snapshot", {"plugin_code": PLUGIN_CODE, "samples": snap})

        while True:
            try:
                event = q.get(timeout=_QUEUE_GET_TIMEOUT)
            except queue.Empty:
                event = None

            now = time.time()
            if event is not None:
                data = event.get("data", {})
                if event.get("type") == "sample" and data.get("plugin_code") == PLUGIN_CODE:
                    if data.get("sensor_id") in bound or not bound:
                        yield _sse_pack("sample", data)
                        last_keepalive = now
                elif event.get("type") == "alert":
                    yield _sse_pack("alert", data)
                    last_keepalive = now

            if now - last_keepalive >= _KEEPALIVE_SECONDS:
                yield b": keepalive\n\n"
                last_keepalive = now
                bound = _bound_sensor_ids()
    except GeneratorExit:
        pass
    finally:
        broadcaster.unsubscribe(q)


@api_view(["GET"])
@permission_classes([AllowAny])
def stream(request):
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
    bound = _bound_sensor_ids()
    samples = [s.to_dict() for s in latest_values.snapshot(PLUGIN_CODE) if s.sensor_id in bound]
    return JsonResponse({"plugin_code": PLUGIN_CODE, "samples": samples})
