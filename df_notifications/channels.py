from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from firebase_admin.messaging import Message
from firebase_admin.messaging import Notification
from typing import Dict
from typing import List

import json
import logging
import requests


User = get_user_model()


class BaseChannel:
    template_parts: List[str]

    def send(self, users: List[User], context: Dict[str, str]):
        pass


class EmailChannel(BaseChannel):
    template_parts = ["subject.txt", "body.txt", "body.html"]

    def send(self, users: List[User], context: Dict[str, str]):
        recipients = context.get(
            "recipients", [user.email for user in users if user.email]
        )
        msg = EmailMultiAlternatives(
            subject=context["subject.txt"], to=recipients, body=context["body.txt"]
        )
        msg.attach_alternative(context["body.html"], "text/html")
        for attachment in context.get("attachments", []):
            msg.attach(**attachment)
        msg.send()


class ConsoleChannel(BaseChannel):
    template_parts = ["title.txt", "body.txt"]

    def send(self, users: List[User], context: Dict[str, str]):
        logging.info(
            f"users: {users}; title: {context['title.txt']}; body: {context['body.txt']}"
        )


class FirebasePushChannel(BaseChannel):
    template_parts = ["title.txt", "body.txt", "data.json"]

    def send(self, users: List[User], context: Dict[str, str]):
        from df_notifications.models import UserDevice

        devices = UserDevice.objects.filter(user__in=users)
        devices.send_message(
            Message(
                notification=Notification(
                    title=context["title.txt"],
                    body=context["body.txt"],
                ),
                data=json.loads(context["data.json"]),
            ),
        )


class JSONPostWebhookChannel(BaseChannel):
    key = "webhook"
    template_parts = ["data.json"]

    def send(self, users: List[User], context: Dict[str, str]):
        requests.post(context["url"], json=json.loads(context["data.json"]))
