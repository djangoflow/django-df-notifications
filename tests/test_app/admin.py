from django.contrib import admin
from tests.test_app.models import Post
from tests.test_app.models import PostNotificationAction
from tests.test_app.models import PostNotificationReminder


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "is_published",
    )


@admin.register(PostNotificationAction)
class PostNotificationActionAdmin(admin.ModelAdmin):
    list_display = ("template", "is_published_prev", "is_published_next")


@admin.register(PostNotificationReminder)
class PostNotificationReminderAdmin(admin.ModelAdmin):
    list_display = ("template",)
