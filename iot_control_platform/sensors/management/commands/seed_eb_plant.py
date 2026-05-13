"""
管理命令：把乙苯(EB)装置的核心传感器写入数据库。

用法:
    python manage.py seed_eb_plant            # 创建/更新 5 个 MVP 点位
    python manage.py seed_eb_plant --full     # 创建全部 ~20 个点位(后续补全用)

幂等执行——已存在的 Sensor 会按 sensor_id 更新 plant_metadata,不会重建。
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from sensors.models import Sensor, SensorType


PLANT_CODE = "EB"
SENSOR_TYPE_ID = "EB_INSTRUMENT"
SENSOR_TYPE_NAME = "乙苯装置仪表"

# data_key 是 simulator 在 MQTT data 字段里使用的键名,与 ingest_sensor_data 对应
MVP_POINTS = [
    {
        "sensor_id": "EB-TT-101", "tag": "TT-101", "name": "R1 反应温度",
        "area": "R1", "data_key": "temperature", "unit": "K",
        "normal_value": 434, "hi_threshold": 440, "lo_threshold": 425,
        "severity": "high",
    },
    {
        "sensor_id": "EB-PT-101", "tag": "PT-101", "name": "R1 反应压力",
        "area": "R1", "data_key": "pressure", "unit": "atm",
        "normal_value": 20, "hi_threshold": 22, "lo_threshold": 18,
        "severity": "high",
    },
    {
        "sensor_id": "EB-LT-102", "tag": "LT-102", "name": "R1 蒸汽包液位",
        "area": "R1", "data_key": "level", "unit": "%",
        "normal_value": 50, "hi_threshold": 80, "lo_threshold": 20,
        "severity": "critical",
    },
    {
        "sensor_id": "EB-FT-401", "tag": "FT-401", "name": "DEB 循环流量",
        "area": "C2", "data_key": "flow_rate", "unit": "kmol/h",
        "normal_value": 282, "hi_threshold": 350, "lo_threshold": 200,
        "severity": "high",
    },
    {
        "sensor_id": "EB-TT-201", "tag": "TT-201", "name": "R2 反应温度",
        "area": "R2", "data_key": "temperature", "unit": "K",
        "normal_value": 432, "hi_threshold": 438, "lo_threshold": 420,
        "severity": "high",
    },
]

FULL_EXTRA_POINTS = [
    # 后续补全用,先占位字典结构
    # 反应器
    {"sensor_id": "EB-LT-101", "tag": "LT-101", "name": "R1 液位", "area": "R1",
     "data_key": "level", "unit": "%", "normal_value": 50,
     "hi_threshold": 70, "lo_threshold": 30, "severity": "mid"},
    {"sensor_id": "EB-PT-201", "tag": "PT-201", "name": "R2 反应压力", "area": "R2",
     "data_key": "pressure", "unit": "atm", "normal_value": 19,
     "hi_threshold": 21, "lo_threshold": 17, "severity": "high"},
    {"sensor_id": "EB-LT-201", "tag": "LT-201", "name": "R2 液位", "area": "R2",
     "data_key": "level", "unit": "%", "normal_value": 50,
     "hi_threshold": 70, "lo_threshold": 30, "severity": "mid"},
    # 精馏塔
    {"sensor_id": "EB-PT-301", "tag": "PT-301", "name": "C1 塔顶压力", "area": "C1",
     "data_key": "pressure", "unit": "atm", "normal_value": 0.3,
     "hi_threshold": 0.5, "lo_threshold": None, "severity": "high"},
    {"sensor_id": "EB-TT-301", "tag": "TT-301", "name": "C1 塔釜温度", "area": "C1",
     "data_key": "temperature", "unit": "K", "normal_value": 390,
     "hi_threshold": 400, "lo_threshold": 380, "severity": "mid"},
    {"sensor_id": "EB-LT-301", "tag": "LT-301", "name": "C1 回流罐液位", "area": "C1",
     "data_key": "level", "unit": "%", "normal_value": 50,
     "hi_threshold": 80, "lo_threshold": 20, "severity": "mid"},
    {"sensor_id": "EB-TT-302", "tag": "TT-302", "name": "C1 第14级温度", "area": "C1",
     "data_key": "temperature", "unit": "K", "normal_value": 365.8,
     "hi_threshold": 370, "lo_threshold": 360, "severity": "mid"},
    {"sensor_id": "EB-PT-401", "tag": "PT-401", "name": "C2 塔顶压力", "area": "C2",
     "data_key": "pressure", "unit": "atm", "normal_value": 0.1,
     "hi_threshold": 0.3, "lo_threshold": None, "severity": "high"},
    {"sensor_id": "EB-TT-401", "tag": "TT-401", "name": "C2 塔釜温度", "area": "C2",
     "data_key": "temperature", "unit": "K", "normal_value": 407,
     "hi_threshold": 415, "lo_threshold": 395, "severity": "mid"},
    {"sensor_id": "EB-LT-401", "tag": "LT-401", "name": "C2 回流罐液位", "area": "C2",
     "data_key": "level", "unit": "%", "normal_value": 50,
     "hi_threshold": 80, "lo_threshold": 20, "severity": "mid"},
    {"sensor_id": "EB-TT-402", "tag": "TT-402", "name": "C2 第20级温度", "area": "C2",
     "data_key": "temperature", "unit": "K", "normal_value": 394.5,
     "hi_threshold": 400, "lo_threshold": 388, "severity": "mid"},
    # 流量
    {"sensor_id": "EB-FT-101", "tag": "FT-101", "name": "乙烯进料流量", "area": "FEED",
     "data_key": "flow_rate", "unit": "kmol/h", "normal_value": 630.6,
     "hi_threshold": 760, "lo_threshold": 500, "severity": "mid"},
    {"sensor_id": "EB-FT-102", "tag": "FT-102", "name": "苯进料流量", "area": "FEED",
     "data_key": "flow_rate", "unit": "kmol/h", "normal_value": 630.6,
     "hi_threshold": 760, "lo_threshold": 500, "severity": "mid"},
    {"sensor_id": "EB-FT-103", "tag": "FT-103", "name": "总苯流量(含循环)", "area": "FEED",
     "data_key": "flow_rate", "unit": "kmol/h", "normal_value": 1600,
     "hi_threshold": 1900, "lo_threshold": 1300, "severity": "mid"},
    {"sensor_id": "EB-FT-301", "tag": "FT-301", "name": "EB 产品流量", "area": "C1",
     "data_key": "flow_rate", "unit": "kmol/h", "normal_value": 630.6,
     "hi_threshold": 760, "lo_threshold": 500, "severity": "mid"},
    {"sensor_id": "EB-FT-501", "tag": "FT-501", "name": "蒸汽产量(R1)", "area": "R1",
     "data_key": "flow_rate", "unit": "kmol/h", "normal_value": 500,
     "hi_threshold": 600, "lo_threshold": 350, "severity": "mid"},
]


class Command(BaseCommand):
    help = "幂等创建/更新乙苯装置的传感器记录"

    def add_arguments(self, parser):
        parser.add_argument(
            "--full",
            action="store_true",
            help="创建全部 ~20 个点位(默认只创建 MVP 5 个)",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        sensor_type, created = SensorType.objects.update_or_create(
            SensorType_id=SENSOR_TYPE_ID,
            defaults={
                "name": SENSOR_TYPE_NAME,
                "description": "EB(乙苯)装置虚拟仪表节点,统一类型",
                "data_fields": ["temperature", "pressure", "level", "flow_rate"],
                "config_parameters": ["normal_value", "hi_threshold", "lo_threshold"],
                "commands": {},
            },
        )
        self.stdout.write(
            f"{'创建' if created else '已存在'} SensorType: {sensor_type.name}"
        )

        points = MVP_POINTS + (FULL_EXTRA_POINTS if options["full"] else [])
        for p in points:
            sensor, created = Sensor.objects.update_or_create(
                sensor_id=p["sensor_id"],
                defaults={
                    "name": f"{p['tag']} {p['name']}",
                    "description": f"{p['name']}({p['tag']}),所属区域 {p['area']}",
                    "location": p["area"],
                    "sensor_type": sensor_type,
                    "plant_code": PLANT_CODE,
                    "plant_metadata": {
                        "tag": p["tag"],
                        "area": p["area"],
                        "data_key": p["data_key"],
                        "unit": p["unit"],
                        "normal_value": p["normal_value"],
                        "hi_threshold": p["hi_threshold"],
                        "lo_threshold": p["lo_threshold"],
                        "severity": p["severity"],
                    },
                },
            )
            mark = "+" if created else "·"
            self.stdout.write(f"  {mark} {sensor.sensor_id}  {p['name']}")

        self.stdout.write(self.style.SUCCESS(
            f"完成。当前 EB 装置传感器共 "
            f"{Sensor.objects.filter(plant_code=PLANT_CODE).count()} 个。"
        ))
