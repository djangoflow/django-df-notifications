from df_notifications.drf.serializers import UserDeviceSerializer
from df_notifications.models import UserDevice
from fcm_django.api.rest_framework import FCMDeviceAuthorizedViewSet


class UserDeviceViewSet(FCMDeviceAuthorizedViewSet):
    queryset = UserDevice.objects.all()
    serializer_class = UserDeviceSerializer
