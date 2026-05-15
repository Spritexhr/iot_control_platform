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
        返回可绑定到节点的传感器 / 设备列表（全量主模型）。
        节点上的位号、单位、阈值等绘制参数由前端节点属性面板保存到 canvas JSON 中，
        本接口仅负责返回主模型的基础元数据。
        """
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
