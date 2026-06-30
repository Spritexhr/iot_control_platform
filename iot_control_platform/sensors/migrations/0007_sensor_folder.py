from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("resource_folders", "0001_initial"), ("sensors", "0006_remove_sensor_plant_fields")]
    operations = [
        migrations.AddField(
            model_name="sensor", name="folder",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sensors", to="resource_folders.resourcefolder", verbose_name="管理文件夹"),
        )
    ]
