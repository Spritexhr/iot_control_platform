from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from .models import SensorType, Sensor, SensorData, SensorStatusCollection
from .serializers import (
    SensorTypeSerializer,
    SensorListSerializer,
    SensorDetailSerializer,
    SensorCreateUpdateSerializer,
    SensorDataSerializer,
    SensorStatusSerializer,
)


class SensorTypeViewSet(viewsets.ModelViewSet):
    """传感器类型 CRUD API"""
    queryset = SensorType.objects.all()
    serializer_class = SensorTypeSerializer


class SensorViewSet(viewsets.ModelViewSet):
    """
    传感器 CRUD API
    支持按 sensor_id 查找、筛选、搜索
    """
    queryset = Sensor.objects.select_related('sensor_type').all()
    lookup_field = 'sensor_id'

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return SensorDetailSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return SensorCreateUpdateSerializer
        return SensorListSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        # 按类型筛选
        sensor_type_id = self.request.query_params.get('sensor_type')
        if sensor_type_id:
            qs = qs.filter(sensor_type_id=sensor_type_id)
        # 按在线状态筛选（基于 last_seen 实时计算，3分钟内有数据视为在线）
        online = self.request.query_params.get('online')
        if online is not None:
            threshold = timezone.now() - timedelta(minutes=3)
            if online == 'true':
                qs = qs.filter(last_seen__gte=threshold)
            elif online == 'false':
                qs = qs.filter(Q(last_seen__isnull=True) | Q(last_seen__lt=threshold))
        # 搜索
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(sensor_id__icontains=search))
        return qs

    @action(detail=True, methods=['get'], url_path='data')
    def sensor_data(self, request, sensor_id=None):
        """获取传感器历史数据，支持时间范围查询"""
        sensor = self.get_object()
        hours = int(request.query_params.get('hours', 1))
        limit = int(request.query_params.get('limit', 200))
        start_time = timezone.now() - timedelta(hours=hours)
        records = SensorData.objects.filter(
            sensor=sensor, timestamp__gte=start_time
        ).order_by('-timestamp')[:limit]
        serializer = SensorDataSerializer(records, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='status')
    def sensor_status(self, request, sensor_id=None):
        """获取传感器状态记录"""
        sensor = self.get_object()
        limit = int(request.query_params.get('limit', 50))
        records = SensorStatusCollection.objects.filter(
            sensor=sensor
        ).order_by('-timestamp')[:limit]
        serializer = SensorStatusSerializer(records, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='command')
    def send_command(self, request, sensor_id=None):
        """向传感器发送命令"""
        sensor = self.get_object()
        command_name = request.data.get('command_name')
        params = request.data.get('params', {})
        make_sure = request.data.get('make_sure', False)

        if not command_name:
            return Response(
                {'detail': '缺少 command_name 参数'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            from services.sensors_service.sensor_command_send_service import sensor_command_send_service
            if make_sure:
                result = sensor_command_send_service.send_custom_command_with_make_sure(
                    sensor.sensor_id, command_name, params or None
                )
            else:
                result = sensor_command_send_service.send_custom_command(
                    sensor.sensor_id, command_name, params or None
                )
            return Response({'success': result, 'command': command_name})
        except Exception as e:
            return Response(
                {'detail': str(e), 'success': False},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
