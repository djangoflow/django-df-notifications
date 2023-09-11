from rest_framework.routers import DefaultRouter

from .viewsets import PushActionCategoryViewSet, UserDeviceViewSet

router = DefaultRouter()
router.register("devices", UserDeviceViewSet, basename="devices")
router.register(
    "action-categories", PushActionCategoryViewSet, basename="action-categories"
)

urlpatterns = router.urls
