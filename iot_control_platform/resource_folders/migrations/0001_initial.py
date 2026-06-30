from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="ResourceFolder",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, verbose_name="文件夹名称")),
                ("resource_type", models.CharField(choices=[("sensor", "传感器"), ("device", "设备")], db_index=True, max_length=10, verbose_name="资源类型")),
                ("sort_order", models.IntegerField(db_index=True, default=0, verbose_name="显示顺序")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
                ("parent", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="children", to="resource_folders.resourcefolder", verbose_name="上级文件夹")),
            ],
            options={"verbose_name": "资源文件夹", "verbose_name_plural": "资源文件夹", "ordering": ["sort_order", "id"]},
        ),
        migrations.AddConstraint(
            model_name="resourcefolder",
            constraint=models.UniqueConstraint(fields=("resource_type", "parent", "name"), name="uniq_resource_folder_sibling_name"),
        ),
    ]
