from df_notifications.models import UserDevice
from fcm_django.api.rest_framework import FCMDeviceSerializer


class UserDeviceSerializer(FCMDeviceSerializer):
    class Meta(FCMDeviceSerializer.Meta):
        model = UserDevice
        fields = FCMDeviceSerializer.Meta.fields
