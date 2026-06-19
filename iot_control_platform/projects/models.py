"""
平台原生「项目/场景」系统的核心模型。

一个 Project（项目/场景）= 一批传感器/设备成员（装置）+ 自动化规则（控制）+ 多个视图（展示）。

设计要点（由 plugins/eb_plant 的 binding/section 模式升格为平台一等公民）：
- 主模型 Sensor / Device 零改动：Project 通过 ProjectSensorMember / ProjectDeviceMember
  「软引用」全局 Sensor / Device，项目内固有的展示元数据（位号 / 分区 / 阈值 / 排序 /
  可见性）独立存储在成员表里。主模型对本 app 零感知。
- 同一传感器 / 设备可被多个项目复用：成员唯一性按 (project, sensor, data_key) /
  (project, device)，而非全局唯一。
- related_name 统一用 project_members，与 eb_plant 插件占用的 eb_bindings /
  eb_device_binding 并存不冲突。
- point_id 规则与 EB 保持一致（sensor_id 或 sensor_id::data_key），前端 findByBinding 可直接复用。
"""
from django.conf import settings
from django.db import models


SEVERITY_CHOICES = [
    ("low", "low"),
    ("mid", "mid"),
    ("high", "high"),
    ("critical", "critical"),
]


class Project(models.Model):
    """项目 / 场景顶层容器。如「苯乙烯生产工厂」「家居智能控制」。"""

    SCENE_TYPE_CHOICES = [
        ("industrial", "工业装置"),
        ("smart_home", "智能家居"),
        ("custom", "自定义"),
    ]

    code = models.CharField(
        max_length=30,
        unique=True,
        verbose_name="项目代号",
        help_text="唯一短码，如 EB / HOME，用于实时通道与对外引用",
    )
    name = models.CharField(max_length=100, verbose_name="项目名称")
    description = models.TextField(blank=True, verbose_name="项目描述")
    scene_type = models.CharField(
        max_length=20,
        choices=SCENE_TYPE_CHOICES,
        default="custom",
        verbose_name="场景类型",
        help_text="决定展示默认风格（工业蓝白 / 暖米色等）",
    )
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    sort_order = models.IntegerField(default=0, db_index=True, verbose_name="显示顺序")
    view_settings = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="视图全局设置",
        help_text='如 {"grid_cols": 4, "refresh_ms": 1000}',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_projects",
        verbose_name="创建人",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "项目/场景"
        verbose_name_plural = "项目/场景"
        ordering = ["sort_order", "id"]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class ProjectSection(models.Model):
    """项目内分区（工段 / 区域 / 房间）。成员可归属一个分区；
    未归属（section 为空）的成员在展示时统一落到末尾「未分组」段。"""

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="sections",
        verbose_name="所属项目",
    )
    name = models.CharField(max_length=50, verbose_name="分区名", help_text="如 反应工段 / 客厅")
    sort_order = models.IntegerField(default=0, db_index=True, verbose_name="显示顺序")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "项目分区"
        verbose_name_plural = "项目分区"
        ordering = ["sort_order", "id"]

    def __str__(self) -> str:
        return f"{self.project.code}/{self.name}"


class ProjectSensorMember(models.Model):
    """把全局 Sensor 加入某项目的成员记录（升格自 EBPlantSensorBinding）。"""

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="sensor_members",
        verbose_name="所属项目",
    )
    sensor = models.ForeignKey(
        "sensors.Sensor",
        on_delete=models.CASCADE,
        related_name="project_members",
        verbose_name="主模型传感器",
    )
    section = models.ForeignKey(
        ProjectSection,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sensor_members",
        verbose_name="所属分区",
        help_text="留空表示未分组（展示时归到末尾「未分组」段）",
    )

    tag = models.CharField(max_length=50, blank=True, verbose_name="位号", help_text="如 TT-101")
    area = models.CharField(max_length=50, blank=True, verbose_name="区域", help_text="如 R1 / FEED")

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
        verbose_name = "项目传感器成员"
        verbose_name_plural = "项目传感器成员"
        ordering = ["sort_order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "sensor", "data_key"],
                name="uniq_project_sensor_data_key",
            ),
        ]

    @property
    def description(self) -> str:
        return self.sensor.description if self.sensor_id else ""

    @property
    def point_id(self) -> str:
        """实时数据流里的唯一点位 ID。
        - 单字段传感器（data_key 留空）→ 用 sensor_id
        - 多字段传感器（同 sensor 多成员）→ 用 sensor_id::data_key 区分
        """
        if self.data_key:
            return f"{self.sensor.sensor_id}::{self.data_key}"
        return self.sensor.sensor_id

    def __str__(self) -> str:
        return f"{self.tag or self.point_id}"


class ProjectDeviceMember(models.Model):
    """把全局 Device 加入某项目的成员记录（升格自 EBPlantDeviceBinding）。

    与 EB 不同：EB 是全局 OneToOne（一个设备只能上一次大屏），这里用 FK + (project, device)
    唯一约束，使同一设备可被多个项目复用。"""

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="device_members",
        verbose_name="所属项目",
    )
    device = models.ForeignKey(
        "devices.Device",
        on_delete=models.CASCADE,
        related_name="project_members",
        verbose_name="主模型设备",
    )
    section = models.ForeignKey(
        ProjectSection,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="device_members",
        verbose_name="所属分区",
        help_text="留空表示未分组",
    )

    tag = models.CharField(max_length=50, blank=True, verbose_name="位号", help_text="如 P-101")
    area = models.CharField(max_length=50, blank=True, verbose_name="区域")

    sort_order = models.IntegerField(default=0, db_index=True, verbose_name="显示顺序")
    is_visible = models.BooleanField(default=True, verbose_name="是否显示")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "项目设备成员"
        verbose_name_plural = "项目设备成员"
        ordering = ["sort_order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "device"],
                name="uniq_project_device",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.tag or (self.device.device_id if self.device_id else '')}"


class ProjectView(models.Model):
    """项目的一个展示视图。统一收编 eb_plant（card）/ plant_diagram（diagram）/
    data_viz（timeseries）的存储：类型特定的布局放在 config（JSON）里。"""

    VIEW_TYPE_CHOICES = [
        ("card", "卡片大屏"),
        ("diagram", "流程图"),
        ("timeseries", "时序趋势"),
    ]

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="views",
        verbose_name="所属项目",
    )
    name = models.CharField(max_length=50, verbose_name="视图名")
    view_type = models.CharField(
        max_length=20,
        choices=VIEW_TYPE_CHOICES,
        default="card",
        verbose_name="视图类型",
    )
    config = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="视图配置",
        help_text="类型特定：diagram 存 canvas；timeseries 存选中源+字段+默认时段；card 存网格设置",
    )
    is_default = models.BooleanField(default=False, verbose_name="是否默认视图")
    sort_order = models.IntegerField(default=0, db_index=True, verbose_name="显示顺序")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "项目视图"
        verbose_name_plural = "项目视图"
        ordering = ["sort_order", "id"]

    def __str__(self) -> str:
        return f"{self.project.code}/{self.name}({self.view_type})"
