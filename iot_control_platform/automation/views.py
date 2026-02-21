import logging
import io
import contextlib
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from .models import AutomationRule
from .serializers import (
    AutomationRuleListSerializer,
    AutomationRuleDetailSerializer,
    AutomationRuleCreateUpdateSerializer,
)

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
    支持搜索、手动执行、启动/停止轮询
    """
    queryset = AutomationRule.objects.all()

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
        return qs

    @action(detail=True, methods=['post'], url_path='launch')
    def launch(self, request, pk=None):
        """启动轮询：标记规则为持续轮询状态，可附带轮询间隔"""
        rule = self.get_object()
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
        rule.save(update_fields=['is_launched', 'process_status', 'error_message',
                                 'poll_interval', 'updated_at'])
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

    @action(detail=True, methods=['post'], url_path='execute')
    def execute(self, request, pk=None):
        """
        手动执行一次规则，捕获 print 输出和 WARNING+ 日志并返回
        """
        rule = self.get_object()

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
