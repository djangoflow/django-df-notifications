from .models import NotificationHistory
from .models import UserDevice
from django.contrib import admin
from fcm_django.admin import DeviceAdmin
from fcm_django.models import FCMDevice


admin.site.unregister(FCMDevice)


@admin.register(UserDevice)
class UserDeviceAdmin(DeviceAdmin):
    pass


@admin.register(NotificationHistory)
class NotificationHistoryAdmin(admin.ModelAdmin):
    list_display = ("template", "channel", "instance_id", "created")
    date_hierarchy = "created"
    search_fields = (
        "template",
        "channel",
    )
