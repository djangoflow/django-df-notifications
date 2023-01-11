from django.conf import settings
from rest_framework.settings import APISettings


DEFAULTS = {
    "TRANSPORTS": [
        "df_notifications.transports.EmailTransport",
        "df_notifications.transports.ConsoleTransport",
        "df_notifications.transports.FirebasePushTransport",
        "df_notifications.transports.JSONPostWebhookTransport",
    ],
}

IMPORT_STRINGS = []

api_settings = APISettings(
    getattr(settings, "DF_NOTIFICATIONS", IMPORT_STRINGS), DEFAULTS
)
