# Generated manually - 合并 AutomationScript 到 AutomationRule

from django.db import migrations, models


def migrate_script_to_rule(apps, schema_editor):
    """将 AutomationScript 数据迁移到 AutomationRule，并更新关联规则的 script_key"""
    AutomationScript = apps.get_model("automation", "AutomationScript")
    AutomationRule = apps.get_model("automation", "AutomationRule")

    for script in AutomationScript.objects.all():
        # 更新已关联此 script 的 rule（FK 列名为 script_id，新字段为 script_key）
        for rule in AutomationRule.objects.filter(script=script):
            rule.script_key = script.script_id
            rule.module_path = script.module_path
            rule.function_name = script.function_name
            rule.save()
        # 若无规则引用，则创建新规则
        if not AutomationRule.objects.filter(script=script).exists():
            AutomationRule.objects.create(
                name=script.name or script.script_id,
                description=script.description or "",
                is_enabled=script.is_enabled,
                script_key=script.script_id,
                module_path=script.module_path,
                function_name=script.function_name,
                automation_script="",
                device_list=[],
            )


def reverse_migrate(apps, schema_editor):
    """回滚：无法恢复 AutomationScript，仅清空新增字段"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("automation", "0003_add_automation_script_and_rule_script"),
    ]

    operations = [
        migrations.AddField(
            model_name="automationrule",
            name="script_key",
            field=models.CharField(
                blank=True,
                help_text="唯一标识，engine.run_script() 通过此 ID 调用。若设置则使用脚本文件，否则使用内联脚本。",
                max_length=80,
                null=True,
                unique=True,
                verbose_name="脚本ID",
            ),
        ),
        migrations.AddField(
            model_name="automationrule",
            name="module_path",
            field=models.CharField(
                blank=True,
                help_text="如 automation.script.humidity_overflow_print",
                max_length=200,
                null=True,
                verbose_name="模块路径",
            ),
        ),
        migrations.AddField(
            model_name="automationrule",
            name="function_name",
            field=models.CharField(
                default="run",
                max_length=50,
                verbose_name="函数名",
            ),
        ),
        migrations.RunPython(migrate_script_to_rule, reverse_migrate),
        migrations.RemoveField(
            model_name="automationrule",
            name="script",
        ),
        migrations.RenameField(
            model_name="automationrule",
            old_name="script_key",
            new_name="script_id",
        ),
        migrations.AlterField(
            model_name="automationrule",
            name="automation_script",
            field=models.TextField(
                blank=True,
                help_text="\n        Python 脚本，实现触发判断和执行逻辑（脚本文件模式留空）。\n        \n        可用变量：devices 字典，key 为 device_id，value 为包装对象。\n        \n        【传感器 Sensor】\n        - current_state: 最新 SensorData.data（来自 sensor.data_records）\n        - 数据字段由 SensorType.data_fields 定义，如 temperature、humidity\n        \n        【设备 Device】\n        - current_state: 最新 DeviceData.data（来自 device.data_records）\n        - send_command(name, params): 发送控制命令，命令名来自 DeviceType.commands\n        \n        返回值：True 执行成功，False 不满足条件或执行失败\n        ```python\n        sensor = devices.get('DHT11-WEMOS-001')\n        led = devices.get('SG_80_01')\n        if sensor and sensor.current_state:\n            temp = sensor.current_state.get('temperature', 0)\n            if temp > 30 and led:\n                led.send_command('high', {})\n                return True\n        return False\n        ```\n        ",
                verbose_name="内联脚本",
            ),
        ),
        migrations.DeleteModel(
            name="AutomationScript",
        ),
    ]
