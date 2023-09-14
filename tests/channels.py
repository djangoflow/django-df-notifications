from typing import Any, Dict, Iterable

from df_notifications.channels import BaseChannel


class TestChannel(BaseChannel):
    template_parts = ["msg"]

    def send(self, users: Iterable[Any], context: Dict) -> None:
        print(context)
