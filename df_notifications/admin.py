from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest
from fcm_django.admin import DeviceAdmin
from fcm_django.models import FCMDevice

from .models import (
    CustomPushMessage,
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


@admin.register(CustomPushMessage)
class CustomPushMessageAdmin(admin.ModelAdmin):
    list_display = ("title", "created", "sent")
    date_hierarchy = "created"
    search_fields = ("title",)
    autocomplete_fields = ("audience",)

    def send(self, request: HttpRequest, queryset: QuerySet[CustomPushMessage]) -> None:
        for obj in queryset:
            obj.send()
        self.message_user(request, "Messages sent")

    send.short_description = "Send selected messages"

    actions = [send]
