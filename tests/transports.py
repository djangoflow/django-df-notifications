from df_notifications.transports import BaseTransport
from typing import Dict


class TestTransport(BaseTransport):
    key = "test"
    template_parts = ["msg"]
    title_part = "msg"
    additional_data = []
    config_items = []

    def send(self, user, data: Dict[str, str], config_items: Dict[str, str]):
        print(data["msg"])
