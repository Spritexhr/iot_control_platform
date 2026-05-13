"""实时数据相关 URL。"""
from django.urls import path

from .plant_control_views import inject_disturbance
from .sse_views import plant_snapshot, plant_stream

urlpatterns = [
    path("realtime/plant/<str:plant_code>/stream", plant_stream, name="plant-stream"),
    path("realtime/plant/<str:plant_code>/snapshot", plant_snapshot, name="plant-snapshot"),
    path("realtime/plant/EB/disturbance", inject_disturbance, name="plant-disturbance"),
]
