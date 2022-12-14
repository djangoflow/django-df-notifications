import json
import requests
import logging
from django.core.mail import EmailMultiAlternatives
from django.template import Context
from django.template import Template
from django.utils.translation import gettext_lazy as _
from django_slack import slack_message
from django.utils.functional import cached_property
from firebase_admin.messaging import Message
from firebase_admin.messaging import Notification


def send_notification(template, users, context, attachments):
    from df_notifications.models import NotificationChannels

    classes = {
        NotificationChannels.EMAIL: EmailNotification,
        NotificationChannels.PUSH: PushNotification,
        NotificationChannels.SLACK: SlackNotification,
        NotificationChannels.WEBHOOK: WebhookNotification,
        NotificationChannels.CONSOLE: ConsoleNotification,
    }
    try:
        chnl_class = classes[template.channel]
    except KeyError:
        raise NotImplementedError(f"Please implement handler for '{template.channel}'")

    obj = chnl_class(template, users, context, attachments)
    obj.send()


class NotificationBase:
    def __init__(self, template, users=None, context=None, attachments=None):
        self.template = template
        self.users = users
        self.context = context
        self.attachments = attachments

    def send(self):
        raise NotImplementedError("Please implement send method")

    def create_history_record(self):
        from df_notifications.models import NotificationHistory

        history = NotificationHistory.objects.create(
            channel=self.channel,
            data=self.rendered_data,
            body=self.rendered_body,
            subject=self.rendered_subject,
            body_html=self.rendered_body_html,
        )
        history.users.set(self.users)
        self.history.add(history)
        return history

    @cached_property
    def rendered_body(self):
        return render_string(self.template.body, self.context)

    @cached_property
    def rendered_subject(self):
        return render_string(self.template.subject.splitlines(), self.context)

    @cached_property
    def rendered_data(self):
        return (
            json.loads(render_string(self.template.data, self.context))
            if self.template.data
            else {}
        )

    @cached_property
    def rendered_body_html(self):
        from df_notifications.models import NotificationChannels

        if self.template.channel != NotificationChannels.EMAIL:
            return self.template.body_html

        template_html = ''.join(
            [
                f'{{% extends "{self.base_html_template}"%}}{{% block body %}}',
                f"{self.template.body_html}{{% endblock %}}",
            ]
        )
        return render_string(template_html, self.context)


class EmailNotification(NotificationBase):
    base_html_template = "df_notifications/base_email.html"

    def send(self):
        subject = self.rendered_subject
        body_text = self.rendered_body
        body_html = self.rendered_body_html
        to_emails = [user.email for user in self.users if user.email]

        msg = EmailMultiAlternatives(subject=subject, to=to_emails, body=body_text)
        msg.attach_alternative(body_html, "text/html")
        for attachment in self.attachments:
            msg.attach(**attachment)
        msg.send()


class SlackNotification(NotificationBase):
    base_html_template = "df_notifications/base_slack.html"

    def send(self):
        slack_message(
            self.base_html_template,
            context=self.context,
            attachments=[
                {
                    "text": self.rendered_body,
                    "title": self.rendered_subject,
                }
            ],
        )


class PushNotification(NotificationBase):
    def send(self):
        devices = self.template.get_device_queryset().filter(user__in=self.users)
        devices.send_message(
            Message(
                notification=Notification(
                    title=self.rendered_subject,
                    body=self.rendered_body,
                ),
                data=self.rendered_data,
            ),
        )


class WebhookNotification(NotificationBase):
    def send(self):
        requests.post(
            self.rendered_subject,
            data=self.rendered_body,
            json=self.rendered_data,
        )


class ConsoleNotification(NotificationBase):
    def send(self):
        subject = self.rendered_subject
        logging.info(f"Notification: {subject}")


def render_string(template_string, context):
    return Template(template_string).render(Context(context))
