import json
from typing import List, Optional, TypeVar

from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q, QuerySet

from df_notifications.decorators import (
    register_reminder_model,
    register_rule_model,
)
from df_notifications.models import (
    AsyncNotificationMixin,
    NotifiableModelMixin,
    NotificationModelReminder,
    NotificationModelRule,
)

M = TypeVar("M", bound=models.Model)


class Post(NotifiableModelMixin):
    title = models.CharField(max_length=255)
    description = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    is_published = models.BooleanField(default=False)

    def json_data(self) -> str:
        return json.dumps(
            {
                "title": self.title,
                "description": self.description,
                "is_published": self.is_published,
            }
        )


class BasePostNotificationRule(NotificationModelRule):
    model = Post
    admin_list_display = [
        "template_prefix",
        "channel",
        "is_published_prev",
        "is_published_next",
    ]
    tracking_fields = ["is_published"]

    is_published_prev = models.BooleanField(default=False, null=True)
    is_published_next = models.BooleanField(default=True)

    def get_users(self, instance: M) -> list:
        return [instance.author]

    @classmethod
    def get_queryset(
        cls, instance: Post, prev: Optional[Post]
    ) -> QuerySet["BasePostNotificationRule"]:
        qs = cls.objects.filter(
            is_published_next=instance.is_published,
        )

        if prev:
            qs = qs.filter(
                Q(is_published_prev__isnull=True)
                | Q(is_published_prev=prev.is_published),
            )

        return qs

    class Meta:
        abstract = True


@register_rule_model
class PostNotificationRule(BasePostNotificationRule):
    pass


@register_rule_model
class AsyncPostNotificationRule(AsyncNotificationMixin, BasePostNotificationRule):
    pass


@register_reminder_model
class PostNotificationReminder(NotificationModelReminder):
    MODIFIED_MODEL_FIELD = "updated"
    model = Post
    admin_list_display = [
        "template_prefix",
        "channel",
        "delay",
        "cooldown",
        "repeat",
        "is_published",
        "action",
    ]

    is_published = models.BooleanField(default=True)

    def get_users(self, instance: M) -> List[User]:
        return [instance.author]
