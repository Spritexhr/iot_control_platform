from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sensors', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='Sensor',
            old_name='device_id',
            new_name='sensor_id',
        ),
        migrations.AlterField(
            model_name='Sensor',
            name='name',
            field=models.CharField(max_length=100, verbose_name='传感器名称'),
        ),
        migrations.AlterField(
            model_name='Sensor',
            name='description',
            field=models.TextField(blank=True, verbose_name='传感器描述'),
        ),
        migrations.AlterField(
            model_name='Sensor',
            name='location',
            field=models.CharField(blank=True, max_length=200, verbose_name='传感器位置'),
        ),
        migrations.AlterField(
            model_name='SensorType',
            name='SensorType_id',
            field=models.CharField(
                db_index=True, max_length=50, unique=True, verbose_name='传感器类型唯一ID'
            ),
        ),
    ]
