from df_notifications.decorators import register_action_model
from df_notifications.models import NotificationAction
from df_notifications.models import NotificationAsyncReminder
from django.contrib.auth.models import User
from django.db import models
from django.db.models import QuerySet
from typing import Optional

import json


class Post(models.Model):
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


@register_action_model
class PostNotificationAction(NotificationAction):
    model = Post

    is_published_prev = models.BooleanField(default=False)
    is_published_next = models.BooleanField(default=True)

    def get_user(self, instance: Post, prev) -> User:
        return instance.author

    @classmethod
    def get_queryset(
        cls, instance: Post, prev: Optional[Post]
    ) -> QuerySet["PostNotificationAction"]:
        return cls.objects.filter(
            is_published_prev=prev.is_published if prev else False,
            is_published_next=instance.is_published,
        )


class PostNotificationReminder(NotificationAsyncReminder):
    model = Post

    def get_user(self, instance: Post, prev) -> User:
        return instance.author
