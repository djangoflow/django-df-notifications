from .viewsets import PushActionCategoryViewSet
from .viewsets import UserDeviceViewSet
from rest_framework.routers import DefaultRouter


router = DefaultRouter()
router.register("devices", UserDeviceViewSet, basename="devices")
router.register(
    "action-categories", PushActionCategoryViewSet, basename="action-categories"
)

urlpatterns = router.urls
