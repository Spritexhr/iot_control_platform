from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'device-types', views.DeviceTypeViewSet, basename='device-type')
router.register(r'devices', views.DeviceViewSet, basename='device')

urlpatterns = [
    path('', include(router.urls)),
]
