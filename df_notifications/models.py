from datetime import timedelta
from df_notifications.fields import NoMigrationsChoicesField
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db import transaction
from django.db.models import Count
from django.db.models import Q
from django.db.models import QuerySet
from django.utils import timezone
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
    user = models.ForeignKey(
        User,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_query_name=_("fcmdevice"),
    )

    class Meta:
        verbose_name = _("User device")
        verbose_name_plural = _("User devices")


# -------- Notifications ----------


class NotificationHistoryQuerySet(models.QuerySet):
    def for_instance(self, instance: M):
        return self.filter(
            instance_id=instance.pk,
            content_type=ContentType.objects.get_for_model(instance).id,
        )


class NotificationHistory(models.Model):
    id = models.BigAutoField(primary_key=True)
    users = models.ManyToManyField(User, blank=True)
    created = models.DateTimeField(auto_now_add=True, db_index=True)
    channel = NoMigrationsChoicesField(
        max_length=255,
        choices=[(key, key) for key in settings.DF_NOTIFICATIONS["CHANNELS"]],
    )
    template = models.CharField(max_length=255)
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
            models.Index(fields=["template", "created"]),
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
    def is_field_changed(cls, instance: M, prev: Optional[M]):
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

    def perform_action(self, instance: M):
        pass

    @classmethod
    def invoke(cls, instance: M):
        prev = getattr(instance, "_pre_save_instance", None)

        if not cls.is_field_changed(instance, prev):
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


class NotificationModelMixin(models.Model):
    model: Type[M]
    admin_list_display: List[str] = ["channel", "template"]

    history = models.ManyToManyField(NotificationHistory, blank=True, editable=False)
    channel = NoMigrationsChoicesField(
        max_length=255,
        choices=[(key, key) for key in settings.DF_NOTIFICATIONS["CHANNELS"]],
    )
    template = models.CharField(max_length=255)
    context = models.JSONField(default=dict, blank=True)

    def get_users(self, instance: M) -> List[User]:
        return []

    def get_context(self, instance: M) -> Dict[str, Any]:
        return {
            **self.context,
            "instance": instance,
        }

    def send(self, instance: M):
        from .utils import send_notification

        notification = send_notification(
            self.get_users(instance),
            self.channel,
            self.template,
            self.get_context(instance),
        )
        self.history.add(notification)

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

    def perform_action(self, instance: M):
        self.send(instance)
        if self.action:
            exec(self.action)

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
