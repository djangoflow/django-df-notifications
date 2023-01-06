from django.contrib import admin
from tests.test_app.models import Post
from tests.test_app.models import PostNotificationAction


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "is_published",
    )


@admin.register(PostNotificationAction)
class PostNotificationActionAdmin(admin.ModelAdmin):
    list_display = ("is_published_prev", "is_published_next", "template")
