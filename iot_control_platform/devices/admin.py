"""
设备管理后台配置
参考 sensors/admin 结构实现
"""
from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.shortcuts import redirect
from django.contrib import messages
from django.utils import timezone
from .models import DeviceType, Device, DeviceData
from services.devices_service.device_command_send_service import device_command_send_service


@admin.register(DeviceType)
class DeviceTypeAdmin(admin.ModelAdmin):
    """设备类型管理"""

    list_display = ['DeviceType_id', 'name', 'devices_count', 'created_at']
    search_fields = ['DeviceType_id', 'name', 'description']

    fieldsets = [
        ('基本信息', {
            'fields': ['DeviceType_id', 'name', 'description']
        }),
        ('状态与配置', {
            'fields': ['state_fields', 'config_parameters', 'commands'],
            'description': '使用JSON格式。commands 格式参见 SensorType'
        }),
    ]

    def devices_count(self, obj):
        """设备数量"""
        count = obj.devices.count()
        return format_html('<b>{}</b>', count)
    devices_count.short_description = '设备数量'


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    """设备管理"""

    list_display = ['device_id', 'name', 'device_type', 'latest_data_time', 'online_indicator', 'created_at']
    list_filter = ['device_type', 'is_online', 'created_at']
    search_fields = ['device_id', 'name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'mqtt_topic_data', 'mqtt_topic_control', 'command_buttons_detail_display']

    fieldsets = [
        ('基本信息', {
            'fields': ['device_id', 'name', 'device_type', 'description', 'location']
        }),
        ('命令控制', {
            'fields': ['command_buttons_detail_display'],
            'description': '发送控制命令到该设备（需先保存设备；需在设备类型中配置 commands）'
        }),
        ('MQTT配置', {
            'fields': ['mqtt_topic_data', 'mqtt_topic_control'],
            'description': '保存时自动生成，格式：iot/devices/{device_id}/xxx'
        }),
        ('状态信息', {
            'fields': ['is_online', 'last_seen']
        }),
        ('时间戳', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]

    actions = ['check_online_status']

    def get_readonly_fields(self, request, obj=None):
        """确保命令控制区域在添加和编辑页都显示"""
        base = list(super().get_readonly_fields(request, obj))
        if 'command_buttons_detail_display' not in base:
            base.append('command_buttons_detail_display')
        return base

    def latest_data_time(self, obj):
        """最新数据时间"""
        latest = obj.data_records.first()
        if latest:
            time_diff = timezone.now() - latest.timestamp
            if time_diff.total_seconds() < 300:
                color = 'green'
            elif time_diff.total_seconds() < 3600:
                color = 'orange'
            else:
                color = 'red'
            return format_html(
                '<span style="color: {};">{}</span>',
                color,
                latest.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            )
        return format_html('<span style="color: gray;">{}</span>', '无数据')
    latest_data_time.short_description = '最新数据时间'

    def online_indicator(self, obj):
        """在线指示器"""
        if obj.is_online:
            return format_html('<span style="color: green; font-weight: bold;">{}</span>', '✓ 在线')
        return format_html('<span style="color: red;">{}</span>', '✗ 离线')
    online_indicator.short_description = '在线状态'

    def check_online_status(self, request, queryset):
        """检查在线状态"""
        for device in queryset:
            device.check_online_status()
        self.message_user(request, f'已检查 {queryset.count()} 个设备的在线状态')
    check_online_status.short_description = '检查在线状态'

    def change_view(self, request, object_id, form_url='', extra_context=None):
        """拦截 POST：当为发送命令时处理并重定向，否则走默认逻辑"""
        if request.method == 'POST' and request.POST.get('admin_send_command'):
            cmd_name = request.POST.get('admin_send_command')
            try:
                device = Device.objects.get(pk=object_id)
            except Device.DoesNotExist:
                messages.error(request, '设备不存在')
                return redirect('admin:devices_device_changelist')

            commands = device_command_send_service.show_device_control_commands(device)
            if cmd_name not in commands:
                messages.error(request, f'未定义的命令: {cmd_name}')
            else:
                command_info = commands[cmd_name]
                params = command_info.get('params') or []
                param_dict = {}
                for p in params:
                    val = request.POST.get(f'param_{p}')
                    if val is not None:
                        try:
                            param_dict[p] = int(val) if str(val).isdigit() else val
                        except (ValueError, TypeError):
                            param_dict[p] = val

                success = device_command_send_service.send_custom_command(
                    device.device_id, cmd_name, param_dict if param_dict else None
                )
                desc = command_info.get('description', cmd_name)
                if success:
                    messages.success(request, f'命令「{desc}」已成功发送到 {device.device_id}')
                else:
                    messages.error(request, f'命令「{desc}」发送失败，请检查 MQTT 连接')

            return redirect('admin:devices_device_change', object_id)

        return super().change_view(request, object_id, form_url, extra_context)

    def command_buttons_detail_display(self, obj):
        """在设备详情页显示可用的命令按钮（通过主表单 POST，无额外 URL）"""
        if not obj or not obj.pk:
            return format_html('<p style="color: gray;">{}</p>', '请先保存设备以显示命令按钮')

        commands = device_command_send_service.show_device_control_commands(obj)
        if not commands:
            return format_html(
                '<p style="color: gray;">该设备类型「{}」未定义控制命令，可在设备类型中配置 commands 字段</p>',
                obj.device_type.name if obj.device_type else '未知'
            )

        buttons = []
        for cmd_name, cmd_info in commands.items():
            desc = cmd_info.get('description', cmd_name)
            params = cmd_info.get('params') or []
            if params:
                inputs_html = mark_safe(''.join(
                    format_html('<label>{}: <input type="number" name="param_{}" value="120" style="width:80px"></label> ', p, p)
                    for p in params
                ))
                buttons.append(format_html(
                    '<span style="display:inline-flex;align-items:center;gap:4px;margin-right:12px">'
                    '{}<button type="submit" name="admin_send_command" value="{}" class="button">{}</button></span>',
                    inputs_html, cmd_name, desc
                ))
            else:
                buttons.append(format_html(
                    '<button type="submit" name="admin_send_command" value="{}" class="button" '
                    'onclick="return confirm(\'确定发送命令「{}」到设备 {}？\');">{}</button>',
                    cmd_name, desc, obj.device_id, desc
                ))

        buttons_html = mark_safe(' '.join(str(b) for b in buttons))
        return format_html('<div style="display: flex; flex-wrap: wrap; gap: 8px;">{}</div>', buttons_html)
    command_buttons_detail_display.short_description = '控制命令'


@admin.register(DeviceData)
class DeviceDataAdmin(admin.ModelAdmin):
    """设备数据管理"""

    list_display = ['device_device_id', 'data_preview', 'timestamp', 'received_at']
    list_filter = ['device__device_type', 'timestamp', 'received_at']
    search_fields = ['device__device_id', 'device__name']
    readonly_fields = ['device', 'data', 'timestamp', 'received_at']
    date_hierarchy = 'timestamp'

    fieldsets = [
        ('数据信息', {
            'fields': ['device', 'data', 'timestamp', 'received_at']
        }),
    ]

    def device_device_id(self, obj):
        """设备ID"""
        return obj.device.device_id
    device_device_id.short_description = '设备ID'
    device_device_id.admin_order_field = 'device__device_id'

    def data_preview(self, obj):
        """数据预览"""
        import json
        try:
            data_str = json.dumps(obj.data, ensure_ascii=False)
            if len(data_str) > 100:
                data_str = data_str[:100] + '...'
            return format_html('<code>{}</code>', data_str)
        except Exception:
            return str(obj.data)
    data_preview.short_description = '数据内容'

    def has_add_permission(self, request):
        """禁止手动添加数据"""
        return False

    def has_change_permission(self, request, obj=None):
        """禁止修改数据"""
        return False
