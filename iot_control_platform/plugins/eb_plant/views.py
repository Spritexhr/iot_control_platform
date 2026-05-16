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
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from devices.models import Device
from sensors.models import Sensor, SensorData
from services.realtime.latest_values import broadcaster, ingest_sensor_data, latest_values

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

_KEEPALIVE_SECONDS = 10
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
        """单条或批量导入：
        - 传 sensor_ids=[...] 走批量，按各 sensor 的 sensor_type.data_fields 自动拆分：
          * 多字段（>=2）→ 每个字段建一条 binding，data_key=field、tag=sensorId-field
          * 单字段（=1）或无字段元数据 → 一条 data_key="" 的 binding（保持 P&ID 老画板兼容）
          * (sensor, data_key) 已存在的跳过；UniqueConstraint + ignore_conflicts 兜底并发
        - 否则走 ViewSet 标准 create（用于"+字段"按钮单条新增）
        """
        sensor_ids = request.data.get("sensor_ids")
        if isinstance(sensor_ids, list):
            sensors = Sensor.objects.filter(id__in=sensor_ids).select_related("sensor_type")
            to_create = []
            for s in sensors:
                fields = s.sensor_type.data_fields if s.sensor_type_id else None
                if not (isinstance(fields, list) and fields) or len(fields) == 1:
                    fields_to_use = [""]
                else:
                    fields_to_use = list(fields)

                existing = set(
                    EBPlantSensorBinding.objects.filter(sensor=s).values_list("data_key", flat=True)
                )
                for f in fields_to_use:
                    if f in existing:
                        continue
                    tag = (f"{s.sensor_id}-{f}" if f else s.sensor_id)[:50]
                    to_create.append(EBPlantSensorBinding(sensor=s, data_key=f, tag=tag))

            EBPlantSensorBinding.objects.bulk_create(to_create, ignore_conflicts=True)
            # bulk_create + ignore_conflicts 不保证 PK 返回，重新按 (sensor, data_key) 查回实际写入的行
            created_keys = {(b.sensor_id, b.data_key) for b in to_create}
            if created_keys:
                created_qs = EBPlantSensorBinding.objects.filter(
                    sensor_id__in={k[0] for k in created_keys}
                ).select_related("sensor", "sensor__sensor_type")
                created_qs = [b for b in created_qs if (b.sensor_id, b.data_key) in created_keys]
            else:
                created_qs = []
            data = EBPlantSensorBindingSerializer(created_qs, many=True).data
            return Response({"created": data}, status=status.HTTP_201_CREATED)
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


def _bound_point_ids() -> set:
    """已可见 binding 的 point_id 集合（区分同 sensor 不同 data_key）。"""
    bindings = EBPlantSensorBinding.objects.filter(is_visible=True).select_related("sensor")
    return {b.point_id for b in bindings}


def _backfill_missing_from_db() -> None:
    """
    内存缓存 latest_values 是进程级的：导入新传感器后、或进程刚启动时缓存为空，
    UI 就会"配了没显示"。这里对每个可见 binding，若 point_id 在缓存里没有，
    就从 SensorData 取最近一条 ingest 进来，让大屏立即拿到最后一帧。新帧上来照常推。
    """
    bindings = EBPlantSensorBinding.objects.filter(is_visible=True).select_related("sensor")
    for binding in bindings:
        if latest_values.get(binding.point_id) is not None:
            continue
        last = (
            SensorData.objects.filter(sensor=binding.sensor)
            .order_by("-timestamp")
            .first()
        )
        if last is None:
            continue
        try:
            ingest_sensor_data(
                sensor_id=binding.point_id,
                data=last.data,
                timestamp=last.timestamp.timestamp() if last.timestamp else None,
                plugin_code=PLUGIN_CODE,
                binding=binding,
            )
        except Exception as exc:
            log.warning("EB 回填最近一帧失败 point_id=%s err=%s", binding.point_id, exc)


def _event_stream():
    """SSE 生成器：先发快照，再循环消费广播队列。"""
    q = broadcaster.subscribe()
    last_keepalive = time.time()
    try:
        _backfill_missing_from_db()
        bound = _bound_point_ids()
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
                bound = _bound_point_ids()
    except GeneratorExit:
        pass
    finally:
        broadcaster.unsubscribe(q)


@csrf_exempt
@require_GET
def stream(request):
    """SSE 端点。不走 DRF 的 @api_view —— DRF 的内容协商会因为
    EventSource 发 `Accept: text/event-stream` 而找不到 renderer 返回 406。
    SSE 是纯流式响应，用 Django 原生 view 即可，权限层面跟 snapshot 一样靠 AllowAny。
    """
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
    _backfill_missing_from_db()
    bound = _bound_point_ids()
    samples = [s.to_dict() for s in latest_values.snapshot(PLUGIN_CODE) if s.sensor_id in bound]
    return JsonResponse({"plugin_code": PLUGIN_CODE, "samples": samples})
