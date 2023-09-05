from functools import cache
from typing import Any, Dict, Iterable, List, Union

from django.template.loader import render_to_string
from django.utils.module_loading import import_string

from df_notifications.channels import BaseChannel
from df_notifications.models import NotificationHistory, NotificationModelMixin
from df_notifications.settings import api_settings


@cache
def get_channel_instance(channel: NotificationModelMixin) -> BaseChannel:
    return import_string(api_settings.CHANNELS[channel])()  # type: ignore


def send_notification(
    users: type[Iterable[Any]],
    channel: str,
    template_prefixes: Union[List[str], str],
    context: Dict[str, Any],
) -> NotificationHistory:
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

    channel_instance.send(users, {**context, **parts})  # type: ignore

    notification = NotificationHistory.objects.create(
        channel=channel,
        template_prefix=template_prefixes[0],
        content=parts if api_settings.SAVE_HISTORY_CONTENT else "",
        instance=context.get("instance"),
    )
    notification.users.set(users)
    return notification
