from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"projects", views.ProjectViewSet, basename="project")
router.register(r"project_sections", views.ProjectSectionViewSet, basename="project-section")
router.register(r"project_sensor_members", views.ProjectSensorMemberViewSet, basename="project-sensor-member")
router.register(r"project_device_members", views.ProjectDeviceMemberViewSet, basename="project-device-member")
router.register(r"project_views", views.ProjectViewViewSet, basename="project-view")

urlpatterns = router.urls
