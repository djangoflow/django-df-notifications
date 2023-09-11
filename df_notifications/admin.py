from django.contrib import admin
from fcm_django.admin import DeviceAdmin
from fcm_django.models import FCMDevice

from .models import (
    NotificationHistory,
    PushAction,
    PushActionCategory,
    UserDevice,
)

admin.site.unregister(FCMDevice)


@admin.register(PushActionCategory)
class PushActionCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")


@admin.register(PushAction)
class PushActionAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "button_text",
        "authentication_required",
        "destructive",
        "foreground",
    )


@admin.register(UserDevice)
class UserDeviceAdmin(DeviceAdmin):
    pass


@admin.register(NotificationHistory)
class NotificationHistoryAdmin(admin.ModelAdmin):
    list_display = ("template_prefix", "channel", "instance_id", "created")
    date_hierarchy = "created"
    search_fields = (
        "template_prefix",
        "channel",
    )
