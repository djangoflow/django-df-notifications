from django.contrib import admin
from tests.test_app.models import Post
from tests.test_app.models import PostNotificationReminder
from tests.test_app.models import PostNotificationRule


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "is_published",
    )


@admin.register(PostNotificationRule)
class PostNotificationRuleAdmin(admin.ModelAdmin):
    list_display = (
        "template_prefix",
        "channel",
        "is_published_prev",
        "is_published_next",
    )


@admin.register(PostNotificationReminder)
class PostNotificationReminderAdmin(admin.ModelAdmin):
    list_display = (
        "template_prefix",
        "channel",
    )
