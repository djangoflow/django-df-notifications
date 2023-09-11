import json
import logging
from typing import Dict, Iterable

import requests
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone
from django_slack import slack_message
from firebase_admin.firestore import client
from firebase_admin.messaging import Message, Notification
from otp_twilio.models import TwilioSMSDevice


class BaseChannel:
    template_parts = ["subject.txt", "body.txt", "body.html", "data.json"]

    def send(self, users: Iterable, context: Dict[str, str]) -> None:
        pass


class EmailChannel(BaseChannel):
    template_parts = ["subject.txt", "body.txt", "body.html"]

    def send(self, users: Iterable, context: Dict[str, str]) -> None:
        recipients = context.get(
            "recipients", [user.email for user in users if user.email]
        )
        msg = EmailMultiAlternatives(
            subject=context["subject.txt"], to=recipients, body=context["body.txt"]
        )
        msg.attach_alternative(context["body.html"], "text/html")
        for attachment in context.get("attachments", []):
            msg.attach(**attachment)  # type: ignore
        msg.send()


class ConsoleChannel(BaseChannel):
    template_parts = ["subject.txt", "body.txt"]

    def send(self, users: Iterable, context: Dict[str, str]) -> None:
        logging.info(
            f"users: {users}; subject: {context['subject.txt']}; body: {context['body.txt']}"
        )


class FirebasePushChannel(BaseChannel):
    template_parts = ["subject.txt", "body.txt", "data.json"]

    def send(self, users: Iterable, context: Dict[str, str]) -> None:
        try:
            devices = context["devices_queryset"]
        except KeyError:
            from df_notifications.models import UserDevice

            devices = UserDevice.objects.all()

        devices.filter(user__in=users).send_message(
            Message(
                notification=Notification(
                    title=context["subject.txt"],
                    body=context["body.txt"],
                ),
                data=json.loads(context["data.json"]),
            ),
        )


class JSONPostWebhookChannel(BaseChannel):
    template_parts = ["subject.txt", "body.txt", "data.json"]

    def send(self, users: Iterable, context: Dict[str, str]) -> None:
        requests.post(
            context["subject.txt"].strip(),
            data=context["body.txt"].strip(),
            json=json.loads(context["data.json"]),
        )


class SlackChannel(BaseChannel):
    template_parts = ["subject.txt", "body.txt"]

    def send(self, users: Iterable, context: Dict[str, str]) -> None:
        slack_message(
            "df_notifications/base_slack.html",
            context=context,
            attachments=[
                {"title": context["subject.txt"], "text": context["body.txt"]}
            ],
        )


class FirebaseChatChannel(BaseChannel):
    template_parts = ["body.txt"]

    def send(self, users: Iterable, context: Dict[str, str]) -> None:
        db = client()
        db.collection("rooms").document(context["chat_room_id"]).collection(
            "messages"
        ).document().set(
            {
                "text": context["body.txt"],
                "createdAt": timezone.now(),
                "updatedAt": timezone.now(),
                "type": "text",
                "authorId": context.get("chat_author_id", "system"),
            }
        )


class TwilioSMSChannel(BaseChannel):
    template_parts = ["body.txt"]

    def send(self, users: Iterable, context: Dict[str, str]) -> None:
        for device in TwilioSMSDevice.objects.filter(user__in=users):
            device._deliver_token(context["body.txt"])
