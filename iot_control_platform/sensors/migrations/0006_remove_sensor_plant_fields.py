from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sensors', '0005_sensor_plant_code_sensor_plant_metadata'),
    ]

    operations = [
        migrations.RemoveField(model_name='sensor', name='plant_code'),
        migrations.RemoveField(model_name='sensor', name='plant_metadata'),
    ]
