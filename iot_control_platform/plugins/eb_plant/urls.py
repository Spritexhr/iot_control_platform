from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"sensor_bindings", views.EBPlantSensorBindingViewSet, basename="eb-sensor-binding")
router.register(r"device_bindings", views.EBPlantDeviceBindingViewSet, basename="eb-device-binding")
router.register(r"sections", views.EBPlantSectionViewSet, basename="eb-section")

urlpatterns = [
    path("snapshot", views.snapshot, name="eb-plant-snapshot"),
    path("layout", views.layout, name="eb-plant-layout"),
    path("config", views.config_view, name="eb-plant-config"),
    path("bindable_sources", views.bindable_sources, name="eb-plant-bindable-sources"),
]

urlpatterns += router.urls
