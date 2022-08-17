from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.db import models
from django.template import Context
from django.template import Template
from django.utils.translation import gettext_lazy as _
from django_slack import slack_message
from fcm_django.models import AbstractFCMDevice
from firebase_admin.messaging import Message
from firebase_admin.messaging import Notification

import json
import logging
import requests


User = get_user_model()


class NotificationChannels(models.IntegerChoices):
    PUSH = 100, "push"
    EMAIL = 200, "email"
    SMS = 300, "sms"
    CALL = 400, "call"
    CHAT = 500, "chat"
    SLACK = 600, "slack"
    WEBHOOK = 700, "webhook"

    CONSOLE = 1_000_000, "console"


class AbstractNotificationBase(models.Model):
    channel = models.PositiveSmallIntegerField(choices=NotificationChannels.choices)
    subject = models.CharField(max_length=1024)
    body = models.TextField(null=True, blank=True)
    body_html = models.TextField(null=True, blank=True)
    data = models.TextField(null=True, blank=True)

    class Meta:
        abstract = True


class NotificationHistory(AbstractNotificationBase):
    timestamp = models.DateTimeField(auto_now=True)
    users = models.ManyToManyField(
        User, help_text="Users this notification was sent to"
    )

    class Meta:
        verbose_name_plural = "Notification History"


class AbstractNotification(AbstractNotificationBase):
    history = models.ManyToManyField(NotificationHistory, blank=True)
    email_template = "df_notifications/base_email.html"
    slack_template = "df_notifications/base_slack.html"

    def get_device_queryset(self):
        return UserDevice.objects.all()

    def send(
        self,
        users=None,
        context=None,
        attachments=None,
    ):
        users = users or []
        attachments = attachments or []
        """
        :param users: users to be notified
        :param context: context
        :param attachments: attachments for email
        :return: history object
        """

        _context = Context(context)

        subject = Template("".join(self.subject.splitlines())).render(_context)

        data = json.loads(Template(self.data).render(_context)) if self.data else {}
        body = Template(self.body).render(_context)

        body_html = Template(
            (
                f'{{% extends "{self.email_template}"%}}{{% block body %}}'
                f"{self.body_html}{{% endblock %}}"
            )
            if self.channel == NotificationChannels.EMAIL
            else self.body_html
        ).render(_context)

        if self.channel == NotificationChannels.EMAIL:
            to_emails = [user.email for user in users if user.email]
            msg = EmailMultiAlternatives(subject=subject, to=to_emails, body=body)
            msg.attach_alternative(body_html, "text/html")
            for attachment in attachments:
                msg.attach(**attachment)
            msg.send()
        elif self.channel == NotificationChannels.PUSH:
            devices = self.get_device_queryset().filter(
                user__in=users,
            )
            devices.send_message(
                Message(
                    notification=Notification(
                        title=subject,
                        body=body,
                    ),
                    data=data,
                ),
            )
        elif self.channel == NotificationChannels.SLACK:
            x = slack_message(
                self.slack_template,
                context=context,
                attachments=[{"text": body, "title": subject}],
            )
            print(x)
        elif self.channel == NotificationChannels.WEBHOOK:
            requests.post(subject, data=body, json=data)
        elif self.channel == NotificationChannels.CONSOLE:
            logging.info(f"Notification: {subject}")
        else:
            raise NotImplementedError

        history = NotificationHistory.objects.create(
            channel=self.channel,
            data=data,
            body=body,
            subject=subject,
            body_html=body_html,
        )
        history.users.set(users)
        self.history.add(history)
        return history

    def save(self, *args, **kwargs):
        self.data = json.dumps(json.loads(self.data))
        super().save(*args, **kwargs)

    class Meta:
        abstract = True


class UserDevice(AbstractFCMDevice):
    class Meta:
        verbose_name = _("User device")
        verbose_name_plural = _("User devices")
