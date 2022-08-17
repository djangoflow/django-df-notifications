from fcm_django.api.rest_framework import FCMDeviceSerializer

from df_notifications.models import UserDevice


class UserDeviceSerializer(FCMDeviceSerializer):
    class Meta(FCMDeviceSerializer.Meta):
        model = UserDevice
        fields = FCMDeviceSerializer.Meta.fields
