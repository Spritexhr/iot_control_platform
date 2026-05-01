from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r"platform-configs", views.PlatformConfigViewSet, basename="platform-config")
router.register(r"plugin-manager", views.PluginViewSet, basename="plugin-manager")

urlpatterns = [
    path("", include(router.urls)),
]
