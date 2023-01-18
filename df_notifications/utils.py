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


@cache
def channel_instance(channel) -> BaseChannel:
    return import_string(settings.DF_NOTIFICATIONS["CHANNELS"][channel])()


def render_parts(channel_name: str, template_prefix: str, context: Dict[str, Any]):
    channel = channel_instance(channel_name)
    return {
        part: render_to_string(
            [
                f"{template_prefix}_{channel_name}_{part}",
                f"{template_prefix}_{part}",
            ],
            context=context,
        )
        for part in channel.template_parts
    }


def send_notification(
    users: List[User], channel_name: str, template_prefix: str, context: Dict[str, Any]
):
    channel = channel_instance(channel_name)
    parts = render_parts(channel_name, template_prefix, context)
    channel.send(users, {**context, **parts})

    notification = NotificationHistory.objects.create(
        channel=channel_name,
        template_prefix=template_prefix,
        content=parts if settings.DF_NOTIFICATIONS["SAVE_HISTORY_CONTENT"] else "",
        instance=context.get("instance"),
    )
    notification.users.set(users)
    return notification
