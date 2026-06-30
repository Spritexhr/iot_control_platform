from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from rest_framework.test import APITestCase

from devices.admin import DeviceAdmin
from devices.models import Device, DeviceType
from sensors.admin import SensorAdmin
from sensors.models import Sensor, SensorType

from .models import ResourceFolder


class ResourceFolderApiTests(APITestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(
            username="folder-admin", password="test", is_staff=True
        )
        self.client.force_authenticate(self.admin)
        self.sensor_type = SensorType.objects.create(SensorType_id="T", name="测试传感器")
        self.device_type = DeviceType.objects.create(DeviceType_id="D", name="测试设备")
        self.sensor = Sensor.objects.create(sensor_id="S-1", name="传感器1", sensor_type=self.sensor_type)
        self.device = Device.objects.create(device_id="D-1", name="设备1", device_type=self.device_type)

    def test_independent_trees_and_cycle_validation(self):
        sensor_root = self.client.post(
            "/api/resource-folders/", {"name": "一车间", "resource_type": "sensor"}, format="json"
        )
        self.assertEqual(sensor_root.status_code, 201)
        device_root = self.client.post(
            "/api/resource-folders/", {"name": "一车间", "resource_type": "device"}, format="json"
        )
        self.assertEqual(device_root.status_code, 201)
        child = self.client.post(
            "/api/resource-folders/",
            {"name": "反应区", "resource_type": "sensor", "parent": sensor_root.data["id"]},
            format="json",
        )
        self.assertEqual(child.status_code, 201)
        cross_type = self.client.patch(
            f"/api/resource-folders/{child.data['id']}/",
            {"parent": device_root.data["id"]}, format="json",
        )
        self.assertEqual(cross_type.status_code, 400)
        cycle = self.client.patch(
            f"/api/resource-folders/{sensor_root.data['id']}/",
            {"parent": child.data["id"]}, format="json",
        )
        self.assertEqual(cycle.status_code, 400)

    def test_bulk_move_filter_and_non_empty_delete(self):
        folder = ResourceFolder.objects.create(name="归档", resource_type="sensor")
        moved = self.client.post(
            "/api/sensors/bulk-move/", {"sensor_ids": [self.sensor.sensor_id], "folder": folder.id}, format="json"
        )
        self.assertEqual(moved.status_code, 200)
        self.sensor.refresh_from_db()
        self.assertEqual(self.sensor.folder_id, folder.id)

        filtered = self.client.get("/api/sensors/", {"folder": folder.id})
        self.assertEqual(filtered.status_code, 200)
        self.assertEqual(filtered.data["count"], 1)

        blocked = self.client.delete(f"/api/resource-folders/{folder.id}/")
        self.assertEqual(blocked.status_code, 409)

        unfiled = self.client.post(
            "/api/sensors/bulk-move/", {"sensor_ids": [self.sensor.sensor_id], "folder": None}, format="json"
        )
        self.assertEqual(unfiled.status_code, 200)
        self.assertEqual(self.client.delete(f"/api/resource-folders/{folder.id}/").status_code, 204)

    def test_wrong_resource_folder_is_rejected(self):
        device_folder = ResourceFolder.objects.create(name="设备目录", resource_type="device")
        response = self.client.patch(
            f"/api/sensors/{self.sensor.sensor_id}/", {"folder": device_folder.id}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_page_size_is_bounded(self):
        response = self.client.get("/api/sensors/", {"page_size": 96})
        self.assertEqual(response.status_code, 200)
        self.assertIn("count", response.data)

    def test_folder_writes_require_staff(self):
        viewer = get_user_model().objects.create_user(username="folder-viewer", password="test")
        self.client.force_authenticate(viewer)
        self.assertEqual(self.client.get("/api/resource-folders/?resource_type=sensor").status_code, 200)
        response = self.client.post(
            "/api/resource-folders/", {"name": "无权限", "resource_type": "sensor"}, format="json"
        )
        self.assertEqual(response.status_code, 403)
        move = self.client.post(
            "/api/sensors/bulk-move/", {"sensor_ids": [self.sensor.sensor_id], "folder": None}, format="json"
        )
        self.assertEqual(move.status_code, 403)

    def test_paginated_reorder_keeps_other_pages_stable(self):
        self.sensor.sort_order = 1
        self.sensor.save(update_fields=["sort_order"])
        for index in range(2, 5):
            Sensor.objects.create(
                sensor_id=f"S-{index}", name=f"传感器{index}",
                sensor_type=self.sensor_type, sort_order=index,
            )
        before = list(
            Sensor.objects.order_by("sort_order", "-created_at").values_list("sensor_id", flat=True)
        )
        page_two = before[2:4]
        response = self.client.post(
            "/api/sensors/reorder/",
            {"order": list(reversed(page_two)), "page": 2, "page_size": 2, "folder": "unfiled"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        after = list(
            Sensor.objects.order_by("sort_order", "-created_at").values_list("sensor_id", flat=True)
        )
        self.assertEqual(after[:2], before[:2])
        self.assertEqual(after[2:4], list(reversed(page_two)))

    def test_admin_folder_choices_are_limited_by_resource_type(self):
        sensor_root = ResourceFolder.objects.create(name="厂区", resource_type="sensor")
        sensor_child = ResourceFolder.objects.create(
            name="车间", resource_type="sensor", parent=sensor_root
        )
        device_folder = ResourceFolder.objects.create(name="设备区", resource_type="device")
        request = RequestFactory().get("/admin/")
        request.user = self.admin

        sensor_formfield = SensorAdmin(Sensor, admin.site).formfield_for_foreignkey(
            Sensor._meta.get_field("folder"), request
        )
        device_formfield = DeviceAdmin(Device, admin.site).formfield_for_foreignkey(
            Device._meta.get_field("folder"), request
        )

        self.assertEqual(list(sensor_formfield.queryset), [sensor_root, sensor_child])
        self.assertEqual(list(device_formfield.queryset), [device_folder])
        self.assertEqual(str(sensor_child), "传感器/厂区 / 车间")
