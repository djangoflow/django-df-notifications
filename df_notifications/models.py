from dbtemplates.models import Template as DbTemplate
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.db import models
from django.db.models import QuerySet
from django.template.loader import render_to_string
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _
from fcm_django.models import AbstractFCMDevice
from typing import Any
from typing import Dict
from typing import Generic
from typing import List
from typing import Optional
from typing import Type
from typing import TYPE_CHECKING
from typing import TypeVar

import functools


M = TypeVar("M", bound=models.Model)

User = get_user_model()

# https://code.djangoproject.com/ticket/33174
if TYPE_CHECKING:

    class GenericBase(Generic[M]):
        pass

else:

    class GenericBase:
        def __class_getitem__(cls, _):
            return cls


# class NotificationChannels(models.IntegerChoices):
#     PUSH = 100, "push"
#     EMAIL = 200, "email"
#     SMS = 300, "sms"
#     CALL = 400, "call"
#     CHAT = 500, "chat"
#     SLACK = 600, "slack"
#     WEBHOOK = 700, "webhook"
#     CONSOLE = 1000, "console"
#
#
# class AbstractNotificationBase(models.Model):
#     channel = models.PositiveSmallIntegerField(choices=NotificationChannels.choices)
#     subject = models.CharField(max_length=1024)
#     body = models.TextField(null=True, blank=True)
#     body_html = models.TextField(null=True, blank=True)
#     data = models.TextField(null=True, blank=True)
#
#     class Meta:
#         abstract = True


# class NotificationHistory(AbstractNotificationBase):
#     id = models.BigAutoField(
#         verbose_name=_("ID"),
#         primary_key=True,
#     )
#     timestamp = models.DateTimeField(auto_now=True)
#     users = models.ManyToManyField(
#         settings.AUTH_USER_MODEL, help_text="Users this notification was sent to"
#     )
#
#     class Meta:
#         verbose_name_plural = "Notification history"


# class NotificationTemplate(AbstractNotificationBase):
#     history = models.ManyToManyField(NotificationHistory, blank=True)
#     # Example: notifications/bookings/new_booking
#     # The we render {template_prefix}_subject
#     # The we render {template_prefix}_body
#     # The we render {template_prefix}_body_html
#     # The we render {template_prefix}_data
#     # and so on....
#     # We can fall back to _body if body_html does not exist
#     # also have email_body_html -> email_body -> body etc
#     # template will be notificaations/channel/prefix
#     # notifications/push/base_body.txt
#     # notifications/push/base_email_subject.txt
#     # notifications/base_body.html
#
#     template_prefix = models.CharField(max_length=255, unique=True)
#
#     email_template = "df_notifications/base_email.html"
#     slack_template = "df_notifications/base_slack.html"
#
#     def get_device_queryset(self):
#         return UserDevice.objects.all()
#
#     def send(
#             self,
#             users=None,
#             context=None,
#             attachments=None,
#     ):
#         users = users or []
#         attachments = attachments or []
#         """
#         :param users: users to be notified
#         :param context: context
#         :param attachments: attachments for email
#         :return: history object
#         """
#
#         _context = Context(context)
#
#         subject = Template("".join(self.subject.splitlines())).render(_context)
#
#         data = json.loads(Template(self.data).render(_context)) if self.data else {}
#         body = Template(self.body).render(_context)
#
#         body_html = Template(
#             (
#                 f'{{% extends "{self.email_template}"%}}{{% block body %}}'
#                 f"{self.body_html}{{% endblock %}}"
#             )
#             if self.channel == NotificationChannels.EMAIL
#             else self.body_html
#         ).render(_context)
#
#         if self.channel == NotificationChannels.EMAIL:
#             to_emails = [user.email for user in users if user.email]
#             msg = EmailMultiAlternatives(subject=subject, to=to_emails, body=body)
#             msg.attach_alternative(body_html, "text/html")
#             for attachment in attachments:
#                 msg.attach(**attachment)
#             msg.send()
#         elif self.channel == NotificationChannels.PUSH:
#             devices = self.get_device_queryset().filter(
#                 user__in=users,
#             )
#             devices.send_message(
#                 Message(
#                     notification=Notification(
#                         title=subject,
#                         body=body,
#                     ),
#                     data=data,
#                 ),
#             )
#         elif self.channel == NotificationChannels.SLACK:
#             slack_message(
#                 self.slack_template,
#                 context=context,
#                 attachments=[{"text": body, "title": subject}],
#             )
#         elif self.channel == NotificationChannels.WEBHOOK:
#             requests.post(subject, data=body, json=data)
#         elif self.channel == NotificationChannels.CONSOLE:
#             logging.info(f"Notification: {subject}")
#         else:
#             raise NotImplementedError
#
#         history = NotificationHistory.objects.create(
#             channel=self.channel,
#             data=data,
#             body=body,
#             subject=subject,
#             body_html=body_html,
#         )
#         history.users.set(users)
#         self.history.add(history)
#         return history
#
#     def save(self, *args, **kwargs):
#         self.data = json.dumps(json.loads(self.data))
#         super().save(*args, **kwargs)
#
#     def send_async(self, users, instance, context=None):
#         send_notification_async.delay(
#             self.pk,
#             [str(user.pk) for user in users],
#             instance._meta.label_lower,
#             str(instance.pk),
#             additional_context=context,
#         )
#
#


class UserDevice(AbstractFCMDevice):
    class Meta:
        verbose_name = _("User device")
        verbose_name_plural = _("User devices")


# -------- Notifications ----------


class BaseTransport:
    key: str
    template_parts: List[str]
    title_part: str
    additional_data: List[str]
    config_items: List[str]

    def send(self, user: User, data: Dict[str, str], config_items: Dict[str, str]):
        pass


class EmailTransport(BaseTransport):
    key = "email"
    template_parts = ["subject", "body", "body_html"]
    title_part = "subject"
    additional_data = ["attachments"]
    config_items = ["recipient"]

    def send(self, user: User, data: Dict[str, Any], config_items: Dict[str, str]):
        recipient = config_items.get("recipient", user.email)
        msg = EmailMultiAlternatives(
            subject=data["subject"], to=[recipient], body=data["body"]
        )
        msg.attach_alternative(data["body_html"], "text/html")
        for attachment in data.get("attachments", []):
            msg.attach(**attachment)
        msg.send()


class ConsoleTransport(BaseTransport):
    key = "console"
    template_parts = ["title", "body"]
    title_part = "title"
    additional_data = []
    config_items = []

    def send(self, user: User, data: Dict[str, Any], config_items: Dict[str, str]):
        print(f"user: {user}; title: {data['title']}; body: {data['body']}")


class NotificationChannel(models.Model):
    transport_class = models.CharField(
        max_length=255
    )  # TODO: get choices from settings

    def save(self, *args, **kwargs):
        created = self.pk is None
        super().save(*args, **kwargs)
        if created:
            for item_key in self.transport.config_items:
                NotificationChannelConfigItem.objects.create(
                    channel=self,
                    key=item_key,
                )

    def send(self, user: User, data: Dict[str, Any]):
        self.transport.send(
            user, data, config_items={item.key: item.value for item in self.items.all()}
        )

    @functools.cached_property
    def transport(self) -> BaseTransport:
        return import_string(self.transport_class)()

    def __str__(self):
        return self.transport.key


class NotificationChannelConfigItem(models.Model):
    channel = models.ForeignKey(
        NotificationChannel, on_delete=models.CASCADE, related_name="items"
    )
    key = models.CharField(max_length=255)
    value = models.CharField(max_length=1024, default="", blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["channel", "key"], name="channel_key_unique"
            )
        ]


class NotificationTemplate(models.Model):
    channel = models.ForeignKey(NotificationChannel, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)

    @property
    def title(self):
        return self.parts.get(name=self.channel.transport.title_part).content

    def send(self, user: User, context: Dict[str, Any], data: Dict[str, Any]):
        rendered_parts = {
            part.name: render_to_string(part.template_name, context=context)
            for part in self.parts.all()
        }
        self.channel.send(user, {**data, **rendered_parts})
        notification = NotificationHistory.objects.create(
            user=user,
            template=self,
            title=rendered_parts[self.channel.transport.title_part],
        )
        for name, content in rendered_parts.items():
            NotificationHistoryPart.objects.create(
                notification=notification,
                name=name,
                content=content,
            )

    def save(self, *args, **kwargs):
        created = self.pk is None
        super().save(*args, **kwargs)
        if created:
            for name in self.channel.transport.template_parts:
                NotificationTemplatePart(
                    name=name,
                    template=self,
                ).save()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["channel", "name"], name="channel_name_unique"
            )
        ]

    def __str__(self):
        return self.name


class NotificationTemplatePart(models.Model):
    name = models.CharField(max_length=255)
    content = models.TextField(default="", blank=True)
    template = models.ForeignKey(
        NotificationTemplate, on_delete=models.CASCADE, related_name="parts"
    )
    db_template = models.ForeignKey(
        DbTemplate, on_delete=models.CASCADE, related_name="template_part"
    )

    @property
    def template_name(self):
        return (
            f"df_notification/{self.template.name}/{self.template.channel}/{self.name}"
        )

    def save(self, *args, **kwargs):
        created = self.pk is None
        db_template, _ = DbTemplate.objects.get_or_create(name=self.template_name)
        db_template.content = self.content
        db_template.save()
        if created:
            self.db_template = db_template
        super().save(*args, **kwargs)


class NotificationHistory(models.Model):
    template = models.ForeignKey(
        NotificationTemplate, on_delete=models.CASCADE, related_name="history"
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True, db_index=True)
    title = models.CharField(max_length=255)

    class Meta:
        verbose_name_plural = "Notification history"

        indexes = [
            models.Index(fields=["user", "template", "created"]),
            models.Index(fields=["template", "created"]),
        ]


class NotificationHistoryPart(models.Model):
    notification = models.ForeignKey(
        NotificationHistory, on_delete=models.CASCADE, db_index=True
    )
    name = models.CharField(max_length=255)
    content = models.TextField(default="", blank=True)


# ----------- Actions -------------


class BaseAction(GenericBase[M], models.Model):
    model: Type[M]

    @classmethod
    def get_queryset(cls, instance: M, prev: Optional[M]) -> QuerySet["BaseAction"]:
        return cls.objects.all()

    def condition(self, instance: M, prev: Optional[M]) -> bool:
        return True

    def perform_action(self, instance: M, prev: Optional[M]):
        pass

    @classmethod
    def invoke(cls, instance: M):
        prev_instance = getattr(instance, "_pre_save_instance", None)
        for action in cls.get_queryset(instance, prev_instance):
            if action.condition(instance, prev_instance):
                action.perform_action(instance, prev_instance)

    class Meta:
        abstract = True


class BaseReminder(GenericBase[M], models.Model):
    model: Type[M]
    model_queryset: Optional[QuerySet[M]] = None

    @classmethod
    def get_queryset(cls) -> QuerySet["BaseReminder"]:
        return cls.objects.all()

    def get_model_queryset(self) -> QuerySet[M]:
        return self.model_queryset or self.model.objects.all()

    def condition(self, instance: M) -> bool:
        return True

    def perform_action(self, instance: M):
        pass

    @classmethod
    def invoke(cls):
        for reminder in cls.get_queryset():
            for instance in reminder.get_model_queryset():
                if reminder.condition(instance):
                    reminder.perform_action(instance)

    class Meta:
        abstract = True


class NotificationMixin(models.Model):
    template = models.ForeignKey(NotificationTemplate, on_delete=models.CASCADE)

    def get_user(self, instance: M, prev: Optional[M]) -> User:
        raise NotImplementedError()

    def get_additional_data(self, instance: M, prev: Optional[M]) -> Dict[str, Any]:
        return {}

    def send_notification(self, instance: M, prev: Optional[M]) -> User:
        self.template.send(
            user=self.get_user(instance, prev),
            context={
                "instance": instance,
                "prev": prev,
            },
            data=self.get_additional_data(instance, prev),
        )

    class Meta:
        abstract = True


class AsyncNotificationMixin(NotificationMixin):
    model: Type[M]

    def send_notification(self, instance: M, prev: Optional[M]) -> User:
        from .tasks import send_notification_async

        send_notification_async.delay(
            template_pk=self.template.pk,
            user_pk=self.get_user(instance, prev).pk,
            model_name=self.model._meta.label_lower,
            model_pk=instance.pk,
        )

    class Meta:
        abstract = True


class NotificationAction(BaseAction, NotificationMixin):
    def perform_action(self, instance: M, prev: Optional[M]):
        self.send_notification(instance, prev)

    class Meta:
        abstract = True


class NotificationReminder(BaseReminder, NotificationMixin):
    def perform_action(self, instance: M):
        self.send_notification(instance, None)

    class Meta:
        abstract = True


class NotificationAsyncAction(AsyncNotificationMixin, NotificationAction):
    class Meta:
        abstract = True


class NotificationAsyncReminder(AsyncNotificationMixin, NotificationReminder):
    class Meta:
        abstract = True
