"""
乙苯(EB)装置大屏插件的独立数据表。

设计要点
- 插件不在主模型(Sensor/Device)上挂字段；本插件需要的"工艺位号、阈值、显示参数"
  全部独立存储在本文件定义的三张表里。
- 通过 ForeignKey/OneToOneField 引用主模型的 Sensor / Device。主模型删除时本插件
  绑定级联删除，反向不耦合：主模型本身不感知本插件存在。
- 传感器绑定按 (sensor, data_key) 唯一：温压一体等"多 data_key"传感器可以为不同字段
  各建一行 binding，独立展示、独立阈值、独立严重度。
- 设备绑定保持一对一：同一阀门只能在大屏上绑定一次。
"""
from django.db import models


class EBPlantConfig(models.Model):
    """大屏全局视图配置（单例式，name='default' 唯一一条）。"""

    name = models.CharField(
        max_length=50,
        unique=True,
        default="default",
        verbose_name="配置名",
        help_text="默认仅一条 default，预留未来多套配置",
    )

    view_settings = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="视图设置",
        help_text='例如 {"grid_cols": 4, "refresh_ms": 1000, "show_threshold_line": true}',
    )

    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "EB 大屏配置"
        verbose_name_plural = "EB 大屏配置"

    def __str__(self) -> str:
        return self.name


class EBPlantSensorBinding(models.Model):
    """从主模型导入到 EB 大屏的传感器绑定记录。"""

    SEVERITY_CHOICES = [
        ("low", "low"),
        ("mid", "mid"),
        ("high", "high"),
        ("critical", "critical"),
    ]

    sensor = models.ForeignKey(
        "sensors.Sensor",
        on_delete=models.CASCADE,
        related_name="eb_bindings",
        verbose_name="主模型传感器",
    )

    tag = models.CharField(max_length=50, blank=True, verbose_name="仪表位号", help_text="如 TT-101")
    area = models.CharField(max_length=50, blank=True, verbose_name="区域", help_text="如 R1 / R2 / FEED")

    data_key = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="数据键名",
        help_text="从 SensorData.data 取值的字段名，留空表示自动取唯一字段（仅在传感器只有一个字段时有意义）",
    )
    unit = models.CharField(max_length=20, blank=True, verbose_name="单位")

    normal_value = models.FloatField(null=True, blank=True, verbose_name="正常值")
    hi_threshold = models.FloatField(null=True, blank=True, verbose_name="高阈值")
    lo_threshold = models.FloatField(null=True, blank=True, verbose_name="低阈值")
    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
        default="mid",
        verbose_name="严重度",
    )

    sort_order = models.IntegerField(default=0, db_index=True, verbose_name="显示顺序")
    is_visible = models.BooleanField(default=True, verbose_name="是否显示")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "EB 传感器绑定"
        verbose_name_plural = "EB 传感器绑定"
        ordering = ["sort_order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["sensor", "data_key"],
                name="uniq_eb_sensor_data_key",
            ),
        ]

    @property
    def point_id(self) -> str:
        """前端实时数据流里的唯一 ID。
        - 单字段传感器（data_key 留空）→ 用 sensor_id
        - 多字段传感器（同 sensor 多 binding）→ 用 sensor_id::data_key 区分
        """
        if self.data_key:
            return f"{self.sensor.sensor_id}::{self.data_key}"
        return self.sensor.sensor_id

    def __str__(self) -> str:
        return f"{self.tag or self.point_id}"


class EBPlantDeviceBinding(models.Model):
    """从主模型导入到 EB 大屏的设备绑定记录。"""

    device = models.OneToOneField(
        "devices.Device",
        on_delete=models.CASCADE,
        related_name="eb_device_binding",
        verbose_name="主模型设备",
    )

    tag = models.CharField(max_length=50, blank=True, verbose_name="设备位号", help_text="如 P-101")
    area = models.CharField(max_length=50, blank=True, verbose_name="区域")

    sort_order = models.IntegerField(default=0, db_index=True, verbose_name="显示顺序")
    is_visible = models.BooleanField(default=True, verbose_name="是否显示")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "EB 设备绑定"
        verbose_name_plural = "EB 设备绑定"
        ordering = ["sort_order", "id"]

    def __str__(self) -> str:
        return f"{self.tag or self.device.device_id}"
