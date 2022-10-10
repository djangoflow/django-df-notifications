from .models import NotificationHistory
from .models import NotificationTemplate
from .models import UserDevice
from django.contrib import admin
from fcm_django.admin import DeviceAdmin
from fcm_django.models import FCMDevice


@admin.register(NotificationHistory)
class NotificationHistoryAdmin(admin.ModelAdmin):
    def get_users(self, obj):
        return ",".join(obj.users.values_list("email", flat=True))

    get_users.short_description = "users"

    date_hierarchy = "timestamp"
    search_fields = ("users__email",)
    list_display = (
        "timestamp",
        "channel",
        "get_users",
        "subject",
    )


admin.site.unregister(FCMDevice)


@admin.register(UserDevice)
class UserDeviceAdmin(DeviceAdmin):
    pass


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    search_fields = ("slug",)
    list_display = ("slug", "channel", "subject")
