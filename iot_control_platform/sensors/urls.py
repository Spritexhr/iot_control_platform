from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'sensor-types', views.SensorTypeViewSet, basename='sensor-type')
router.register(r'sensors', views.SensorViewSet, basename='sensor')

urlpatterns = [
    path('', include(router.urls)),
]
