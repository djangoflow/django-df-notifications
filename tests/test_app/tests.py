from dbtemplates.models import Template
from df_notifications.models import NotificationHistory
from django.contrib.auth import get_user_model
from django.utils import timezone
from tests.test_app.models import Post
from tests.test_app.models import PostNotificationReminder
from tests.test_app.models import PostNotificationRule

import pytest


User = get_user_model()

pytestmark = [pytest.mark.django_db]


def setup_published_notification():
    action = PostNotificationRule(
        is_published_next=True,
        is_published_prev=False,
        channel="console",
        template_prefix="df_notifications/posts/published",
    )
    action.save()
    Template.objects.create(
        name=f"{action.template_prefix}_title.txt",
        content="New post: {{ instance.title }}",
    )
    Template.objects.create(
        name=f"{action.template_prefix}_console_body.txt",
        content="{{ instance.description }}",
    )


def test_post_published_notification_created():
    setup_published_notification()

    user = User.objects.create(
        email="test@test.com",
    )
    post = Post.objects.create(
        title="Title 1",
        description="Content 1",
        is_published=True,
        author=user,
    )
    notifications = NotificationHistory.objects.all()
    assert len(notifications) == 1
    notification = notifications[0]
    assert notification.content["title.txt"] == f"New post: {post.title}"
    assert notification.content["body.txt"] == post.description


def test_post_non_published_notification_not_created():
    setup_published_notification()

    user = User.objects.create(
        email="test@test.com",
    )
    Post.objects.create(
        title="Title 1",
        description="Content 1",
        is_published=False,
        author=user,
    )
    assert not NotificationHistory.objects.exists()


def test_notification_history_queryset_for_instance_filtering():
    setup_published_notification()

    user = User.objects.create(
        email="test@test.com",
    )
    post1 = Post.objects.create(
        title="Title 1",
        description="Content 1",
        is_published=True,
        author=user,
    )
    Post.objects.create(
        title="Title 2",
        description="Content 2",
        is_published=True,
        author=user,
    )

    notifications = NotificationHistory.objects.for_instance(post1)
    assert len(notifications) == 1
    notification = notifications[0]
    assert notification.content["body.txt"] == post1.description


def test_reminder_queryset_is_valid():
    reminder = PostNotificationReminder(
        is_published=True,
        channel="console",
        template_prefix="df_notifications/posts/published",
    )
    reminder.save()

    user = User.objects.create(
        email="test@test.com",
    )
    post = Post.objects.create(
        title="Title 1",
        description="Content 1",
        is_published=True,
        author=user,
    )

    posts = list(reminder.get_model_queryset())
    assert len(posts) == 1
    assert posts[0] == post


def test_reminder_respect_delay():
    reminder = PostNotificationReminder(
        is_published=True,
        channel="console",
        template_prefix="df_notifications/posts/published",
        delay=timezone.timedelta(seconds=60),
    )
    reminder.save()

    user = User.objects.create(
        email="test@test.com",
    )
    Post.objects.create(
        title="Title 1",
        description="Content 1",
        is_published=True,
        author=user,
    )
    assert not reminder.get_model_queryset().exists()

    Post.objects.update(updated=timezone.now() - timezone.timedelta(seconds=120))
    assert reminder.get_model_queryset().exists()


def test_reminder_performs_retries():
    reminder = PostNotificationReminder(
        is_published=True,
        channel="console",
        template_prefix="df_notifications/posts/published",
        repeat=2,
        cooldown=timezone.timedelta(seconds=0),
        delay=timezone.timedelta(seconds=0),
    )
    reminder.save()

    user = User.objects.create(
        email="test@test.com",
    )
    post = Post.objects.create(
        title="Title 1",
        description="Content 1",
        is_published=True,
        author=user,
    )

    PostNotificationReminder.invoke()
    assert post.notifications.count() == 1
    PostNotificationReminder.invoke()
    assert post.notifications.count() == 2
    PostNotificationReminder.invoke()
    assert post.notifications.count() == 2
