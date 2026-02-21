# Generated manually for DeviceType structure alignment with SensorType

from django.db import migrations, models


def set_device_type_ids(apps, schema_editor):
    """为已有的 DeviceType 设置 DeviceType_id"""
    DeviceType = apps.get_model('devices', 'DeviceType')
    for dt in DeviceType.objects.all():
        dt.DeviceType_id = f"DT-{dt.id}"
        dt.save()


class Migration(migrations.Migration):

    dependencies = [
        ("devices", "0003_rename_fields_to_lists"),
    ]

    operations = [
        migrations.AddField(
            model_name="devicetype",
            name="DeviceType_id",
            field=models.CharField(
                db_index=True,
                max_length=50,
                null=True,
                verbose_name="设备类型唯一ID"
            ),
        ),
        migrations.AddField(
            model_name="devicetype",
            name="commands",
            field=models.JSONField(
                blank=True,
                default=dict,
                verbose_name="可用命令列表"
            ),
        ),
        migrations.RunPython(set_device_type_ids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="devicetype",
            name="DeviceType_id",
            field=models.CharField(
                db_index=True,
                max_length=50,
                unique=True,
                verbose_name="设备类型唯一ID",
                null=False,
            ),
        ),
    ]
