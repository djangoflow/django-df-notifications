from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from typing import Any
from typing import Dict
from typing import List

import logging


User = get_user_model()


class BaseTransport:
    key: str
    template_parts: List[str]
    title_part: str
    additional_data: List[str]
    config_items: List[str]

    def send(self, user: User, data: Dict[str, str], config_items: Dict[str, str]):
        pass


class EmailTransport(BaseTransport):
    key = "email"
    template_parts = ["subject", "body", "body_html"]
    title_part = "subject"
    additional_data = ["attachments"]
    config_items = ["recipient"]

    def send(self, user: User, data: Dict[str, Any], config_items: Dict[str, str]):
        recipient = config_items.get("recipient", user.email)
        msg = EmailMultiAlternatives(
            subject=data["subject"], to=[recipient], body=data["body"]
        )
        msg.attach_alternative(data["body_html"], "text/html")
        for attachment in data.get("attachments", []):
            msg.attach(**attachment)
        msg.send()


class ConsoleTransport(BaseTransport):
    key = "console"
    template_parts = ["title", "body"]
    title_part = "title"
    additional_data = []
    config_items = []

    def send(self, user: User, data: Dict[str, Any], config_items: Dict[str, str]):
        logging.info(f"user: {user}; title: {data['title']}; body: {data['body']}")
