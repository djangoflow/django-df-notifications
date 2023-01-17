from django.contrib import admin
from tests.test_app.models import Post


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "is_published",
    )
