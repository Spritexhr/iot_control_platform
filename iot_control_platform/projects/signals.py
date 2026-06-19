"""
监听 SensorData 落库，若该传感器已加入某些项目，则按各项目成员构造点位样本，
广播到对应的 projects.{project_id} 通道。

设备状态不在此另写信号：直接复用主层 DeviceStatusCollection 信号（consumer 订阅
devices.all 后按成员过滤转发），与 eb_plant 一致。

实时缓存说明：projects 不写 services.realtime 的全局 latest_values 缓存（那是按 point_id
索引的，与插件共享会互相覆盖）。projects 的 snapshot 改为现查 DB，这里只负责增量广播。
"""
import logging

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from sensors.models import SensorData
from services.realtime import dispatch
from services.realtime.latest_values import build_point_sample

from .models import ProjectSensorMember

logger = logging.getLogger(__name__)


@receiver(post_save, sender=SensorData, dispatch_uid="projects_ingest_sensor_data")
def on_sensor_data_saved(sender, instance: SensorData, created: bool, **kwargs):
    if not created:
        return
    try:
        # 同一 sensor 可能属于多个项目、且每个项目内可有多条成员（多 data_key）。
        members = ProjectSensorMember.objects.filter(
            sensor_id=instance.sensor_id, is_visible=True,
        ).select_related("sensor", "project")
        ts = instance.timestamp.timestamp() if instance.timestamp else None
        payloads = []
        for m in members:
            sample = build_point_sample(
                m.point_id, instance.data, ts,
                plugin_code=m.project.code, binding=m,
            )
            payloads.append((m.project_id, sample.to_dict()))

        if not payloads:
            return

        def _publish():
            for project_id, payload in payloads:
                dispatch.publish_project_sample(project_id, payload)

        # 与主层一致：延迟到事务提交后再广播（回滚不推、不阻塞 INSERT）
        transaction.on_commit(_publish)
    except Exception as exc:
        logger.warning("projects 实时广播失败 sensor_id=%s err=%s", instance.sensor_id, exc)
