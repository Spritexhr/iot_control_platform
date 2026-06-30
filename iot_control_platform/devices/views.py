from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta
from .models import DeviceType, Device, DeviceStatusCollection
from .serializers import (
    DeviceTypeSerializer,
    DeviceListSerializer,
    DeviceDetailSerializer,
    DeviceCreateUpdateSerializer,
    DeviceStatusSerializer,
)
from resource_folders.models import ResourceFolder
from resource_folders.pagination import ResourcePageNumberPagination


class DeviceTypeViewSet(viewsets.ModelViewSet):
    """设备类型 CRUD API，创建/修改/删除仅限工作人员（is_staff）"""
    queryset = DeviceType.objects.annotate(_device_count=Count('devices')).order_by('name')
    serializer_class = DeviceTypeSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), IsAdminUser()]
        return [IsAuthenticated()]


class DeviceViewSet(viewsets.ModelViewSet):
    """
    设备 CRUD API
    支持按 device_id 查找、筛选、搜索
    创建/修改/删除/发送命令仅限工作人员，非工作人员仅可查看
    """
    queryset = Device.objects.select_related('device_type', 'folder').prefetch_related(
        'status_records'
    ).all()
    lookup_field = 'device_id'
    pagination_class = ResourcePageNumberPagination

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy', 'send_command', 'bulk_move'):
            return [IsAuthenticated(), IsAdminUser()]
        return [IsAuthenticated()]

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
        folder = self.request.query_params.get('folder')
        if folder == 'unfiled':
            qs = qs.filter(folder__isnull=True)
        elif folder:
            if not folder.isdigit():
                return qs.none()
            qs = qs.filter(folder_id=int(folder), folder__resource_type=ResourceFolder.DEVICE)
        return qs

    @action(detail=False, methods=['post'], url_path='bulk-move')
    def bulk_move(self, request):
        device_ids = request.data.get('device_ids')
        folder_id = request.data.get('folder')
        if not isinstance(device_ids, list) or not device_ids or not all(isinstance(x, str) for x in device_ids):
            return Response({'detail': 'device_ids 必须是非空字符串数组'}, status=400)
        folder = None
        if folder_id is not None:
            try:
                folder = ResourceFolder.objects.get(pk=folder_id, resource_type=ResourceFolder.DEVICE)
            except ResourceFolder.DoesNotExist:
                return Response({'detail': '设备文件夹不存在'}, status=400)
        unique_ids = set(device_ids)
        qs = Device.objects.filter(device_id__in=unique_ids)
        if qs.count() != len(unique_ids):
            return Response({'detail': '包含不存在的设备'}, status=400)
        updated = qs.update(folder=folder)
        return Response({'updated': updated})

    @action(detail=True, methods=['get'], url_path='status')
    def device_status(self, request, device_id=None):
        """获取设备历史状态记录，支持时间范围查询。"""
        device = self.get_object()
        hours = int(request.query_params.get('hours', 1))
        limit = int(request.query_params.get('limit', 200))
        start_time = timezone.now() - timedelta(hours=hours)
        records = DeviceStatusCollection.objects.filter(
            device=device, timestamp__gte=start_time
        ).order_by('-timestamp')[:limit]
        serializer = DeviceStatusSerializer(records, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='reorder',
            permission_classes=[IsAuthenticated, IsAdminUser])
    def reorder(self, request):
        """
        批量更新设备显示顺序。
        请求体：{"order": ["device_id_a", "device_id_b", ...]}
        按数组顺序写入 sort_order = 1, 2, ...，未列出的设备保持原值。
        """
        order = request.data.get('order')
        if not isinstance(order, list) or not all(isinstance(x, str) for x in order):
            return Response(
                {'detail': 'order 必须是 device_id 字符串数组'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        page = request.data.get('page')
        page_size = request.data.get('page_size')
        folder = request.data.get('folder')
        if page is not None or page_size is not None:
            try:
                page = int(page)
                page_size = int(page_size)
                if page < 1 or page_size < 1 or page_size > 96:
                    raise ValueError
            except (TypeError, ValueError):
                return Response({'detail': 'page/page_size 参数无效'}, status=400)

            scope = Device.objects.all()
            if folder == 'unfiled' or folder is None:
                scope = scope.filter(folder__isnull=True)
            else:
                scope = scope.filter(folder_id=folder)
            all_ids = list(
                scope.order_by('sort_order', '-created_at').values_list('device_id', flat=True)
            )
            start = (page - 1) * page_size
            page_ids = all_ids[start:start + page_size]
            if len(order) != len(page_ids) or set(order) != set(page_ids):
                return Response({'detail': '排序内容与当前页资源不一致，请刷新后重试'}, status=409)
            all_ids[start:start + len(page_ids)] = order
            rows = list(Device.objects.filter(device_id__in=all_ids))
            row_map = {row.device_id: row for row in rows}
            for index, device_id in enumerate(all_ids, start=1):
                row_map[device_id].sort_order = index
            with transaction.atomic():
                Device.objects.bulk_update(rows, ['sort_order'])
        else:
            # 兼容旧客户端：仅更新请求中给出的顺序。
            with transaction.atomic():
                for index, device_id in enumerate(order, start=1):
                    Device.objects.filter(device_id=device_id).update(sort_order=index)
        return Response({'updated': len(order)})

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
