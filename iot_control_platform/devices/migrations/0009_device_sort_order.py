from django.db import migrations, models


def init_sort_order(apps, schema_editor):
    """已有设备按 -created_at 顺序赋值 sort_order = 1, 2, ...，保持当前显示顺序。"""
    Device = apps.get_model('devices', 'Device')
    for index, device in enumerate(Device.objects.order_by('-created_at'), start=1):
        device.sort_order = index
        device.save(update_fields=['sort_order'])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('devices', '0008_remove_icon_field'),
    ]

    operations = [
        migrations.AddField(
            model_name='device',
            name='sort_order',
            field=models.IntegerField(
                db_index=True,
                default=0,
                help_text='数值越小越靠前；新建项默认 0 排在最前，由前端拖拽更新',
                verbose_name='显示顺序',
            ),
        ),
        migrations.AlterModelOptions(
            name='device',
            options={
                'ordering': ['sort_order', '-created_at'],
                'verbose_name': '设备',
                'verbose_name_plural': '设备列表',
            },
        ),
        migrations.RunPython(init_sort_order, reverse_code=noop),
    ]
