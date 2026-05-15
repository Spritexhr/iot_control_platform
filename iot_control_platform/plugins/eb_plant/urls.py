from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"sensor_bindings", views.EBPlantSensorBindingViewSet, basename="eb-sensor-binding")
router.register(r"device_bindings", views.EBPlantDeviceBindingViewSet, basename="eb-device-binding")

urlpatterns = [
    path("snapshot", views.snapshot, name="eb-plant-snapshot"),
    path("stream", views.stream, name="eb-plant-stream"),
    path("config", views.config_view, name="eb-plant-config"),
    path("bindable_sources", views.bindable_sources, name="eb-plant-bindable-sources"),
]

urlpatterns += router.urls
