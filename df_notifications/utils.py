from df_notifications.channels import BaseChannel
from df_notifications.channels import User
from df_notifications.models import NotificationHistory
from django.conf import settings
from django.utils.module_loading import import_string
from functools import cache
from render_block import render_block_to_string
from typing import Any
from typing import Dict
from typing import List


@cache
def get_channel_instance(channel) -> BaseChannel:
    return import_string(settings.DF_NOTIFICATIONS["CHANNELS"][channel])()


def send_notification(
    users: List[User], channel: str, template: str, context: Dict[str, Any]
):
    channel_instance = get_channel_instance(channel)
    parts = {
        part: render_block_to_string(template, part, context=context)
        for part in channel_instance.template_parts
    }
    channel_instance.send(users, {**context, **parts})

    notification = NotificationHistory.objects.create(
        channel=channel,
        template=template,
        content=parts if settings.DF_NOTIFICATIONS["SAVE_HISTORY_CONTENT"] else "",
        instance=context.get("instance"),
    )
    notification.users.set(users)
    return notification
