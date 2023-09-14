from typing import Any, Dict, Iterable

from df_notifications.channels import BaseChannel


class TestAggregator:
    def aggregate_send(self) -> Message:
        """
        Aggregates the message and returns it if send is required otherwise  returns None

        :return:
        """
        return True

class TestChannel(BaseChannel):
    key = "test"
    template_parts = ["msg"]
    title_part = "msg"
    additional_data: list = []
    config_items: list = []
    aggregator = TestAggregator

    def send(self, users: Iterable[Any], context: Dict) -> None:
        print(context)
