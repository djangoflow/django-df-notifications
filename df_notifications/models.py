import json
from celery import current_app as app
from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _
from fcm_django.models import AbstractFCMDevice
from .channels import send_notification


class NotificationChannels(models.IntegerChoices):
    PUSH = 100, "push"
    EMAIL = 200, "email"
    SMS = 300, "sms"
    CALL = 400, "call"
    CHAT = 500, "chat"
    SLACK = 600, "slack"
    WEBHOOK = 700, "webhook"

    CONSOLE = 1000, "console"


class AbstractNotificationBase(models.Model):
    channel = models.PositiveSmallIntegerField(choices=NotificationChannels.choices)
    subject = models.CharField(max_length=1024)
    body = models.TextField(null=True, blank=True)
    body_html = models.TextField(null=True, blank=True)
    data = models.TextField(null=True, blank=True)

    class Meta:
        abstract = True


class NotificationHistory(AbstractNotificationBase):
    id = models.BigAutoField(
        verbose_name=_("ID"),
        primary_key=True,
    )
    timestamp = models.DateTimeField(auto_now=True)
    users = models.ManyToManyField(
        settings.AUTH_USER_MODEL, help_text="Users this notification was sent to"
    )

    class Meta:
        verbose_name_plural = "Notification history"


class NotificationTemplate(AbstractNotificationBase):
    history = models.ManyToManyField(NotificationHistory, blank=True)
    # TODO: ^ this does not smell good - maybe notification history should have FK to template ?
    slug = models.CharField(max_length=255, unique=True)

    def get_device_queryset(self):
        return UserDevice.objects.all()

    def send(
        self,
        users=None,
        context=None,
        attachments=None,
    ):
        """
        :param users: users to be notified
        :param context: context
        :param attachments: attachments for email
        :return: history object
        """
        users = users or []
        attachments = attachments or []

        return send_notification(self, users, attachments, context)

    def save(self, *args, **kwargs):
        self.data = json.dumps(json.loads(self.data))
        super().save(*args, **kwargs)

    def send_async(self, users, instance, context=None):
        send_notification_async.delay(
            self.pk,
            [str(user.pk) for user in users],
            instance._meta.label_lower,
            str(instance.pk),
            additional_context=context,
        )


@app.task
def send_notification_async(
    template_pk, user_pks, model_name, model_pk, additional_context=None
):
    additional_context = additional_context or {}
    User = get_user_model()
    template: NotificationTemplate = NotificationTemplate.objects.get(pk=template_pk)
    Model = apps.get_model(model_name)
    instance = Model.objects.get(pk=model_pk)
    users = User.objects.filter(pk__in=user_pks)

    template.send(users, {"instance": instance, **additional_context})


class UserDevice(AbstractFCMDevice):
    class Meta:
        verbose_name = _("User device")
        verbose_name_plural = _("User devices")
