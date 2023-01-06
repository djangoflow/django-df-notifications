from celery import current_app as app
from df_notifications.models import BaseReminder
from df_notifications.models import NotificationTemplate
from django.apps import apps
from django.contrib.auth import get_user_model


@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(60, register_reminders.s())


@app.task()
def register_reminders():
    for model in apps.get_models():
        if issubclass(model, BaseReminder):
            model.invoke()


@app.task
def send_notification_async(
    template_pk, user_pk, model_name, model_pk, additional_context=None
):
    additional_context = additional_context or {}
    User = get_user_model()
    template: NotificationTemplate = NotificationTemplate.objects.get(pk=template_pk)
    Model = apps.get_model(model_name)
    instance = Model.objects.get(pk=model_pk)
    user = User.objects.get(pk=user_pk)
    template.send(user, context={"instance": instance, **additional_context}, data={})
