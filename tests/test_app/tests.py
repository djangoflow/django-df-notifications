from df_notifications.models import NotificationChannel
from df_notifications.models import NotificationHistory
from df_notifications.models import NotificationTemplate
from django.contrib.auth import get_user_model
from tests.test_app.models import Post
from tests.test_app.models import PostNotificationAction

import pytest


User = get_user_model()

pytestmark = [pytest.mark.django_db]


def setup_published_notification():
    channel = NotificationChannel.objects.create(
        transport_class="df_notifications.transports.ConsoleTransport"
    )
    template = NotificationTemplate.objects.create(
        channel=channel,
        name="post_published_console",
    )
    PostNotificationAction.objects.create(
        is_published_prev=False,
        is_published_next=True,
        template=template,
    )
    title_part = template.parts.get(name="title")
    title_part.content = "New post: {{ instance.title }}"
    title_part.save()


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
    notification = NotificationHistory.objects.get(user=user)
    assert notification.title == f"New post: {post.title}"


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
    assert not NotificationHistory.objects.filter(user=user).exists()
