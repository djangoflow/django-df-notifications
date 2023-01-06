from .models import NotificationChannel
from .models import NotificationChannelConfigItem
from .models import NotificationTemplate
from .models import NotificationTemplatePart
from .models import UserDevice
from django.contrib import admin
from fcm_django.admin import DeviceAdmin
from fcm_django.models import FCMDevice


# class NotificationHistoryResourceMixin(resources.ModelResource):
#     class Meta:
#         import_id_fields = ("id",)
#         fields = (
#             # "id",
#             "users",
#             "channel",
#             "subject",
#             "body",
#             "body_html",
#             "data",
#             "timestamp",
#         )
#         skip_unchanged = True
#         report_skipped = True
#         export_order = fields
#         model = NotificationHistory
#
#
# @admin.register(NotificationHistory)
# class NotificationHistoryAdmin(ImportExportMixin, admin.ModelAdmin):
#     resource_class = NotificationHistoryResourceMixin
#
#     def get_users(self, obj):
#         return ",".join(obj.users.values_list("email", flat=True))
#
#     get_users.short_description = "users"
#
#     date_hierarchy = "timestamp"
#     search_fields = ("users__email",)
#     list_display = (
#         "timestamp",
#         "channel",
#         "get_users",
#         "subject",
#     )
#
#
admin.site.unregister(FCMDevice)


@admin.register(UserDevice)
class UserDeviceAdmin(DeviceAdmin):
    pass


#
#
# class NotificationTemplateResourceMixin(resources.ModelResource):
#     class Meta:
#         import_id_fields = ("id",)
#         fields = (
#             "id",
#             "channel",
#             "subject",
#             "body",
#             "body_html",
#             "data",
#         )
#         skip_unchanged = True
#         report_skipped = True
#         export_order = fields
#         model = NotificationTemplate
#
#
# @admin.register(NotificationTemplate)
# class NotificationTemplateAdmin(ImportExportMixin, admin.ModelAdmin):
#     resource_class = NotificationTemplateResourceMixin
#     search_fields = ("template_prefix",)
#     list_display = ("template_prefix", "channel", "subject")


class NotificationChannelConfigItemInline(admin.TabularInline):
    model = NotificationChannelConfigItem
    fields = ("key", "value")
    readonly_fields = ("key",)
    fk_name = "channel"
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(NotificationChannel)
class NotificationChannelAdmin(admin.ModelAdmin):
    list_display = ("transport_class", "param")
    inlines = (NotificationChannelConfigItemInline,)

    def param(self, obj: NotificationChannel):
        item = obj.items.first()
        return item.value if item else None


class NotificationTemplatePartInline(admin.TabularInline):
    model = NotificationTemplatePart
    fields = ("name", "content")
    fk_name = "template"
    readonly_fields = ["name"]
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    list_display = ("name", "channel", "title")
    exclude = ("parts",)
    inlines = (NotificationTemplatePartInline,)

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ["channel"]
        else:
            return []
