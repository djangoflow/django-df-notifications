from contextlib import contextmanager
from typing import Any, Dict, Generator, Type

from django.contrib import admin
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import QuerySet
from django.db.models.signals import post_save, pre_save
from django.http import HttpRequest
from django.template import TemplateDoesNotExist
from django.template.loader import get_template
from django.urls import reverse
from django.utils.safestring import mark_safe
from import_export.admin import ImportExportMixin
from import_export.resources import ModelResource

from df_notifications.models import M, NotificationModelMixin, get_channel_instance


@contextmanager
def disable_notification_signal(sender: Type[M]) -> Generator[None, None, None]:
    """
    Temporarily disconnects a signal for a given sender.
    """
    if sender not in notification_receivers:
        raise ValueError(f"Signal not found for '{sender}'")

    receiver = notification_receivers[sender]

    post_save.disconnect(
        sender=sender, receiver=receiver, dispatch_uid=signal_dispatch_uid(sender)
    )
    try:
        yield
    finally:
        post_save.connect(
            sender=sender,
            receiver=receiver,
            weak=False,
            dispatch_uid=signal_dispatch_uid(sender),
        )


def save_previous_instance(
    sender: Type[M], instance: Type[M], **kwargs: Dict[Any, Any]
) -> None:
    if instance.pk:
        try:
            instance._pre_save_instance = sender.objects.get(pk=instance.pk)
        except ObjectDoesNotExist:
            instance._pre_save_instance = None
    else:
        instance._pre_save_instance = None


def create_proxy_model(model_class: Type[object]) -> type:
    return type(
        model_class.__name__,
        (model_class,),
        {
            "__module__": "df_notifications",
            "Meta": type("Meta", (object,), {"proxy": True, "auto_created": True}),
        },
    )


def register_notification_model_admin(model_class: Type[object]) -> None:
    ProxyModel = create_proxy_model(model_class)

    @admin.register(ProxyModel)
    class AdminProxyModel(ImportExportMixin, admin.ModelAdmin):
        def get_list_display(self, request: HttpRequest) -> tuple:
            return (
                *model_class.admin_list_display,
                "content",
            )

        def get_resource_classes(self) -> list:
            class ProxyModelResource(ModelResource):
                class Meta:
                    model = model_class
                    skip_unchanged = True
                    report_skipped = False

            return [ProxyModelResource]

        def content(self, obj: M) -> str:
            url = reverse("admin:dbtemplates_template_changelist")
            return mark_safe(f'<a href="{url}?q={obj.template_prefix}">Change</a>')

        @admin.action(
            description="Initialize DB Templates for notifications (override current content)"
        )
        def populate(self, request: HttpRequest, qs: QuerySet) -> None:
            from dbtemplates.models import Template

            for item in qs:
                assert isinstance(item, NotificationModelMixin)

                for part in get_channel_instance(item.channel).template_parts:
                    names = [
                        f"{item.template_prefix}{item.channel}__{part}",
                        f"{item.template_prefix}{part}",
                    ]
                    for name in names:
                        try:
                            with transaction.atomic():
                                Template.objects.filter(name=name).delete()
                                template = get_template(name)
                                with open(template.origin.name, "r") as f:
                                    Template.objects.create(name=name, content=f.read())
                        except TemplateDoesNotExist:
                            pass

        actions = [populate]


notification_receivers = {}


def signal_dispatch_uid(model_class: Type[M]) -> str:
    return f"notification_receiver_{model_class.__name__}"


def register_rule_model(rule_class: Type[M]) -> Type[M]:
    pre_save.connect(
        save_previous_instance,
        rule_class.model,
        weak=False,
        dispatch_uid="save_previous_instance",
    )

    def apply_action(
        sender: Type[M], instance: Type[M], **kwargs: Dict[Any, Any]
    ) -> None:
        rule_class.invoke(instance)

    notification_receivers[rule_class.model] = apply_action
    post_save.connect(
        apply_action,
        rule_class.model,
        weak=False,
        dispatch_uid=signal_dispatch_uid(rule_class.model),
    )

    register_notification_model_admin(rule_class)

    return rule_class


def register_reminder_model(reminder_class: Type[object]) -> Type[object]:
    register_notification_model_admin(reminder_class)
    return reminder_class
