"""
data_viz 插件 - 时间段数据可视化

提供:
- GET /ping/                    端到端探针
- GET /sources/                 列出所有 sensor + device，附带可绘制字段
- GET /series/?kind=&source_id= 取指定来源在时间窗内的时序数据 + 状态事件
"""
from datetime import timedelta

from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from devices.models import Device, DeviceData
from sensors.models import Sensor, SensorData, SensorStatusCollection

# 单次返回上限，避免一次性把 10w 行扔给前端图表
DEFAULT_LIMIT = 2000
MAX_LIMIT = 10000


def _parse_dt(value, default):
    """解析 ISO 时间，失败返回 default"""
    if not value:
        return default
    dt = parse_datetime(value)
    if dt is None:
        return default
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt)
    return dt


def _truncate_window(qs, limit):
    """
    时间窗内若行数超 limit，仅保留最近 limit 条，并按时间升序返回
    （图表通常关心"最近"，前段截断比均匀采样更直观）
    """
    total = qs.count()
    if total > limit:
        rows = list(qs.order_by("-timestamp")[:limit])
        rows.reverse()
    else:
        rows = list(qs.order_by("timestamp"))
    return rows, total


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def ping(request):
    """端到端验证"""
    return Response({"plugin": "data_viz", "status": "ok"})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def sources(request):
    """
    列出可视化数据源
    返回所有 sensor + device 及其可绘制字段（来自类型定义）
    """
    sensor_list = []
    for s in Sensor.objects.select_related("sensor_type").all():
        sensor_list.append({
            "id": s.sensor_id,
            "name": s.name,
            "type": s.sensor_type.name if s.sensor_type else "",
            "data_fields": s.sensor_type.data_fields if s.sensor_type else [],
            "is_online": s.computed_is_online,
            "last_seen": s.last_seen.isoformat() if s.last_seen else None,
            "location": s.location,
        })

    device_list = []
    for d in Device.objects.select_related("device_type").all():
        device_list.append({
            "id": d.device_id,
            "name": d.name,
            "type": d.device_type.name if d.device_type else "",
            "state_fields": d.device_type.state_fields if d.device_type else [],
            "is_online": d.is_online,
            "last_seen": d.last_seen.isoformat() if d.last_seen else None,
            "location": d.location,
        })

    return Response({"sensors": sensor_list, "devices": device_list})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def series(request):
    """
    取指定来源的时间窗时序数据
    Query:
      kind:       sensor | device
      source_id:  Sensor.sensor_id 或 Device.device_id
      start, end: ISO 时间，缺省为最近 24 小时
      limit:      返回点上限，默认 2000，最大 10000
    """
    kind = (request.GET.get("kind") or "").lower()
    source_id = request.GET.get("source_id") or ""
    if kind not in ("sensor", "device") or not source_id:
        return Response(
            {"detail": "kind 必须为 sensor 或 device，且 source_id 必填"},
            status=400,
        )

    now = timezone.now()
    end = _parse_dt(request.GET.get("end"), now)
    start = _parse_dt(request.GET.get("start"), end - timedelta(hours=24))
    if start >= end:
        return Response({"detail": "start 必须早于 end"}, status=400)

    try:
        limit = int(request.GET.get("limit") or DEFAULT_LIMIT)
    except ValueError:
        limit = DEFAULT_LIMIT
    limit = max(1, min(limit, MAX_LIMIT))

    if kind == "sensor":
        try:
            sensor = Sensor.objects.select_related("sensor_type").get(sensor_id=source_id)
        except Sensor.DoesNotExist:
            return Response({"detail": f"传感器 {source_id} 不存在"}, status=404)

        data_qs = SensorData.objects.filter(
            sensor=sensor, timestamp__gte=start, timestamp__lte=end
        )
        rows, total = _truncate_window(data_qs, limit)
        points = [{"t": r.timestamp.isoformat(), "data": r.data} for r in rows]

        # 状态事件：上限单独限制，不与 data 共用
        events_qs = SensorStatusCollection.objects.filter(
            sensor=sensor, timestamp__gte=start, timestamp__lte=end
        ).order_by("timestamp")[:limit]
        events = [
            {"t": e.timestamp.isoformat(), "event": e.event_name, "data": e.data}
            for e in events_qs
        ]

        return Response({
            "kind": "sensor",
            "source_id": sensor.sensor_id,
            "name": sensor.name,
            "type": sensor.sensor_type.name if sensor.sensor_type else "",
            "fields": sensor.sensor_type.data_fields if sensor.sensor_type else [],
            "start": start.isoformat(),
            "end": end.isoformat(),
            "points": points,
            "count": total,
            "truncated": total > limit,
            "events": events,
        })

    # kind == "device"
    try:
        device = Device.objects.select_related("device_type").get(device_id=source_id)
    except Device.DoesNotExist:
        return Response({"detail": f"设备 {source_id} 不存在"}, status=404)

    data_qs = DeviceData.objects.filter(
        device=device, timestamp__gte=start, timestamp__lte=end
    )
    rows, total = _truncate_window(data_qs, limit)
    points = [{"t": r.timestamp.isoformat(), "data": r.data} for r in rows]

    return Response({
        "kind": "device",
        "source_id": device.device_id,
        "name": device.name,
        "type": device.device_type.name if device.device_type else "",
        "fields": device.device_type.state_fields if device.device_type else [],
        "start": start.isoformat(),
        "end": end.isoformat(),
        "points": points,
        "count": total,
        "truncated": total > limit,
        "events": [],
    })
