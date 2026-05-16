"""
P&ID 画板 API。

- /api/plugins/plant_diagram/                     列表 / 创建
- /api/plugins/plant_diagram/<id>/                详情 / 更新 / 删除
- /api/plugins/plant_diagram/bindable_targets/    给节点绑定下拉用的传感器 + 设备清单
"""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from devices.models import Device
from plugins.eb_plant.models import EBPlantDeviceBinding, EBPlantSensorBinding
from sensors.models import Sensor

from .models import PlantDiagram
from .serializers import PlantDiagramDetailSerializer, PlantDiagramListSerializer


class PlantDiagramViewSet(viewsets.ModelViewSet):
    """画板 CRUD。编辑操作仅 is_staff，普通用户只能读。"""

    queryset = PlantDiagram.objects.all()

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAuthenticated(), IsAdminUser()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == "list":
            return PlantDiagramListSerializer
        return PlantDiagramDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        # 仅按 PlantDiagram 自身的 plant_code 字段过滤（与主模型无关）
        plant_code = self.request.query_params.get("plant_code")
        if plant_code:
            qs = qs.filter(plant_code=plant_code.strip().upper())
        return qs

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(created_by=user)

    @action(detail=False, methods=["get"], url_path="bindable_targets")
    def bindable_targets(self, request):
        """
        返回可绑定到节点的传感器 / 设备列表。

        - 装置插件已经接管"哪些点位被纳入大屏"这件事（如 EB 走 EBPlantSensorBinding/
          EBPlantDeviceBinding），P&ID 画板只是这份点位集合的另一种可视化形态，所以
          下拉只列已绑定的点，避免画板和大屏出现不一致的点位集合。
        - 节点 binding.id 存的是 binding.point_id（单字段 = sensor_id，多字段 = sensor_id::data_key），
          与 SSE 推送下来的 sample.sensor_id 直接精确命中。

        TODO: 未来新增装置插件（如 ST）后，把"plant_code → binding 表"的映射改成
              注册机制，而不是这里硬编码。
        """
        plant_code = (request.query_params.get("plant_code") or "EB").strip().upper()

        if plant_code == "EB":
            sensor_bindings = (
                EBPlantSensorBinding.objects
                .filter(is_visible=True)
                .select_related("sensor", "sensor__sensor_type")
                .order_by("sort_order", "id")
            )
            sensors = []
            for b in sensor_bindings:
                s = b.sensor
                sensors.append({
                    "id": b.point_id,
                    "name": s.name,
                    "tag": b.tag,
                    "data_key": b.data_key,
                    "unit": b.unit,
                    "area": b.area,
                    "type": s.sensor_type.name if s.sensor_type_id else "",
                    "hi_threshold": b.hi_threshold,
                    "lo_threshold": b.lo_threshold,
                    "severity": b.severity,
                })

            device_bindings = (
                EBPlantDeviceBinding.objects
                .filter(is_visible=True)
                .select_related("device", "device__device_type")
                .order_by("sort_order", "id")
            )
            devices = []
            for b in device_bindings:
                d = b.device
                devices.append({
                    "id": d.device_id,
                    "name": d.name,
                    "tag": b.tag,
                    "area": b.area,
                    "type": d.device_type.name if d.device_type_id else "",
                    "commands": list((d.device_type.commands or {}).keys()) if d.device_type_id else [],
                })

            return Response({"sensors": sensors, "devices": devices})

        # 其他 plant_code 暂时还没有专属 binding 表（如 ST 装置插件尚未实现），
        # 回落主模型全量保持画板可用，待对应插件落地后再走该插件的 binding 表。
        sensors = []
        for s in Sensor.objects.select_related("sensor_type").order_by("sort_order", "sensor_id"):
            sensors.append({
                "id": s.sensor_id,
                "name": s.name,
                "type": s.sensor_type.name if s.sensor_type_id else "",
                "data_fields": (s.sensor_type.data_fields or []) if s.sensor_type_id else [],
            })

        devices = []
        for d in Device.objects.select_related("device_type").order_by("sort_order", "device_id"):
            devices.append({
                "id": d.device_id,
                "name": d.name,
                "type": d.device_type.name if d.device_type_id else "",
                "commands": list((d.device_type.commands or {}).keys()) if d.device_type_id else [],
            })

        return Response({"sensors": sensors, "devices": devices})
