"""
监听 SensorData 落库后事件，若对应传感器已在 EB 插件中导入，
则更新实时缓存并广播给 SSE 订阅方。
"""
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from sensors.models import SensorData
from services.realtime.latest_values import ingest_sensor_data

from .models import EBPlantSensorBinding

logger = logging.getLogger(__name__)

PLUGIN_CODE = "EB"


@receiver(post_save, sender=SensorData, dispatch_uid="eb_plant_ingest_sensor_data")
def on_sensor_data_saved(sender, instance: SensorData, created: bool, **kwargs):
    if not created:
        return
    try:
        # 同一 sensor 在 EB 大屏可有多条 binding（温压一体那种"温度一条、压力一条"），
        # 每条用 point_id (sensor_id::data_key) 区分实时点位。
        bindings = EBPlantSensorBinding.objects.filter(
            sensor_id=instance.sensor_id, is_visible=True,
        ).select_related("sensor")
        ts = instance.timestamp.timestamp() if instance.timestamp else None
        for binding in bindings:
            ingest_sensor_data(
                sensor_id=binding.point_id,
                data=instance.data,
                timestamp=ts,
                plugin_code=PLUGIN_CODE,
                binding=binding,
            )
    except Exception as exc:
        logger.warning("EB 实时广播失败 sensor_id=%s err=%s", instance.sensor_id, exc)
