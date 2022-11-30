from .models import NotificationHistory
from .models import NotificationTemplate
from .models import UserDevice
from django.contrib import admin
from fcm_django.admin import DeviceAdmin
from fcm_django.models import FCMDevice
from import_export import resources
from import_export.admin import ImportExportMixin


class NotificationHistoryResourceMixin(resources.ModelResource):
    class Meta:
        import_id_fields = ("id",)
        fields = (
            # "id",
            "users",
            "channel",
            "subject",
            "body",
            "body_html",
            "data",
            "timestamp",
        )
        skip_unchanged = True
        report_skipped = True
        export_order = fields
        model = NotificationHistory


@admin.register(NotificationHistory)
class NotificationHistoryAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = NotificationHistoryResourceMixin

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


class NotificationTemplateResourceMixin(resources.ModelResource):
    class Meta:
        import_id_fields = ("id",)
        fields = (
            "id",
            "channel",
            "subject",
            "body",
            "body_html",
            "data",
        )
        skip_unchanged = True
        report_skipped = True
        export_order = fields
        model = NotificationTemplate


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = NotificationTemplateResourceMixin
    search_fields = ("slug",)
    list_display = ("slug", "channel", "subject")
