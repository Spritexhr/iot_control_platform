from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from devices.models import Device, DeviceType
from projects.models import Project, ProjectDeviceMember, ProjectSection, ProjectSensorMember
from sensors.models import Sensor, SensorType

from .models import AutomationRule
from .resources import RuleResourceUnavailable, effective_device_list
from .scheduler import _process_automation_rules


class ProjectAutomationRuleApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.superuser = user_model.objects.create_superuser(
            username="root", password="test-password", email="root@example.com"
        )
        self.staff = user_model.objects.create_user(
            username="staff", password="test-password", is_staff=True
        )
        self.viewer = user_model.objects.create_user(
            username="viewer", password="test-password"
        )

        self.sensor_type = SensorType.objects.create(
            SensorType_id="temperature-type",
            name="温度传感器",
            data_fields=["temperature"],
        )
        self.sensor = Sensor.objects.create(
            sensor_id="sensor-1",
            name="温度一",
            sensor_type=self.sensor_type,
        )
        self.other_sensor = Sensor.objects.create(
            sensor_id="sensor-2",
            name="温度二",
            sensor_type=self.sensor_type,
        )
        self.device_type = DeviceType.objects.create(
            DeviceType_id="relay-type",
            name="继电器",
            commands={"turn_on": {"params": []}},
        )
        self.device = Device.objects.create(
            device_id="device-1",
            name="继电器一",
            device_type=self.device_type,
        )
        self.other_device = Device.objects.create(
            device_id="device-2",
            name="继电器二",
            device_type=self.device_type,
        )
        self.project = Project.objects.create(code="P1", name="项目一")
        self.section = ProjectSection.objects.create(project=self.project, name="房间一")
        self.other_section = ProjectSection.objects.create(project=self.project, name="房间二")
        self.sensor_member = ProjectSensorMember.objects.create(
            project=self.project,
            section=self.section,
            sensor=self.sensor,
            tag="TT-1",
        )
        self.device_member = ProjectDeviceMember.objects.create(
            project=self.project,
            section=self.section,
            device=self.device,
            tag="K-1",
        )

    def rule_payload(self, **overrides):
        payload = {
            "name": "房间脚本",
            "script_id": "room_script",
            "project": self.project.id,
            "section": self.section.id,
            "script": "from engine import sensors\n\ndef loop():\n    return sensors.get('sensor-1') is not None",
            "device_list": [
                {"device_id": self.sensor.sensor_id, "device_type": "Sensor", "name": "温度"},
                {"device_id": self.device.device_id, "device_type": "Device", "name": "继电器"},
            ],
            "poll_interval": 5,
        }
        payload.update(overrides)
        return payload

    def create_rule(self, **overrides):
        self.client.force_authenticate(self.superuser)
        response = self.client.post(
            reverse("automation-rule-list"), self.rule_payload(**overrides), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        return AutomationRule.objects.get(pk=response.data["id"])

    def test_project_rule_only_accepts_imported_room_resources(self):
        self.client.force_authenticate(self.superuser)
        payload = self.rule_payload(
            device_list=[
                {"device_id": self.other_sensor.sensor_id, "device_type": "Sensor"},
            ]
        )
        response = self.client.post(reverse("automation-rule-list"), payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("未导入当前房间", str(response.data))

    def test_project_and_section_must_match(self):
        other_project = Project.objects.create(code="P2", name="项目二")
        wrong_section = ProjectSection.objects.create(project=other_project, name="房间")
        self.client.force_authenticate(self.superuser)
        response = self.client.post(
            reverse("automation-rule-list"),
            self.rule_payload(section=wrong_section.id),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("不属于所选项目", str(response.data))

    def test_available_sources_are_limited_to_imported_room_members(self):
        self.client.force_authenticate(self.viewer)
        response = self.client.get(
            reverse("automation-rule-available-sources"),
            {"project": self.project.id, "section": self.section.id},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([row["id"] for row in response.data["sensors"]], ["sensor-1"])
        self.assertEqual([row["id"] for row in response.data["devices"]], ["device-1"])

    def test_list_can_filter_by_project_and_section_and_exposes_scope(self):
        rule = self.create_rule()
        AutomationRule.objects.create(
            name="全局脚本", script_id="global_script", script="def loop(): return True"
        )
        self.client.force_authenticate(self.viewer)
        response = self.client.get(
            reverse("automation-rule-list"),
            {"project": self.project.id, "section": self.section.id},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rows = response.data.get("results", response.data)
        self.assertEqual([row["id"] for row in rows], [rule.id])
        self.assertEqual(rows[0]["project_code"], "P1")
        self.assertEqual(rows[0]["section_name"], "房间一")

    def test_scope_cannot_be_changed_after_creation(self):
        rule = self.create_rule()
        self.client.force_authenticate(self.superuser)
        response = self.client.patch(
            reverse("automation-rule-detail", args=[rule.id]),
            {"section": self.other_section.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("不能修改所属房间", str(response.data))

    def test_removed_member_blocks_execution_and_launch(self):
        rule = self.create_rule()
        self.sensor_member.delete()

        with self.assertRaises(RuleResourceUnavailable):
            effective_device_list(rule)

        self.client.force_authenticate(self.staff)
        execute_response = self.client.post(reverse("automation-rule-execute", args=[rule.id]))
        launch_response = self.client.post(reverse("automation-rule-launch", args=[rule.id]))
        self.assertEqual(execute_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(launch_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_scheduler_stops_rule_after_member_is_removed(self):
        rule = self.create_rule()
        rule.is_launched = True
        rule.process_status = "running"
        rule.save(update_fields=["is_launched", "process_status"])
        self.sensor_member.delete()

        _process_automation_rules(timezone.now())

        rule.refresh_from_db()
        self.assertFalse(rule.is_launched)
        self.assertEqual(rule.process_status, "error_stopped")
        self.assertIn("不属于规则所在房间", rule.error_message)

    def test_staff_cannot_write_but_can_execute(self):
        rule = self.create_rule(device_list=[])
        self.client.force_authenticate(self.staff)
        create_response = self.client.post(
            reverse("automation-rule-list"), self.rule_payload(script_id="staff_script"), format="json"
        )
        execute_response = self.client.post(reverse("automation-rule-execute", args=[rule.id]))

        self.assertEqual(create_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(execute_response.status_code, status.HTTP_200_OK)

    def test_global_rule_keeps_global_resource_behavior(self):
        self.client.force_authenticate(self.superuser)
        response = self.client.post(
            reverse("automation-rule-list"),
            {
                "name": "全局脚本",
                "script_id": "global_rule",
                "script": "def loop(): return True",
                "device_list": [
                    {"device_id": self.other_sensor.sensor_id, "device_type": "Sensor"},
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertIsNone(AutomationRule.objects.get(pk=response.data["id"]).section_id)

    def test_deleting_section_deletes_scoped_rule(self):
        rule = self.create_rule()
        self.section.delete()
        self.assertFalse(AutomationRule.objects.filter(pk=rule.id).exists())
