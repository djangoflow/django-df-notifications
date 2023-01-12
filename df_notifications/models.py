from df_notifications.channels import BaseChannel
from df_notifications.fields import NoMigrationsChoicesField
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.db import transaction
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


class UserDevice(AbstractFCMDevice):
    class Meta:
        verbose_name = _("User device")
        verbose_name_plural = _("User devices")


# -------- Notifications ----------


class NotificationHistory(models.Model):
    users = models.ManyToManyField(User, blank=True)
    created = models.DateTimeField(auto_now_add=True, db_index=True)
    channel = NoMigrationsChoicesField(
        max_length=255,
        choices=[(key, key) for key in settings.DF_NOTIFICATIONS["CHANNELS"]],
    )
    template_prefix = models.CharField(max_length=255)
    content = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name_plural = "Notification history"

        indexes = [
            models.Index(fields=["template_prefix", "created"]),
            models.Index(fields=["channel", "created"]),
        ]


class NotificationMixin(models.Model):
    history = models.ManyToManyField(NotificationHistory, blank=True)
    channel = NoMigrationsChoicesField(
        max_length=255,
        choices=[(key, key) for key in settings.DF_NOTIFICATIONS["CHANNELS"]],
    )
    template_prefix = models.CharField(max_length=255)

    def render_parts(self, context: Dict[str, Any]):
        return {
            part: render_to_string(
                [
                    f"{self.template_prefix}_{self.channel}_{part}",
                    f"{self.template_prefix}_{part}",
                ],
                context=context,
            )
            for part in self.channel_instance.template_parts
        }

    def send_notification(self, users: List[User], context: Dict[str, Any]):
        parts = self.render_parts(context)
        self.channel_instance.send(users, {**context, **parts})

        notification = NotificationHistory.objects.create(
            channel=self.channel,
            template_prefix=self.template_prefix,
            content=parts if settings.DF_NOTIFICATIONS["SAVE_HISTORY_CONTENT"] else "",
        )
        notification.users.set(users)
        self.history.add(notification)

    @functools.cached_property
    def channel_instance(self) -> BaseChannel:
        return import_string(settings.DF_NOTIFICATIONS["CHANNELS"][self.channel])()

    class Meta:
        abstract = True


# ----------- Actions -------------


class BaseModelRule(GenericBase[M], models.Model):
    model: Type[M]

    @classmethod
    def get_queryset(cls, instance: M, prev: Optional[M]) -> QuerySet["BaseModelRule"]:
        return cls.objects.all()

    def check_condition(self, instance: M, prev: Optional[M]) -> bool:
        return True

    def perform_action(self, instance: M):
        pass

    @classmethod
    def invoke(cls, instance: M):
        prev_instance = getattr(instance, "_pre_save_instance", None)
        for action in cls.get_queryset(instance, prev_instance):
            if action.check_condition(instance, prev_instance):
                action.perform_action(instance)

    class Meta:
        abstract = True


class BaseModelReminder(GenericBase[M], models.Model):
    model: Type[M]
    model_queryset: Optional[QuerySet[M]] = None

    @classmethod
    def get_queryset(cls) -> QuerySet["BaseModelReminder"]:
        return cls.objects.all()

    def get_model_queryset(self) -> QuerySet[M]:
        return self.model_queryset or self.model.objects.all()

    def check_condition(self, instance: M) -> bool:
        return True

    def perform_action(self, instance: M):
        pass

    @classmethod
    def invoke(cls):
        for reminder in cls.get_queryset():
            for instance in reminder.get_model_queryset():
                if reminder.check_condition(instance):
                    reminder.perform_action(instance)

    class Meta:
        abstract = True


class NotificationModelMixin(NotificationMixin):
    model: Type[M]
    context = models.JSONField(default=dict, blank=True)

    def get_users(self, instance: M) -> List[User]:
        return []

    def get_context(self, instance: M) -> Dict[str, Any]:
        return {
            **self.context,
            "instance": instance,
        }

    def send(self, instance: M):
        self.send_notification(self.get_users(instance), self.get_context(instance))

    class Meta:
        abstract = True


class AsyncNotificationModelMixin(NotificationModelMixin):
    def send(self, instance: M) -> User:
        from .tasks import send_model_notification_async

        transaction.on_commit(
            lambda: send_model_notification_async.delay(
                self._meta.label_lower,
                str(self.pk),
                str(instance.pk),
            )
        )

    class Meta:
        abstract = True


class NotificationModelRule(NotificationModelMixin, BaseModelRule):
    def perform_action(self, instance: M):
        self.send(instance)

    class Meta:
        abstract = True


class NotificationModelReminder(NotificationModelMixin, BaseModelReminder):
    def perform_action(self, instance: M):
        self.send(instance)

    class Meta:
        abstract = True


class NotificationModelAsyncRule(AsyncNotificationModelMixin, NotificationModelRule):
    class Meta:
        abstract = True


class NotificationModelAsyncReminder(
    AsyncNotificationModelMixin, NotificationModelReminder
):
    class Meta:
        abstract = True
