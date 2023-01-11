from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from firebase_admin.messaging import Message
from firebase_admin.messaging import Notification
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

import json
import logging
import requests


User = get_user_model()


class BaseTransport:
    key: str
    template_parts: List[str]
    title_part: Optional[str] = None
    additional_data: List[str] = []
    config_items: List[str] = []

    def send(self, user: User, data: Dict[str, str], config_items: Dict[str, str]):
        pass

    def get_title_part(self):
        return self.title_part or self.template_parts[0]


class EmailTransport(BaseTransport):
    key = "email"
    template_parts = ["subject", "body", "body_html"]
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

    def send(self, user: User, data: Dict[str, Any], config_items: Dict[str, str]):
        logging.info(f"user: {user}; title: {data['title']}; body: {data['body']}")


class FirebasePushTransport(BaseTransport):
    key = "firebase_push"
    template_parts = ["title", "body", "data"]

    def send(self, user: User, data: Dict[str, str], config_items: Dict[str, str]):
        user.fcmdevice_set.send_message(
            Message(
                notification=Notification(
                    title=data["title"],
                    body=data["body"],
                ),
                data=json.loads(data["data"]),
            ),
        )


class JSONPostWebhookTransport(BaseTransport):
    key = "webhook"
    template_parts = ["title", "json"]
    config_items = ["url"]

    def send(self, user: User, data: Dict[str, str], config_items: Dict[str, str]):
        requests.post(config_items["url"], json=json.loads(data["json"]))
