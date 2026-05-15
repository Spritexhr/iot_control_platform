from rest_framework.routers import DefaultRouter

from .views import PlantDiagramViewSet

router = DefaultRouter()
router.register(r"", PlantDiagramViewSet, basename="plant-diagram")

urlpatterns = router.urls
