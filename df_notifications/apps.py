from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class DFNotificationsConfig(AppConfig):
    default_auto_field = "hashid_field.BigHashidAutoField"
    api_path = "notifications/"
    name = "df_notifications"
    verbose_name = _("DjangoFlow Notifications")

    def ready(self):
        try:
            import df_notifications.signals  # noqa F401
        except ImportError:
            pass
