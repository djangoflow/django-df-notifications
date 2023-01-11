from dbtemplates.models import Template as DbTemplate
from df_notifications.fields import NoMigrationsChoicesField
from df_notifications.transports import BaseTransport
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import QuerySet
from django.template.loader import render_to_string
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _
from fcm_django.models import AbstractFCMDevice
from typing import Any
from typing import Dict
from typing import Generic
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


class UserDevice(AbstractFCMDevice):
    class Meta:
        verbose_name = _("User device")
        verbose_name_plural = _("User devices")


# -------- Notifications ----------


class NotificationChannel(models.Model):
    transport_class = NoMigrationsChoicesField(
        max_length=255,
        choices=[(t, t) for t in settings.DF_NOTIFICATIONS["TRANSPORTS"]],
    )

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

    @functools.cached_property
    def _first_config_item_value(self):
        if not self.transport.config_items:
            return None
        return [
            item.value
            for item in self.items.all()
            if item.key == self.transport.config_items[0]
        ][0]

    def __str__(self):
        if self._first_config_item_value:
            return f"{self.transport.key} {self._first_config_item_value}"

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
        return self.parts.get(name=self.channel.transport.get_title_part()).content

    def send(self, user: User, context: Dict[str, Any], data: Dict[str, Any]):
        rendered_parts = {
            part.name: render_to_string(part.template_name, context=context)
            for part in self.parts.all()
        }
        self.channel.send(user, {**data, **rendered_parts})
        notification = NotificationHistory.objects.create(
            user=user,
            template=self,
            title=rendered_parts[self.channel.transport.get_title_part()],
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
