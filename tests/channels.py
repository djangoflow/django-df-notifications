from typing import Any, Dict, Iterable

from df_notifications.channels import BaseChannel


class TestChannel(BaseChannel):
    key = "test"
    template_parts = ["msg"]
    title_part = "msg"
    additional_data: list = []
    config_items: list = []

    def send(self, users: Iterable[Any], context: Dict) -> None:
        print(context)
