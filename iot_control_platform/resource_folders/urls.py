from rest_framework.routers import DefaultRouter

from .views import ResourceFolderViewSet

router = DefaultRouter()
router.register(r"resource-folders", ResourceFolderViewSet, basename="resource-folder")

urlpatterns = router.urls

