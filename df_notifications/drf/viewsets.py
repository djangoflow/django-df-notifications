from df_notifications.drf.serializers import PushActionCategorySerializer
from df_notifications.drf.serializers import UserDeviceSerializer
from df_notifications.models import PushActionCategory
from df_notifications.models import UserDevice
from fcm_django.api.rest_framework import FCMDeviceAuthorizedViewSet
from rest_framework import permissions
from rest_framework.mixins import ListModelMixin
from rest_framework.viewsets import GenericViewSet


class UserDeviceViewSet(FCMDeviceAuthorizedViewSet):
    queryset = UserDevice.objects.all()
    serializer_class = UserDeviceSerializer


class PushActionCategoryViewSet(ListModelMixin, GenericViewSet):
    queryset = PushActionCategory.objects.prefetch_related("actions").filter(is_active=True)
    permission_classes = (permissions.AllowAny,)
    serializer_class = PushActionCategorySerializer
    pagination_class = None
