from dbtemplates.models import Template
from df_notifications.models import NotificationHistory
from django.contrib.auth import get_user_model
from tests.test_app.models import Post
from tests.test_app.models import PostNotificationAction

import pytest


User = get_user_model()

pytestmark = [pytest.mark.django_db]


def setup_published_notification():
    action = PostNotificationAction(
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
