from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("devices", "0012_remove_device_plant_fields"), ("resource_folders", "0001_initial")]
    operations = [
        migrations.AddField(
            model_name="device", name="folder",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="devices", to="resource_folders.resourcefolder", verbose_name="管理文件夹"),
        )
    ]
