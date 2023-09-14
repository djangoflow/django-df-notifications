from datetime import timedelta
from functools import cache
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generic,
    Iterable,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
)

from celery import current_app as app
from django.conf import settings
from django.contrib.contenttypes.fields import (
    GenericForeignKey,
    GenericRelation,
)
from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction
from django.db.models import Count, Q, QuerySet
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _
from fcm_django.models import AbstractFCMDevice

from df_notifications.channels import BaseChannel
from df_notifications.fields import NoMigrationsChoicesField
from df_notifications.settings import api_settings

M = TypeVar("M", bound=models.Model)

# https://code.djangoproject.com/ticket/33174
if TYPE_CHECKING:

    class GenericBase(Generic[M]):
        pass

else:

    class GenericBase:
        def __class_getitem__(cls, _):
            return cls


@cache
def get_channel_instance(channel: "NotificationModelMixin") -> BaseChannel:
    return import_string(api_settings.CHANNELS[channel])()  # type: ignore


def send_notification(
    users: type[Iterable[Any]],
    channel: str,
    template_prefixes: Union[List[str], str],
    context: Dict[str, Any],
) -> "NotificationHistory":
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


class UserDevice(AbstractFCMDevice):
    user = models.ForeignKey(  # type: ignore
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_query_name=_("fcmdevice"),  # type: ignore
    )

    class Meta:
        verbose_name = _("User device")
        verbose_name_plural = _("User devices")


class PushActionCategory(models.Model):
    name = models.CharField(max_length=64, unique=True, verbose_name="id")
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.name

    class Meta:
        verbose_name = _("Push action category")
        verbose_name_plural = _("Push action categories")


class PushAction(models.Model):
    category = models.ForeignKey(
        PushActionCategory, on_delete=models.CASCADE, related_name="actions"
    )
    name = models.CharField(max_length=64, unique=True, verbose_name="id")
    sequence = models.IntegerField(default=1000)

    button_text = models.CharField(max_length=64)
    authentication_required = models.BooleanField(default=False)
    destructive = models.BooleanField(default=False)
    foreground = models.BooleanField(default=False)

    class Meta:
        ordering = ["category", "sequence"]

    def __str__(self) -> str:
        return self.name


# -------- Notifications ----------


class NotificationHistoryQuerySet(models.QuerySet):
    def for_instance(self, instance: M) -> models.QuerySet:
        return self.filter(
            instance_id=instance.pk,
            content_type=ContentType.objects.get_for_model(instance).id,
        )


class NotificationHistory(models.Model):
    id = models.BigAutoField(primary_key=True)
    users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True)
    created = models.DateTimeField(auto_now_add=True, db_index=True)
    channel = NoMigrationsChoicesField(
        max_length=255,
        choices=[(key, key) for key in api_settings.CHANNELS],
    )
    template_prefix = models.CharField(max_length=255)
    content = models.JSONField(default=dict, blank=True)

    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, null=True, blank=True
    )
    instance_id = models.PositiveBigIntegerField(null=True, blank=True)
    instance = GenericForeignKey("content_type", "instance_id")

    objects = NotificationHistoryQuerySet.as_manager()

    class Meta:
        verbose_name_plural = "Notification history"

        indexes = [
            models.Index(fields=["template_prefix", "created"]),
            models.Index(fields=["channel", "created"]),
            models.Index(fields=["content_type", "instance_id", "created"]),
        ]


class NotifiableModelMixin(models.Model):
    notifications = GenericRelation(NotificationHistory, "instance_id")

    class Meta:
        abstract = True


# ----------- Actions -------------


class BaseModelRule(GenericBase[M], models.Model):
    model: Type[M]
    tracking_fields: Optional[List[str]] = None

    @classmethod
    def compare_fields(cls, instance: M, prev: Optional[M]) -> bool:
        if cls.tracking_fields is None or prev is None:
            return True

        for field in cls.tracking_fields:
            if getattr(instance, field) != getattr(prev, field):
                return True

        return False

    @classmethod
    def get_queryset(cls, instance: M, prev: Optional[M]) -> QuerySet["BaseModelRule"]:
        return cls.objects.all()

    def check_condition(self, instance: M, prev: Optional[M]) -> bool:
        return True

    def perform_action(self, instance: M) -> None:
        pass

    @classmethod
    def invoke(cls, instance: M) -> None:
        prev = getattr(instance, "_pre_save_instance", None)

        if not cls.compare_fields(instance, prev):
            return

        for action in cls.get_queryset(instance, prev):
            if action.check_condition(instance, prev):
                action.perform_action(instance)

    class Meta:
        abstract = True


class BaseModelReminder(GenericBase[M], models.Model):
    model: Type[M]

    @classmethod
    def get_queryset(cls) -> QuerySet["BaseModelReminder"]:
        return cls.objects.all()

    def get_model_queryset(self) -> QuerySet[M]:
        return self.model.objects.all()

    def check_condition(self, instance: M) -> bool:
        return True

    def perform_action(self, instance: M) -> None:
        pass

    @classmethod
    def invoke(cls) -> None:
        for reminder in cls.get_queryset():
            for instance in reminder.get_model_queryset():
                if reminder.check_condition(instance):
                    reminder.perform_action(instance)

    class Meta:
        abstract = True


class NotificationModelMixin(models.Model):
    model: Type[M]
    admin_list_display: List[str] = ["channel", "template_prefix"]

    history = models.ManyToManyField(NotificationHistory, blank=True, editable=False)
    channel = NoMigrationsChoicesField(
        max_length=255,
        choices=[(key, key) for key in api_settings.CHANNELS],
    )
    template_prefix = models.CharField(max_length=255)
    context = models.JSONField(default=dict, blank=True)

    def get_users(self, instance: M) -> list:
        return []

    def get_context(self, instance: M) -> Dict[str, Any]:
        return {
            **self.context,
            "instance": instance,
        }

    def get_template_prefixes(self) -> list:
        return [
            self.template_prefix,
            f"{self.model._meta.app_label}/df_notifications/{self.model._meta.model_name}/",
        ]

    def send(self, instance: M) -> None:
        notification = send_notification(
            self.get_users(instance),  # type: ignore
            self.channel,
            self.get_template_prefixes(),
            self.get_context(instance),
        )
        self.history.add(notification)

    class Meta:
        abstract = True


class AsyncNotificationMixin:
    def send(self, instance: M) -> None:
        transaction.on_commit(
            lambda: app.send_task(
                "df_notifications.tasks.send_model_notification_task",
                args=[
                    self._meta.label_lower,
                    str(self.pk),
                    str(instance.pk),
                ],
            )
        )


class NotificationModelRule(NotificationModelMixin, BaseModelRule):
    def perform_action(self, instance: M) -> None:
        self.send(instance)

    class Meta:
        abstract = True


class NotificationModelReminder(NotificationModelMixin, BaseModelReminder):
    MODIFIED_MODEL_FIELD = "modified"

    delay = models.DurationField(
        help_text="Send the reminder after this period of time",
        default=timedelta(seconds=0),
    )
    cooldown = models.DurationField(
        help_text="Wait so much time before reminding again",
        default=timedelta(hours=1),
    )
    repeat = models.SmallIntegerField(
        help_text="Repeat the reminder this many times", default=1
    )
    action = models.TextField(
        help_text="Python code to execute. You can use "
        "`instance` variable to access current model",
        default="",
        blank=True,
    )

    def get_model_queryset(self) -> QuerySet[M]:
        return (
            super(NotificationModelReminder, self)
            .get_model_queryset()
            .filter(**{f"{self.MODIFIED_MODEL_FIELD}__lt": timezone.now() - self.delay})
            .annotate(
                notification_count=Count(
                    "notifications__id",
                    filter=Q(notifications__in=self.history.all()),
                ),
            )
            .filter(Q(notification_count__lt=self.repeat))
            .exclude(
                Q(notifications__in=self.history.all())
                & Q(notifications__created__gt=(timezone.now() - self.cooldown))
            )
            .distinct()
        )

    def perform_action(self, instance: M) -> None:
        self.send(instance)
        if self.action:
            exec(self.action)

    class Meta:
        abstract = True


class NotificationModelAsyncRule(AsyncNotificationMixin, NotificationModelRule):
    class Meta:
        abstract = True


class NotificationModelAsyncReminder(AsyncNotificationMixin, NotificationModelReminder):
    class Meta:
        abstract = True
