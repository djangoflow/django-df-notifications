from json import JSONDecodeError
from unittest import TestCase
from unittest.mock import patch
from dbtemplates.models import Template
from df_notifications.channels import JSONPostWebhookChannel
from df_notifications.models import NotificationHistory
from df_notifications.tasks import send_notification_async
from df_notifications.utils import send_notification
from django.contrib.auth import get_user_model
from django.utils import timezone
from tests.test_app.models import Post
from tests.test_app.models import PostNotificationReminder
from tests.test_app.models import PostNotificationRule

import pytest


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

    send_notification_async(
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


class TestJSONPostWebhookChannel(TestCase):
    def test_throws_type_error_if_missing_context(self):
        channel = JSONPostWebhookChannel()
        with self.assertRaises(TypeError):
            channel.send(None, None)

    def test_throws_key_error_if_missing_data_json(self):
        channel = JSONPostWebhookChannel()
        context = {
            "subject.txt": "https://example.com/webhook",
            "body.txt": "content"
        }
        with self.assertRaises(KeyError):
            channel.send(None, context)

    def test_throws_key_error_if_missing_body_txt(self):
        channel = JSONPostWebhookChannel()
        context = {
            "subject.txt": "https://example.com/webhook",
            "data.json": '{"type": "new"}'
        }
        with self.assertRaises(KeyError):
            channel.send(None, context)

    def test_throws_key_error_if_missing_subject(self):
        channel = JSONPostWebhookChannel()
        context = {
            "body.txt": "content",
            "data.json": '{"type": "new"}'
        }
        with self.assertRaises(KeyError):
            channel.send(None, context)

    def test_throws_json_decode_error_invalid_data_json(self):
        channel = JSONPostWebhookChannel()
        context = {
            "subject.txt": "https://example.com/webhook",
            "body.txt": "content",
            "data.json": '{"type": "new"'
        }
        with self.assertRaises(JSONDecodeError):
            channel.send(None, context)

    @patch("df_notifications.channels.requests.post")
    def test_post_sent(self, mock_request):
        channel = JSONPostWebhookChannel()
        context = {
            "subject.txt": "https://example.com/webhook ",
            "body.txt": " content ",
            "data.json": '{"type": "new"}'
        }
        channel.send(None, context)

        mock_request.assert_called_once_with(
            "https://example.com/webhook",
            data="content",
            json={"type": "new"}
        )
