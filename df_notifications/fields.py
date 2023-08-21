from typing import Any

from django.db.models import TextField


class NoMigrationsChoicesField(TextField):
    def deconstruct(self) -> Any:
        name, path, args, kwargs = super().deconstruct()
        # Ignore choice changes when generating migrations
        kwargs.pop("choices", None)
        return name, path, args, kwargs
