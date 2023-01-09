from .models import NotificationChannel
from .models import NotificationChannelConfigItem
from .models import NotificationHistory
from .models import NotificationHistoryPart
from .models import NotificationTemplate
from .models import NotificationTemplatePart
from .models import UserDevice
from django.contrib import admin
from fcm_django.admin import DeviceAdmin
from fcm_django.models import FCMDevice


admin.site.unregister(FCMDevice)


@admin.register(UserDevice)
class UserDeviceAdmin(DeviceAdmin):
    pass


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

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ["transport_class"]
        else:
            return []


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


class NotificationHistoryPartInline(admin.TabularInline):
    model = NotificationHistoryPart
    fields = ("name", "content")
    fk_name = "notification"
    readonly_fields = ("name", "content")
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(NotificationHistory)
class NotificationHistoryAdmin(admin.ModelAdmin):
    list_display = ("template", "user", "created")
    date_hierarchy = "created"
    list_filter = ("template", "user")
    search_fields = ("title",)
    inlines = (NotificationHistoryPartInline,)
