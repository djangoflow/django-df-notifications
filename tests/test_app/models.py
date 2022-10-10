from df_notifications.decorators import register_notification
from df_notifications.models import NotificationTemplate
from django.contrib.auth.models import User
from django.db import models


class Post(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    is_published = models.BooleanField(default=False)


@register_notification(model=Post, slugs=["post_created"])
def post_created(prev: Post, next: Post, template: NotificationTemplate, **kwargs):
    context = {
        "prev": prev,
        "instance": next,
    }
    if prev is None:
        template.send(users=list(User.objects.all()), context=context)


@register_notification(model=Post, slugs=["post_published"])
def post_published_async(
    prev: Post, next: Post, template: NotificationTemplate, **kwargs
):
    context = {"prev_title": prev.title}
    if not (prev and prev.is_published) and next.is_published:
        template.send_async(
            users=list(User.objects.all()), instance=next, context=context
        )
