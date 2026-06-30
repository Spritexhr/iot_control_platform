from django.db import migrations


def remove_edge_medium(apps, schema_editor):
    """清除历史 P&ID 画布连线中不再使用的 data.medium。"""
    ProjectView = apps.get_model("projects", "ProjectView")
    for view in ProjectView.objects.filter(view_type="diagram").iterator():
        config = view.config
        if not isinstance(config, dict) or not isinstance(config.get("edges"), list):
            continue
        changed = False
        cleaned_edges = []
        for edge in config["edges"]:
            if not isinstance(edge, dict):
                cleaned_edges.append(edge)
                continue
            cleaned_edge = dict(edge)
            data = cleaned_edge.get("data")
            if isinstance(data, dict) and "medium" in data:
                cleaned_data = dict(data)
                cleaned_data.pop("medium", None)
                cleaned_edge["data"] = cleaned_data
                changed = True
            cleaned_edges.append(cleaned_edge)
        if changed:
            cleaned_config = dict(config)
            cleaned_config["edges"] = cleaned_edges
            ProjectView.objects.filter(pk=view.pk).update(config=cleaned_config)


class Migration(migrations.Migration):
    dependencies = [("projects", "0003_alter_projectview_view_type")]

    operations = [
        migrations.RunPython(remove_edge_medium, migrations.RunPython.noop),
    ]
