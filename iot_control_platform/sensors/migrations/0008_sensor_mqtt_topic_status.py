from django.db import migrations, models
from django.db.models import F, Value
from django.db.models.functions import Concat


def backfill_status_topics(apps, schema_editor):
    Sensor = apps.get_model('sensors', 'Sensor')
    Sensor.objects.update(
        mqtt_topic_data=Concat(
            Value('iot/sensors/'),
            F('sensor_id'),
            Value('/data'),
        ),
        mqtt_topic_status=Concat(
            Value('iot/sensors/'),
            F('sensor_id'),
            Value('/status'),
        ),
        mqtt_topic_control=Concat(
            Value('iot/sensors/'),
            F('sensor_id'),
            Value('/control'),
        ),
    )


def clear_status_topics(apps, schema_editor):
    Sensor = apps.get_model('sensors', 'Sensor')
    Sensor.objects.update(mqtt_topic_status='')


class Migration(migrations.Migration):
    dependencies = [
        ('sensors', '0007_sensor_folder'),
    ]

    operations = [
        migrations.AddField(
            model_name='sensor',
            name='mqtt_topic_status',
            field=models.CharField(blank=True, max_length=200, verbose_name='状态主题'),
        ),
        migrations.RunPython(backfill_status_topics, clear_status_topics),
    ]
