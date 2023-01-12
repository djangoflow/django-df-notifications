from django.conf import settings
from rest_framework.settings import APISettings


DEFAULTS = {
    "CHANNELS": {
        "email": "df_notifications.channels.EmailChannel",
        "console": "df_notifications.channels.ConsoleChannel",
        "push": "df_notifications.channels.FirebasePushChannel",
        "webhook": "df_notifications.channels.JSONPostWebhookChannel",
    },
    "SAVE_HISTORY_CONTENT": True,
}

IMPORT_STRINGS = []

api_settings = APISettings(
    getattr(settings, "DF_NOTIFICATIONS", IMPORT_STRINGS), DEFAULTS
)
