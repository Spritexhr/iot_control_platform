from django.db import migrations, models


def init_sort_order(apps, schema_editor):
    """已有传感器按 -created_at 顺序赋值 sort_order = 1, 2, ...，保持当前显示顺序。"""
    Sensor = apps.get_model('sensors', 'Sensor')
    for index, sensor in enumerate(Sensor.objects.order_by('-created_at'), start=1):
        sensor.sort_order = index
        sensor.save(update_fields=['sort_order'])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('sensors', '0003_alter_sensor_sensor_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='sensor',
            name='sort_order',
            field=models.IntegerField(
                db_index=True,
                default=0,
                help_text='数值越小越靠前；新建项默认 0 排在最前，由前端拖拽更新',
                verbose_name='显示顺序',
            ),
        ),
        migrations.AlterModelOptions(
            name='sensor',
            options={
                'ordering': ['sort_order', '-created_at'],
                'verbose_name': '传感器',
                'verbose_name_plural': '传感器列表',
            },
        ),
        migrations.RunPython(init_sort_order, reverse_code=noop),
    ]
