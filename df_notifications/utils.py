from df_notifications.channels import BaseChannel
from df_notifications.channels import User
from df_notifications.models import NotificationHistory
from django.conf import settings
from django.template import Context
from django.template import Template
from django.utils.module_loading import import_string
from functools import cache
from render_block.django import _build_block_context
from render_block.django import _render_template_block
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
    parts = {}
    for part in channel_instance.template_parts:
        parts[part] = render_block(
            template, f"{part}__{channel}", context=context
        ) or render_block(template, part, context=context)

    channel_instance.send(users, {**context, **parts})

    notification = NotificationHistory.objects.create(
        channel=channel,
        template=template,
        content=parts if settings.DF_NOTIFICATIONS["SAVE_HISTORY_CONTENT"] else "",
        instance=context.get("instance"),
    )
    notification.users.set(users)
    return notification


def render_block(template: str, block: str, context: Dict[str, Any]):
    context_instance = Context(context)
    t = Template(
        f"""{{% extends '{template}' %}}
        {{% block {block} %}}{{{{ block.super }}}}{{% endblock %}}
        """
    )
    with context_instance.bind_template(t):
        _build_block_context(t, context_instance)
        return _render_template_block(t, block, context_instance)
