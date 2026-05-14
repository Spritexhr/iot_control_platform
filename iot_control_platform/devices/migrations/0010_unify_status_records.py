"""
设备侧重构：对齐传感器状态记录 + 合并 state_fields/config_parameters

1) DeviceData 新增 event_name 列，从 data['event'] 搬迁
2) DeviceType.state_fields 并入 config_parameters（去重保序），随后 drop
3) DeviceData 重命名为 DeviceStatusCollection，related_name 'data_records' → 'status_records'
"""
from django.db import migrations, models
import django.db.models.deletion


def forward_extract_event(apps, schema_editor):
    """把每条 DeviceData.data['event'] 提取到独立的 event_name 列。"""
    DeviceData = apps.get_model('devices', 'DeviceData')
    for rec in DeviceData.objects.all():
        data = rec.data if isinstance(rec.data, dict) else {}
        event = data.pop('event', None)
        if event is not None:
            rec.event_name = str(event)
            rec.data = data
            rec.save(update_fields=['event_name', 'data'])


def reverse_inject_event(apps, schema_editor):
    """回滚：把 event_name 写回 data['event']（仅在 reverse 该 migration 时使用）。"""
    DeviceData = apps.get_model('devices', 'DeviceData')
    for rec in DeviceData.objects.all():
        if rec.event_name:
            data = rec.data if isinstance(rec.data, dict) else {}
            data['event'] = rec.event_name
            rec.data = data
            rec.save(update_fields=['data'])


def forward_merge_config(apps, schema_editor):
    """把 DeviceType.state_fields 并入 config_parameters，去重保序（config_parameters 优先）。"""
    DeviceType = apps.get_model('devices', 'DeviceType')
    for dt in DeviceType.objects.all():
        sf = dt.state_fields if isinstance(dt.state_fields, list) else []
        cp = dt.config_parameters if isinstance(dt.config_parameters, list) else []
        merged = []
        for x in cp:
            if x not in merged:
                merged.append(x)
        for x in sf:
            if x not in merged:
                merged.append(x)
        dt.config_parameters = merged
        dt.save(update_fields=['config_parameters'])


def reverse_split_config(apps, schema_editor):
    """合并是有损操作，原 state_fields / config_parameters 的分组无法精确恢复，留 noop。"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('devices', '0009_device_sort_order'),
    ]

    operations = [
        # ===== 1. DeviceData 加 event_name 列 + 搬迁数据 =====
        migrations.AddField(
            model_name='devicedata',
            name='event_name',
            field=models.CharField(
                blank=True,
                help_text='状态事件标签，如 online / offline / interval_updated',
                max_length=100,
                verbose_name='事件名',
            ),
        ),
        migrations.RunPython(forward_extract_event, reverse_inject_event),

        # ===== 2. DeviceType.state_fields 并入 config_parameters，drop state_fields =====
        migrations.RunPython(forward_merge_config, reverse_split_config),
        migrations.RemoveField(
            model_name='devicetype',
            name='state_fields',
        ),
        migrations.AlterField(
            model_name='devicetype',
            name='config_parameters',
            field=models.JSONField(
                default=list,
                help_text='该类型设备的所有可读字段名（状态值 + 配置项合并）。示例：["power_state", "brightness", "heartbeat_interval"]',
                verbose_name='配置参数列表',
            ),
        ),

        # ===== 3. DeviceData 重命名 + related_name + 元数据对齐 =====
        migrations.RenameModel(
            old_name='DeviceData',
            new_name='DeviceStatusCollection',
        ),
        migrations.AlterModelOptions(
            name='devicestatuscollection',
            options={
                'ordering': ['-timestamp'],
                'verbose_name': '设备状态',
                'verbose_name_plural': '设备状态记录',
            },
        ),
        migrations.AlterField(
            model_name='devicestatuscollection',
            name='device',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='status_records',
                to='devices.device',
                verbose_name='设备',
            ),
        ),
        migrations.AlterField(
            model_name='devicestatuscollection',
            name='data',
            field=models.JSONField(
                help_text="设备上报的状态字段，如：{'power_state': true, 'brightness': 80}",
                verbose_name='状态内容',
            ),
        ),
        migrations.AlterField(
            model_name='devicestatuscollection',
            name='timestamp',
            field=models.DateTimeField(
                db_index=True,
                help_text='状态记录的时间戳',
                verbose_name='状态时间',
            ),
        ),

        # ===== 4. RenameModel 后索引名 hash 重算，同步重命名 =====
        migrations.RenameIndex(
            model_name='devicestatuscollection',
            new_name='devices_dev_device__c8b20f_idx',
            old_name='devices_dev_device__246e80_idx',
        ),
        migrations.RenameIndex(
            model_name='devicestatuscollection',
            new_name='devices_dev_timesta_e69fed_idx',
            old_name='devices_dev_timesta_b1901d_idx',
        ),
    ]
