# type: ignore
import json
from typing import Any
from unittest.mock import patch

import pytest
from celery import Celery
from dbtemplates.models import Template
from django.contrib.auth import get_user_model
from django.utils import timezone
from pytest_mock import MockerFixture

from df_notifications.channels import JSONPostWebhookChannel
from df_notifications.models import (
    CustomPushMessage,
    NotificationHistory,
    send_notification,
)
from df_notifications.tasks import send_notification_task
from tests.test_app.models import (
    AsyncPostNotificationRule,
    Post,
    PostNotificationReminder,
    PostNotificationRule,
)

User = get_user_model()

pytestmark = [pytest.mark.django_db]


def setup_templates():
    Template.objects.create(
        name="df_notifications/posts/published/subject.txt",
        content="New post: {{ instance.title }}",
    )
    Template.objects.create(
        name="df_notifications/posts/published/body.txt",
        content="{{ instance.description }}",
    )


def setup_published_notification():
    action = PostNotificationRule(
        is_published_next=True,
        is_published_prev=False,
        channel="console",
        template_prefix="df_notifications/posts/published/",
    )
    action.save()


def setup_async_published_notification():
    action = AsyncPostNotificationRule(
        is_published_next=True,
        is_published_prev=False,
        channel="console",
        template_prefix="df_notifications/posts/published/",
    )
    action.save()


def test_post_published_notification_created():
    setup_published_notification()
    setup_templates()

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
    assert notification.content["subject.txt"] == f"New post: {post.title}"
    assert notification.content["body.txt"] == post.description


@pytest.mark.django_db(transaction=True)
@patch("df_notifications.models.transaction.on_commit", new=lambda fn: fn())
def test_post_published_notification_created_async(
    mocker: MockerFixture, celery_app: Celery, celery_worker: Any
) -> None:
    setup_async_published_notification()
    setup_templates()

    spy = mocker.spy(celery_app, "send_task")
    user = User.objects.create(
        email="test@test.com",
    )
    Post.objects.create(
        title="Title 1",
        description="Content 1",
        is_published=True,
        author=user,
    )

    # No notifications should be created yet
    notifications = NotificationHistory.objects.all()
    assert len(notifications) == 0
    # And async task was scheduled
    assert spy.call_count == 1

    # Simulate task execution
    spy.spy_return.get(timeout=5)

    notifications = NotificationHistory.objects.all()
    assert len(notifications) == 1


def test_post_non_published_notification_not_created():
    setup_published_notification()
    setup_templates()

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
    setup_templates()

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
    setup_templates()
    reminder = PostNotificationReminder(
        is_published=True,
        channel="console",
        template_prefix="df_notifications/posts/published/",
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
    setup_templates()
    reminder = PostNotificationReminder(
        is_published=True,
        channel="console",
        template_prefix="df_notifications/posts/published/",
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
    setup_templates()
    reminder = PostNotificationReminder(
        is_published=True,
        channel="console",
        template_prefix="df_notifications/posts/published/",
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


def test_send_notification_without_model():
    Template.objects.create(
        name="df_notifications/posts/published/subject.txt",
        content="New post: {{ title }}",
    )
    Template.objects.create(
        name="df_notifications/posts/published/body.txt",
        content="{{ description }}",
    )
    user = User.objects.create(
        email="test@test.com",
    )

    notification = send_notification(
        users=[user],
        channel="console",
        template_prefixes="df_notifications/posts/published/",
        context={
            "title": "title 123",
            "description": "description 456",
        },
    )
    assert notification.content["subject.txt"] == "New post: title 123"
    assert notification.content["body.txt"] == "description 456"


def test_send_notification_async_without_model():
    user = User.objects.create(
        email="test@test.com",
    )
    Template.objects.create(
        name="df_notifications/posts/published/subject.txt",
        content="New post: {{ title }}",
    )
    Template.objects.create(
        name="df_notifications/posts/published/body.txt",
        content="{{ description }}",
    )

    send_notification_task(
        [user.id],
        "console",
        "df_notifications/posts/published/",
        {
            "title": "title 123",
            "description": "description 456",
        },
    )
    notifications = NotificationHistory.objects.all()
    assert len(notifications) == 1
    notification = notifications[0]
    assert notification.content["subject.txt"] == "New post: title 123"
    assert notification.content["body.txt"] == "description 456"


def test_reminder_performs_action():
    setup_templates()
    reminder = PostNotificationReminder(
        is_published=True,
        channel="console",
        template_prefix="df_notifications/posts/published/",
        action="instance.title='new title'; instance.save()",
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
    post.refresh_from_db()
    assert post.title == "new title"


def test_rule_not_invoked_on_non_tracked_field_change():
    setup_templates()
    action = PostNotificationRule(
        is_published_next=True,
        is_published_prev=None,
        channel="console",
        template_prefix="df_notifications/posts/published/",
    )
    action.save()

    user = User.objects.create(
        email="test@test.com",
    )
    post = Post.objects.create(
        title="Title 1",
        description="Content 1",
        is_published=True,
        author=user,
    )
    assert len(NotificationHistory.objects.all()) == 1
    post.title = "Title 2"
    post.save()
    assert len(NotificationHistory.objects.all()) == 1
    post.is_published = False
    post.save()
    assert len(NotificationHistory.objects.all()) == 1
    post.is_published = True
    post.save()
    assert len(NotificationHistory.objects.all()) == 2


def test_default_templates_rendered_if_no_template_exists():
    Template.objects.create(
        name="test_app/df_notifications/posts/subject.txt",
        content="New post: {{ instance.title }}",
    )
    Template.objects.create(
        name="test_app/df_notifications/posts/body.txt",
        content="{{ instance.description }}",
    )
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
    assert notification.content["subject.txt"] == f"New post: {post.title}"
    assert notification.content["body.txt"] == post.description


@patch("df_notifications.channels.requests.post")
def test_json_post_webhook_channel(mock_requests_post):
    channel = JSONPostWebhookChannel()
    users = []
    context = {
        "subject.txt": "https://hooks.example.com/hook_endpoint  ",
        "body.txt": " Web hook Test",
        "data.json": '{"notification": "Testing webhook"}',
    }

    channel.send(users, context)

    assert mock_requests_post.called is True
    mock_requests_post.assert_called_once_with(
        "https://hooks.example.com/hook_endpoint",
        data="Web hook Test",
        json={"notification": "Testing webhook"},
    )


@patch("df_notifications.channels.requests.post")
def test_json_post_webhook_channel_with_invalid_context(mock_requests_post):
    """
    Test that an exception is raised,
    when seding wrong context data for JSONPostWebhookChannel
    """
    channel = JSONPostWebhookChannel()
    users = []
    context = {
        "subject.txt": "https://hooks.example.com/hook_endpoint",
        "data.json": '{"notification": "Testing webhook"}',
    }

    with pytest.raises(KeyError):
        channel.send(users, context)

    assert mock_requests_post.called is False


def test_send_custom_push_message() -> None:
    user = User.objects.create(
        email="test@test.com",
    )
    message: CustomPushMessage = CustomPushMessage.objects.create(
        title="Custom title",
        body="Custom body",
        action_url="/custom-url",
        image="/custom-image.png",
    )
    message.audience.set([user])

    message.send()

    assert message.sent is not None
    assert len(NotificationHistory.objects.all()) == 1
    notification = NotificationHistory.objects.all()[0]
    assert notification.content["subject.txt"] == "Custom title"
    assert notification.content["body.txt"] == "Custom body"
    assert json.loads(notification.content["data.json"]) == {
        "action_url": "/custom-url",
        "image": "/custom-image.png",
    }
