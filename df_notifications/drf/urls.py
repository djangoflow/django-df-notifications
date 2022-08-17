from .viewsets import UserDeviceViewSet
from rest_framework.routers import DefaultRouter


router = DefaultRouter()
router.register("devices", UserDeviceViewSet, basename="devices")

urlpatterns = router.urls
