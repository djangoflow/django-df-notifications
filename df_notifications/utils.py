from df_notifications.channels import BaseChannel
from df_notifications.channels import User
from df_notifications.models import NotificationHistory
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.module_loading import import_string
from functools import cache
from typing import Any
from typing import Dict
from typing import List
from typing import Union


@cache
def get_channel_instance(channel) -> BaseChannel:
    return import_string(settings.DF_NOTIFICATIONS["CHANNELS"][channel])()


def send_notification(
    users: List[User],
    channel: str,
    template_prefixes: Union[List[str], str],
    context: Dict[str, Any],
):
    if isinstance(template_prefixes, str):
        template_prefixes = [template_prefixes]

    channel_instance = get_channel_instance(channel)
    parts = {}
    for part in channel_instance.template_parts:
        templates = []
        for prefix in template_prefixes:
            templates.append(f"{prefix}{channel}__{part}")
            templates.append(f"{prefix}{part}")
        parts[part] = render_to_string(templates, context=context).strip()

    channel_instance.send(users, {**context, **parts})

    notification = NotificationHistory.objects.create(
        channel=channel,
        template_prefix=template_prefixes[0],
        content=parts if settings.DF_NOTIFICATIONS["SAVE_HISTORY_CONTENT"] else "",
        instance=context.get("instance"),
    )
    notification.users.set(users)
    return notification
