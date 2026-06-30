import logging
import io
import contextlib
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from config.permissions import IsSuperuser
from rest_framework.response import Response
from django.db.models import Q
from .models import AutomationRule, ControlScheme
from .serializers import (
    AutomationRuleListSerializer,
    AutomationRuleDetailSerializer,
    AutomationRuleCreateUpdateSerializer,
    ControlSchemeSerializer,
    ControlSchemeCreateUpdateSerializer,
)
from .resources import RuleResourceUnavailable, effective_device_list

logger = logging.getLogger(__name__)


_CAPTURE_LOGGERS = ('automation', 'services.devices_service', 'services.sensors_service')


class _LogCaptureHandler(logging.Handler):
    """临时 handler，在规则执行期间捕获 INFO 及以上级别的应用日志"""

    def __init__(self):
        super().__init__(level=logging.INFO)
        self.records: list[dict] = []

    def emit(self, record):
        self.records.append({
            'level': record.levelname,
            'message': f'[{record.name}] {record.getMessage()}',
        })


class AutomationRuleViewSet(viewsets.ModelViewSet):
    """
    自动化规则 CRUD API
    创建、修改、删除仅限超级用户；执行、启动、停止仅限工作人员；非工作人员仅可查看
    """
    queryset = AutomationRule.objects.select_related('project', 'section').all()

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), IsSuperuser()]
        if self.action in ('execute', 'launch', 'stop'):
            return [IsAuthenticated(), IsAdminUser()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return AutomationRuleDetailSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return AutomationRuleCreateUpdateSerializer
        return AutomationRuleListSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        # 搜索
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(script_id__icontains=search)
                | Q(description__icontains=search)
            )
        project = self.request.query_params.get('project')
        section = self.request.query_params.get('section')
        if project:
            qs = qs.filter(project_id=project)
        if section:
            qs = qs.filter(section_id=section)
        return qs

    def _ensure_resources_available(self, rule):
        try:
            effective_device_list(rule)
        except RuleResourceUnavailable as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return None

    @action(detail=True, methods=['post'], url_path='launch')
    def launch(self, request, pk=None):
        """启动轮询：标记规则为持续轮询状态，可附带轮询间隔"""
        rule = self.get_object()
        invalid_response = self._ensure_resources_available(rule)
        if invalid_response:
            return invalid_response
        poll_interval = request.data.get('poll_interval')
        if poll_interval is not None:
            try:
                poll_interval = max(1, int(poll_interval))
                rule.poll_interval = poll_interval
            except (ValueError, TypeError):
                pass
        rule.is_launched = True
        rule.process_status = 'running'
        rule.error_message = ''
        rule.last_run_time = None  # 重新启动时清空上次执行时间
        rule.save(update_fields=['is_launched', 'process_status', 'error_message',
                                 'poll_interval', 'last_run_time', 'updated_at'])
        return Response({
            'id': rule.id,
            'is_launched': rule.is_launched,
            'process_status': rule.process_status,
            'poll_interval': rule.poll_interval,
        })

    @action(detail=True, methods=['post'], url_path='stop')
    def stop(self, request, pk=None):
        """停止轮询：标记规则为停止状态，可附带原因和错误信息"""
        rule = self.get_object()
        reason = request.data.get('reason', 'user')
        error_message = request.data.get('error_message', '')

        rule.is_launched = False
        if reason == 'error':
            rule.process_status = 'error_stopped'
            rule.error_message = error_message
        else:
            rule.process_status = 'stopped_by_user'
            rule.error_message = ''
        rule.save(update_fields=['is_launched', 'process_status', 'error_message', 'updated_at'])
        return Response({
            'id': rule.id,
            'is_launched': rule.is_launched,
            'process_status': rule.process_status,
            'error_message': rule.error_message,
        })

    @action(detail=False, methods=['get'], url_path='available-sources')
    def available_sources(self, request):
        """返回全局资源，或指定项目房间中已导入的资源。"""
        from sensors.models import Sensor
        from devices.models import Device
        from projects.models import ProjectSection

        project_id = request.query_params.get('project')
        section_id = request.query_params.get('section')
        if bool(project_id) != bool(section_id):
            return Response(
                {'detail': 'project 与 section 必须同时提供'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if project_id and section_id:
            try:
                section = ProjectSection.objects.get(pk=section_id, project_id=project_id)
            except (ProjectSection.DoesNotExist, ValueError):
                return Response({'detail': '项目或房间不存在'}, status=status.HTTP_404_NOT_FOUND)
            sensor_members = section.sensor_members.select_related(
                'sensor', 'sensor__sensor_type'
            ).order_by('sort_order', 'id')
            device_members = section.device_members.select_related(
                'device', 'device__device_type'
            ).order_by('sort_order', 'id')

            sensors_data = []
            seen_sensors = set()
            for member in sensor_members:
                sensor = member.sensor
                if sensor.sensor_id in seen_sensors:
                    continue
                seen_sensors.add(sensor.sensor_id)
                fields = sensor.sensor_type.data_fields if sensor.sensor_type_id else []
                sensors_data.append({
                    'id': sensor.sensor_id,
                    'name': member.tag or sensor.name,
                    'data_fields': fields,
                })

            devices_data = []
            for member in device_members:
                device = member.device
                commands = (
                    list(device.device_type.commands.keys())
                    if device.device_type_id and isinstance(device.device_type.commands, dict)
                    else []
                )
                devices_data.append({
                    'id': device.device_id,
                    'name': member.tag or device.name,
                    'commands': commands,
                })
            return Response({'sensors': sensors_data, 'devices': devices_data})

        sensors_data = []
        for s in Sensor.objects.select_related('sensor_type').order_by('name'):
            fields = s.sensor_type.data_fields if s.sensor_type else []
            sensors_data.append({
                'id': s.sensor_id,
                'name': s.name,
                'data_fields': fields,
            })

        devices_data = []
        for d in Device.objects.select_related('device_type').order_by('name'):
            cmds = list(d.device_type.commands.keys()) if d.device_type and d.device_type.commands else []
            devices_data.append({
                'id': d.device_id,
                'name': d.name,
                'commands': cmds,
            })

        return Response({'sensors': sensors_data, 'devices': devices_data})

    @action(detail=True, methods=['post'], url_path='execute')
    def execute(self, request, pk=None):
        """
        手动执行一次规则，捕获 print 输出和 WARNING+ 日志并返回
        """
        rule = self.get_object()
        invalid_response = self._ensure_resources_available(rule)
        if invalid_response:
            return invalid_response

        stdout_capture = io.StringIO()
        log_capture = _LogCaptureHandler()
        captured_loggers = [logging.getLogger(name) for name in _CAPTURE_LOGGERS]
        for lg in captured_loggers:
            lg.addHandler(log_capture)
        try:
            with contextlib.redirect_stdout(stdout_capture):
                success = rule.execute()
            output = stdout_capture.getvalue()
            return Response({
                'success': success,
                'output': output,
                'logs': log_capture.records,
                'rule_name': rule.name,
            })
        except Exception as e:
            logger.exception("执行自动化规则失败 [%s]", rule.name)
            output = stdout_capture.getvalue()
            return Response({
                'success': False,
                'output': output,
                'logs': log_capture.records,
                'error': str(e),
                'rule_name': rule.name,
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            for lg in captured_loggers:
                lg.removeHandler(log_capture)


class ControlSchemeViewSet(viewsets.ModelViewSet):
    """
    控制方案（双位 / PI / PID）CRUD + 启停 + 单拍测试 + 模板。
    增删改仅限超级用户；启停/试运行仅限工作人员；非工作人员仅可查看。
    """
    queryset = ControlScheme.objects.select_related(
        'sensor_member__sensor', 'device_member__device', 'project', 'section'
    ).all()

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), IsSuperuser()]
        if self.action in ('enable', 'disable', 'step'):
            return [IsAuthenticated(), IsAdminUser()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return ControlSchemeCreateUpdateSerializer
        return ControlSchemeSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        project = self.request.query_params.get('project')
        section = self.request.query_params.get('section')
        if project:
            qs = qs.filter(project_id=project)
        if section:
            qs = qs.filter(section_id=section)
        return qs

    @action(detail=True, methods=['post'], url_path='enable')
    def enable(self, request, pk=None):
        """启用控制环：重置内部运行态并标记为运行中。"""
        scheme = self.get_object()
        scheme.reset_runtime_state()
        scheme.is_enabled = True
        scheme.status = 'running'
        scheme.error_message = ''
        scheme.last_run_time = None
        scheme.save(update_fields=['runtime_state', 'is_enabled', 'status',
                                   'error_message', 'last_run_time', 'updated_at'])
        return Response(ControlSchemeSerializer(scheme).data)

    @action(detail=True, methods=['post'], url_path='disable')
    def disable(self, request, pk=None):
        """停用控制环。"""
        scheme = self.get_object()
        scheme.is_enabled = False
        scheme.status = 'idle'
        scheme.error_message = ''
        scheme.save(update_fields=['is_enabled', 'status', 'error_message', 'updated_at'])
        return Response(ControlSchemeSerializer(scheme).data)

    @action(detail=True, methods=['post'], url_path='step')
    def step(self, request, pk=None):
        """手动跑一拍控制（真实下发），返回算得的 PV / 输出 / 命令，供前端"试一下"。"""
        from .controllers import run_control_scheme
        scheme = self.get_object()
        send = request.data.get('send', True)
        result = run_control_scheme(scheme, send=bool(send))
        return Response({**result, 'scheme': ControlSchemeSerializer(scheme).data})

    @action(detail=False, methods=['get'], url_path='templates')
    def templates(self, request):
        """返回三套控制方案模板（参数 schema + 默认值），供前端表单使用。"""
        from .controllers import CONTROL_TEMPLATES
        return Response({'templates': CONTROL_TEMPLATES})
