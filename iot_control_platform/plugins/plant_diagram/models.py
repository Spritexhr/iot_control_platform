"""
P&ID 画板存储模型。

一个 plant_code 可以挂多张画板（主流程 / 公用工程 / 局部放大），
画布数据整存在 `canvas` JSONField 里，结构见 services/plant_diagram_schema.md
（前端约定的 nodes/edges/viewport 三段）。
"""
from django.contrib.auth.models import User
from django.db import models


class PlantDiagram(models.Model):
    plant_code = models.CharField(
        max_length=50,
        db_index=True,
        verbose_name="装置代号",
        help_text='与 Sensor.plant_code 对应，例如 "EB"',
    )

    name = models.CharField(max_length=100, verbose_name="画板名称")
    description = models.TextField(blank=True, verbose_name="画板描述")

    canvas = models.JSONField(
        default=dict,
        verbose_name="画布数据",
        help_text="包含 version / viewport / nodes / edges",
    )

    is_default = models.BooleanField(
        default=False,
        verbose_name="是否默认画板",
        help_text="同一 plant_code 仅可有一张 default；运行态默认打开 default",
    )

    sort_order = models.IntegerField(default=0, verbose_name="排序")

    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="plant_diagrams",
        verbose_name="创建人",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "P&ID 画板"
        verbose_name_plural = "P&ID 画板"
        ordering = ["plant_code", "sort_order", "-updated_at"]
        indexes = [
            models.Index(fields=["plant_code", "is_default"]),
        ]

    def __str__(self) -> str:
        return f"[{self.plant_code}] {self.name}"

    def save(self, *args, **kwargs):
        # 同一 plant_code 内 is_default 只能有一张；新保存的若设了 default，自动取消其它
        if self.is_default:
            PlantDiagram.objects.filter(
                plant_code=self.plant_code, is_default=True,
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)
