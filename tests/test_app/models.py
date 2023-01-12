from df_notifications.decorators import register_rule_model
from df_notifications.models import NotificationModelAsyncReminder
from df_notifications.models import NotificationModelRule
from django.contrib.auth.models import User
from django.db import models
from django.db.models import QuerySet
from typing import List
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


@register_rule_model
class PostNotificationRule(NotificationModelRule):
    model = Post

    is_published_prev = models.BooleanField(default=False)
    is_published_next = models.BooleanField(default=True)

    def get_users(self, instance: Post) -> List[User]:
        return [instance.author]

    @classmethod
    def get_queryset(
        cls, instance: Post, prev: Optional[Post]
    ) -> QuerySet["PostNotificationRule"]:
        return cls.objects.filter(
            is_published_prev=prev.is_published if prev else False,
            is_published_next=instance.is_published,
        )


class PostNotificationReminder(NotificationModelAsyncReminder):
    model = Post

    def get_users(self, instance: Post) -> List[User]:
        return [instance.author]
