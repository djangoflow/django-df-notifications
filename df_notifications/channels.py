from django.core.mail import EmailMultiAlternatives
from django.utils import timezone
from django_slack import slack_message
from firebase_admin.firestore import client
from firebase_admin.messaging import Message
from firebase_admin.messaging import Notification
from otp_twilio.models import TwilioSMSDevice
from typing import Dict
from typing import List

import json
import logging
import requests


class BaseChannel:
    """
    Base class for all notification channels. Subclasses must implement the `send` method.
    """
    template_parts: List[str] = ["subject.txt", "body.txt", "body.html", "data.json"]

    def send(self, users: List, context: Dict[str, str]):
        """
        Send a notification to a list of users.

        :param users: A list of user objects to send the notification to.
        :param context: A dictionary containing the message content.
        """
        raise NotImplementedError("send() method is not implemented.")


class EmailChannel(BaseChannel):
    """
    A notification channel that sends email messages.
    """
    template_parts: List[str] = ["subject.txt", "body.txt", "body.html"]

    def send(self, users: List, context: Dict[str, str]):
        """
        Send an email notification to a list of users.

        :param users: A list of user objects to send the email to.
        :param context: A dictionary containing the email content.
        """
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
    """
    A notification channel that logs messages to the console.
    """
    template_parts: List[str] = ["subject.txt", "body.txt"]

    def send(self, users: List, context: Dict[str, str]):
        """
        Log a message to the console.

        :param users: A list of user objects to send the notification to (unused in this implementation).
        :param context: A dictionary containing the message content.
        """
        logging.info(
            f"users: {users}; subject: {context['subject.txt']}; body: {context['body.txt']}"
        )


class FirebasePushChannel(BaseChannel):
    """
    A notification channel that sends push notifications via Firebase Cloud Messaging.
    """
    template_parts: List[str] = ["subject.txt", "body.txt", "data.json"]

    def send(self, users: List, context: Dict[str, str]):
        """
        Send a push notification to a list of users using Firebase Cloud Messaging.

        :param users: A list of user objects to send the notification to.
        :param context: A dictionary containing the notification content.
        """
        try:
            devices = context.get("devices_queryset")
        except KeyError:
            logging.error("devices_queryset not found in context, using default queryset.")
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
    """
    A notification channel that sends JSON payloads via HTTP POST requests.
    """
    template_parts = ["subject.txt", "body.txt", "data.json"]

    def send(self, users, context: Dict[str, str]):
        """
        Send JSON payload via HTTP POST request to the URL specified in the `subject.txt`.

        :param users: list of users to send the notification to
        :param context: dictionary containing the context for rendering the notification templates
        :return: None
        """
        headers = {'Content-Type': 'application/json'}
        requests.post(
            context["subject.txt"].strip(),
            data=context["body.txt"].strip(),
            json=json.loads(context["data.json"]),
            headers=headers,
        )


class SlackChannel(BaseChannel):
    """
    A notification channel that sends messages to Slack.
    """
    template_parts = ["subject.txt", "body.txt"]

    def send(self, users, context: Dict[str, str]):
        slack_message(
            template_name_or_message="df_notifications/base_slack.html",
            context=context,
            attachments=[
                {"title": context["subject.txt"], "text": context["body.txt"]}
            ],
        )


class FirebaseChatChannel(BaseChannel):
    """
    A notification channel that sends messages to Firebase chat.
    """
    template_parts = ["body.txt"]

    def send(self, users, context: Dict[str, str]):
        db = client()
        room_id = context["chat_room_id"]
        message = {
            "text": context["body.txt"],
            "createdAt": timezone.now(),
            "updatedAt": timezone.now(),
            "type": "text",
            "authorId": context.get("chat_author_id", "system"),
        }
        db.collection("rooms").document(room_id).collection("messages").document().set(message)


class TwilioSMSChannel(BaseChannel):
    """
    A notification channel that sends SMS messages via Twilio.
    """
    template_parts = ["body.txt"]

    def send(self, users, context: Dict[str, str]):
        # Fetch all user devices in a single query
        user_devices = TwilioSMSDevice.objects.filter(user__in=users).select_related('user')
        
        # Loop through the user devices to send SMS messages
        for device in user_devices:
            device._deliver_token(context["body.txt"])
