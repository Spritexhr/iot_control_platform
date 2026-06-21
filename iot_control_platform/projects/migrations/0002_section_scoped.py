"""把成员/视图收紧为「房间（分区）级」隔离模型。

- ProjectView 新增 section 外键（先建为可空，回填后收紧为必填）。
- 已有视图回填到其项目的首个分区。
- 成员 section 由可空(SET_NULL) 收紧为必填(CASCADE)。
- 唯一约束由项目级改为房间级（支持同一传感器/设备在不同房间复用）。
"""
import django.db.models.deletion
from django.db import migrations, models


def assign_views_to_first_section(apps, schema_editor):
    """已有视图（无分区）分配到所属项目的首个分区；项目无分区则删除该视图。"""
    ProjectView = apps.get_model("projects", "ProjectView")
    ProjectSection = apps.get_model("projects", "ProjectSection")
    for view in ProjectView.objects.all():
        first = (
            ProjectSection.objects.filter(project_id=view.project_id)
            .order_by("sort_order", "id")
            .first()
        )
        if first is not None:
            view.section_id = first.id
            view.save(update_fields=["section"])
        else:
            view.delete()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0001_initial"),
    ]

    operations = [
        # 1) 移除旧的项目级唯一约束
        migrations.RemoveConstraint(
            model_name="projectsensormember",
            name="uniq_project_sensor_data_key",
        ),
        migrations.RemoveConstraint(
            model_name="projectdevicemember",
            name="uniq_project_device",
        ),
        # 2) ProjectView 加 section（先可空，便于回填）
        migrations.AddField(
            model_name="projectview",
            name="section",
            field=models.ForeignKey(
                help_text="视图归属一个房间（分区），只能展示本房间成员",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="views",
                to="projects.projectsection",
                verbose_name="所属房间",
            ),
        ),
        # 3) 回填已有视图到首个分区
        migrations.RunPython(assign_views_to_first_section, noop),
        # 4) 成员 section 收紧为必填 + CASCADE
        migrations.AlterField(
            model_name="projectsensormember",
            name="section",
            field=models.ForeignKey(
                help_text="成员必属于一个房间（分区）；删除房间会一并删除其成员",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="sensor_members",
                to="projects.projectsection",
                verbose_name="所属房间",
            ),
        ),
        migrations.AlterField(
            model_name="projectdevicemember",
            name="section",
            field=models.ForeignKey(
                help_text="成员必属于一个房间（分区）；删除房间会一并删除其成员",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="device_members",
                to="projects.projectsection",
                verbose_name="所属房间",
            ),
        ),
        # 5) ProjectView.section 收紧为必填
        migrations.AlterField(
            model_name="projectview",
            name="section",
            field=models.ForeignKey(
                help_text="视图归属一个房间（分区），只能展示本房间成员",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="views",
                to="projects.projectsection",
                verbose_name="所属房间",
            ),
        ),
        # 6) 新的房间级唯一约束
        migrations.AddConstraint(
            model_name="projectsensormember",
            constraint=models.UniqueConstraint(
                fields=["section", "sensor", "data_key"],
                name="uniq_section_sensor_data_key",
            ),
        ),
        migrations.AddConstraint(
            model_name="projectdevicemember",
            constraint=models.UniqueConstraint(
                fields=["section", "device"],
                name="uniq_section_device",
            ),
        ),
    ]
