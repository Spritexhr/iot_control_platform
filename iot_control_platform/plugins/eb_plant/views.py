"""
乙苯(EB)装置大屏 API。

接口列表
- GET/PUT  /api/plugins/eb_plant/config            读写大屏视图配置
- GET      /api/plugins/eb_plant/bindable_sources  列出主模型全量传感器/设备
- /api/plugins/eb_plant/sensor_bindings (CRUD)     传感器绑定
- /api/plugins/eb_plant/device_bindings (CRUD)     设备绑定
- GET      /api/plugins/eb_plant/snapshot          当前已绑定传感器的最新值

实时推送由 WebSocket consumer 提供（plugins.eb_plant.consumers.EBPlantConsumer，
URL: /ws/plugins/eb_plant/）。原 SSE 端点已在 M3 移除。
"""
from __future__ import annotations

import logging

from django.http import JsonResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from devices.models import Device
from sensors.models import Sensor, SensorData
from services.realtime.latest_values import ingest_sensor_data, latest_values

from .models import EBPlantConfig, EBPlantDeviceBinding, EBPlantSection, EBPlantSensorBinding
from .serializers import (
    BindableDeviceSerializer,
    BindableSensorSerializer,
    EBPlantConfigSerializer,
    EBPlantDeviceBindingSerializer,
    EBPlantSectionSerializer,
    EBPlantSensorBindingSerializer,
)

log = logging.getLogger(__name__)

PLUGIN_CODE = "EB"


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
                if not (isinstance(fields, list) and fields):
                    # sensor_type 未定义 data_fields → 单条空 data_key 兜底
                    fields_to_use = [""]
                else:
                    # 有明确字段（1 个或多个）→ 每个字段建一条 binding，data_key 用实际字段名
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


class EBPlantSectionViewSet(_AdminWritePermission, viewsets.ModelViewSet):
    """大屏工段（栏目）CRUD。读 IsAuthenticated，写 IsAdminUser。"""

    queryset = EBPlantSection.objects.all()
    serializer_class = EBPlantSectionSerializer

    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated, IsAdminUser])
    def reorder(self, request):
        """按传入的 section id 顺序批量写 sort_order。body: {"order": [id, id, ...]}"""
        order = request.data.get("order", [])
        if not isinstance(order, list):
            return Response({"detail": "order 必须是 id 列表"}, status=status.HTTP_400_BAD_REQUEST)
        for idx, sec_id in enumerate(order):
            EBPlantSection.objects.filter(id=sec_id).update(sort_order=idx)
        return Response({"ok": True})


# ---------- 实时数据（snapshot 与 consumer 共用的 helper） ----------

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


def _refresh_online_status(samples: list) -> None:
    """
    snapshot/建连首发用的 is_online 必须实时算，不能信缓存里冻住的旧值。

    latest_values 缓存是进程级的：backend 的 worker 自己几乎不会调 ingest_sensor_data
    （那是 mqtt_runner 进程的事），所以它本地缓存里的 PointSample.is_online 往往是很久前
    backfill 那一刻算的，可能早就过期。这里用跟传感器管理页同一套口径（Sensor.computed_is_online）
    现查现算覆盖一遍，避免"切页面/重连一瞬间显示旧状态，几秒后下一帧数据来了才跳回正确状态"的闪烁。
    """
    bindings = EBPlantSensorBinding.objects.filter(is_visible=True).select_related("sensor")
    sensor_by_point = {b.point_id: b.sensor for b in bindings}
    for sample in samples:
        sensor = sensor_by_point.get(sample.get("sensor_id"))
        if sensor is None:
            continue
        sample["is_online"] = bool(sensor.computed_is_online)
        sample["last_seen"] = sensor.last_seen.timestamp() if sensor.last_seen else None


def _device_states() -> list:
    """已可见设备绑定的当前状态：取主模型最近一条 DeviceStatusCollection + 实时在线判定。
    在线状态用 Device.computed_is_online 现查现算（跟设备管理页同口径）。"""
    bindings = (
        EBPlantDeviceBinding.objects.filter(is_visible=True)
        .select_related("device", "device__device_type")
    )
    states = []
    for b in bindings:
        device = b.device
        last = device.status_records.order_by("-timestamp").first()
        states.append({
            "device_id": device.device_id,
            "name": device.name,
            "tag": b.tag or device.device_id,
            "status": (last.data if last and isinstance(last.data, dict) else {}),
            "event": (last.event_name if last else ""),
            "is_online": bool(device.computed_is_online),
            "last_seen": device.last_seen.timestamp() if device.last_seen else None,
            "ts": last.timestamp.timestamp() if (last and last.timestamp) else None,
        })
    return states


def _build_layout() -> dict:
    """大屏骨架：有序工段，每段挂它的传感器/设备绑定（含静态元信息），
    未归属 section 的绑定统一落到末尾「未分组」段。"""
    from collections import defaultdict

    sensor_bindings = (
        EBPlantSensorBinding.objects.filter(is_visible=True)
        .select_related("sensor", "sensor__sensor_type", "section")
    )
    device_bindings = (
        EBPlantDeviceBinding.objects.filter(is_visible=True)
        .select_related("device", "device__device_type", "section")
    )
    s_data = EBPlantSensorBindingSerializer(sensor_bindings, many=True).data
    d_data = EBPlantDeviceBindingSerializer(device_bindings, many=True).data

    s_by_sec = defaultdict(list)
    for it in s_data:
        s_by_sec[it.get("section")].append(it)
    d_by_sec = defaultdict(list)
    for it in d_data:
        d_by_sec[it.get("section")].append(it)

    sections = []
    for sec in EBPlantSection.objects.all():
        sections.append({
            "id": sec.id,
            "name": sec.name,
            "sort_order": sec.sort_order,
            "sensors": s_by_sec.get(sec.id, []),
            "devices": d_by_sec.get(sec.id, []),
        })

    unassigned_sensors = s_by_sec.get(None, [])
    unassigned_devices = d_by_sec.get(None, [])
    if unassigned_sensors or unassigned_devices:
        sections.append({
            "id": None,
            "name": "未分组",
            "sort_order": 10 ** 9,
            "sensors": unassigned_sensors,
            "devices": unassigned_devices,
        })

    return {"plugin_code": PLUGIN_CODE, "sections": sections}


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def layout(request):
    return Response(_build_layout())


@api_view(["GET"])
@permission_classes([AllowAny])
def snapshot(request):
    _backfill_missing_from_db()
    bound = _bound_point_ids()
    samples = [s.to_dict() for s in latest_values.snapshot(PLUGIN_CODE) if s.sensor_id in bound]
    _refresh_online_status(samples)
    return JsonResponse({
        "plugin_code": PLUGIN_CODE,
        "samples": samples,
        "devices": _device_states(),
    })
