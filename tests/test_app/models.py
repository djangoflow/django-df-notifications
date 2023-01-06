from df_notifications.decorators import register_action_model
from df_notifications.models import NotificationAction
from df_notifications.models import NotificationAsyncReminder
from django.contrib.auth.models import User
from django.db import models
from django.db.models import QuerySet
from typing import Optional


class Post(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    is_published = models.BooleanField(default=False)


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


# @register_notification(model=Post, slugs=["post_created"])
# def post_created(prev: Post, next: Post, template: NotificationTemplate, **kwargs):
#     context = {
#         "prev": prev,
#         "instance": next,
#     }
#     if prev is None:
#         template.send(users=list(User.objects.all()), context=context)
#
#
# @register_notification(model=Post, slugs=["post_published"])
# def post_published_async(
#     prev: Post, next: Post, template: NotificationTemplate, **kwargs
# ):
#     context = {"prev_title": prev.title}
#     if not (prev and prev.is_published) and next.is_published:
#         template.send_async(
#             users=list(User.objects.all()), instance=next, context=context
#         )
