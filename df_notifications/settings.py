from django.conf import settings
from rest_framework.settings import APISettings


DEFAULTS = {
    "CHANNELS": {
        "email": "df_notifications.channels.EmailChannel",
        "console": "df_notifications.channels.ConsoleChannel",
        "push": "df_notifications.channels.FirebasePushChannel",
        "webhook": "df_notifications.channels.JSONPostWebhookChannel",
        "chat": "df_notifications.channels.FirebaseChatChannel",
        "slack": "df_notifications.channels.SlackChannel",
        "sms": "df_notifications.channels.TwilioSMSChannel",
        "twitter": "df_notifications.channels.TwitterChannel",


    },
    "SAVE_HISTORY_CONTENT": True,
    "REMINDERS_CHECK_PERIOD": 60,
    "TWITTER_CONSUMER_KEY": '',
    "TWITTER_CONSUMER_SECRET": '',
    "TWITTER_ACCESS_TOKEN": '',
    "TWITTER_ACCESS_TOKEN_SECRET": '',
    "TWITTER_USERNAME": ''
}

IMPORT_STRINGS = []

api_settings = APISettings(
    getattr(settings, "DF_NOTIFICATIONS", None), DEFAULTS, IMPORT_STRINGS
)
