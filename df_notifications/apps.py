from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class DFNotificationsConfig(AppConfig):
    name = "df_notifications"
    verbose_name = _("DjangoFlow Notifications")

    def ready(self) -> None:
        try:
            import df_notifications.signals  # noqa F401
        except ImportError:
            pass

    class DFMeta:
        api_path = "notifications/"
