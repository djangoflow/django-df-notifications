# type: ignore

from typing import Any, Dict, List, Type, Union

from celery import current_app as app
from django.apps import apps
from django.contrib.auth import get_user_model

from df_notifications.models import (
    BaseModelReminder,
    NotificationModelMixin,
    send_notification,
)
from df_notifications.settings import api_settings


@app.on_after_finalize.connect
def setup_periodic_tasks(sender: Any, **kwargs: Any) -> None:
    sender.add_periodic_task(
        api_settings.REMINDERS_CHECK_PERIOD, register_reminders_task.s()
    )


@app.task()
def register_reminders_task() -> None:
    for model in apps.get_models():
        if issubclass(model, BaseModelReminder):
            model.invoke()


@app.task
def send_model_notification_task(
    model_notification_class: str, notification_pk: int, model_pk: int
) -> None:
    ModelNotification: Type[NotificationModelMixin] = apps.get_model(
        model_notification_class
    )
    notification = ModelNotification.objects.get(pk=notification_pk)
    instance = ModelNotification.model.objects.get(pk=model_pk)
    NotificationModelMixin.send(notification, instance)


@app.task
def send_notification_task(
    user_ids: list,
    channel_name: str,
    template_prefixes: Union[List[str], str],
    context: Dict[str, Any],
) -> None:
    User = get_user_model()  # type: ignore
    users = User.objects.filter(id__in=user_ids)
    send_notification(users, channel_name, template_prefixes, context)
