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
        binding = EBPlantSensorBinding.objects.filter(
            sensor_id=instance.sensor_id, is_visible=True,
        ).first()
        if not binding:
            return
        ingest_sensor_data(
            sensor_id=instance.sensor.sensor_id,
            data=instance.data,
            timestamp=instance.timestamp.timestamp() if instance.timestamp else None,
            plugin_code=PLUGIN_CODE,
            binding=binding,
        )
    except Exception as exc:
        logger.warning("EB 实时广播失败 sensor_id=%s err=%s", instance.sensor_id, exc)
