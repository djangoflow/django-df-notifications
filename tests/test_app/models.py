from df_notifications.decorators import register_reminder_model
from df_notifications.decorators import register_rule_model
from df_notifications.models import NotifiableModelMixin
from df_notifications.models import NotificationModelReminder
from df_notifications.models import NotificationModelRule
from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q
from django.db.models import QuerySet
from typing import List
from typing import Optional

import json


class Post(NotifiableModelMixin):
    title = models.CharField(max_length=255)
    description = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    is_published = models.BooleanField(default=False)

    def json_data(self):
        return json.dumps(
            {
                "title": self.title,
                "description": self.description,
                "is_published": self.is_published,
            }
        )


@register_rule_model
class PostNotificationRule(NotificationModelRule):
    model = Post
    admin_list_display = [
        "template",
        "channel",
        "is_published_prev",
        "is_published_next",
    ]
    tracking_fields = ["is_published"]

    is_published_prev = models.BooleanField(default=False, null=True)
    is_published_next = models.BooleanField(default=True)

    def get_users(self, instance: Post) -> List[User]:
        return [instance.author]

    @classmethod
    def get_queryset(
        cls, instance: Post, prev: Optional[Post]
    ) -> QuerySet["PostNotificationRule"]:
        qs = cls.objects.filter(
            is_published_next=instance.is_published,
        )

        if prev:
            qs = qs.filter(
                Q(is_published_prev__isnull=True)
                | Q(is_published_prev=prev.is_published),
            )

        return qs


@register_reminder_model
class PostNotificationReminder(NotificationModelReminder):
    MODIFIED_MODEL_FIELD = "updated"
    model = Post
    admin_list_display = [
        "template",
        "channel",
        "delay",
        "cooldown",
        "repeat",
        "is_published",
        "action",
    ]

    is_published = models.BooleanField(default=True)

    def get_users(self, instance: Post) -> List[User]:
        return [instance.author]
