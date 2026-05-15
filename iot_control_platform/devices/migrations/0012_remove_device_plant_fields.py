from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('devices', '0011_device_plant_code_device_plant_metadata'),
    ]

    operations = [
        migrations.RemoveField(model_name='device', name='plant_code'),
        migrations.RemoveField(model_name='device', name='plant_metadata'),
    ]
