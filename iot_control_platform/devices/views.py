from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from .models import DeviceType, Device, DeviceData
from .serializers import (
    DeviceTypeSerializer,
    DeviceListSerializer,
    DeviceDetailSerializer,
    DeviceCreateUpdateSerializer,
    DeviceDataSerializer,
)


class DeviceTypeViewSet(viewsets.ModelViewSet):
    """设备类型 CRUD API"""
    queryset = DeviceType.objects.all()
    serializer_class = DeviceTypeSerializer


class DeviceViewSet(viewsets.ModelViewSet):
    """
    设备 CRUD API
    支持按 device_id 查找、筛选、搜索
    """
    queryset = Device.objects.select_related('device_type').all()
    lookup_field = 'device_id'

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return DeviceDetailSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return DeviceCreateUpdateSerializer
        return DeviceListSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        # 按类型筛选
        device_type_id = self.request.query_params.get('device_type')
        if device_type_id:
            qs = qs.filter(device_type_id=device_type_id)
        # 按在线状态筛选（基于 last_seen 动态计算）
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
            qs = qs.filter(Q(name__icontains=search) | Q(device_id__icontains=search))
        return qs

    @action(detail=True, methods=['get'], url_path='data')
    def device_data(self, request, device_id=None):
        """获取设备历史数据，支持时间范围查询"""
        device = self.get_object()
        hours = int(request.query_params.get('hours', 1))
        limit = int(request.query_params.get('limit', 200))
        start_time = timezone.now() - timedelta(hours=hours)
        records = DeviceData.objects.filter(
            device=device, timestamp__gte=start_time
        ).order_by('-timestamp')[:limit]
        serializer = DeviceDataSerializer(records, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='command')
    def send_command(self, request, device_id=None):
        """向设备发送命令"""
        device = self.get_object()
        command_name = request.data.get('command_name')
        params = request.data.get('params', {})
        make_sure = request.data.get('make_sure', False)

        if not command_name:
            return Response(
                {'detail': '缺少 command_name 参数'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            from services.devices_service.device_command_send_service import device_command_send_service
            if make_sure:
                result = device_command_send_service.send_custom_command_with_make_sure(
                    device.device_id, command_name, params or None
                )
            else:
                result = device_command_send_service.send_custom_command(
                    device.device_id, command_name, params or None
                )
            return Response({'success': result, 'command': command_name})
        except Exception as e:
            return Response(
                {'detail': str(e), 'success': False},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
