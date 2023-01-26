from celery import current_app as app
from df_notifications.models import BaseModelReminder
from df_notifications.models import NotificationModelMixin
from df_notifications.models import User
from df_notifications.utils import send_notification
from django.apps import apps
from django.conf import settings
from typing import Type


@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(
        settings.DF_NOTIFICATIONS["REMINDERS_CHECK_PERIOD"], register_reminders.s()
    )


@app.task()
def register_reminders():
    for model in apps.get_models():
        if issubclass(model, BaseModelReminder):
            model.invoke()


@app.task
def send_model_notification_async(model_notification_class, notification_pk, model_pk):
    ModelNotification: Type[NotificationModelMixin] = apps.get_model(
        model_notification_class
    )
    notification = ModelNotification.objects.get(pk=notification_pk)
    instance = ModelNotification.model.objects.get(pk=model_pk)
    NotificationModelMixin.send(notification, instance)


@app.task
def send_notification_async(user_ids, channel_name, template, context):
    users = User.objects.filter(id__in=user_ids)
    send_notification(users, channel_name, template, context)
