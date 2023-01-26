from df_notifications.models import NotificationModelMixin
from df_notifications.utils import get_channel_instance
from django.contrib import admin
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_save
from django.db.models.signals import pre_save
from django.urls import reverse
from django.utils.safestring import mark_safe
from import_export.admin import ImportExportMixin
from import_export.resources import ModelResource


def save_previous_instance(sender, instance, **kwargs):
    if instance.pk:
        instance._pre_save_instance = sender.objects.get(pk=instance.pk)
    else:
        instance._pre_save_instance = None


def create_proxy_model(model_class):
    return type(
        model_class.__name__,
        (model_class,),
        {
            "__module__": "df_notifications",
            "Meta": type("Meta", (object,), {"proxy": True, "auto_created": True}),
        },
    )


def register_notification_model_admin(model_class):
    ProxyModel = create_proxy_model(model_class)

    @admin.register(ProxyModel)
    class AdminProxyModel(ImportExportMixin, admin.ModelAdmin):
        def get_list_display(self, request):
            return (
                *model_class.admin_list_display,
                "content",
            )

        def get_resource_classes(self):
            class ProxyModelResource(ModelResource):
                class Meta:
                    model = model_class
                    skip_unchanged = True
                    report_skipped = False

            return [ProxyModelResource]

        def content(self, obj):
            try:
                from dbtemplates.models import Template

                template = Template.objects.get(name=obj.template)
                url = reverse("admin:dbtemplates_template_change", args=[template.pk])
                return mark_safe(f'<a href="{url}">Change</a>')
            except (ImportError, ObjectDoesNotExist):
                return ""

        @admin.action(
            description="Initialize DB Templates for notifications (override current content)"
        )
        def populate(self, request, qs):
            from dbtemplates.models import Template

            for item in qs:
                assert isinstance(item, NotificationModelMixin)
                content = "\n\n".join(
                    f"{{% block {part} %}}{{% endblock %}}"
                    for part in get_channel_instance(item.channel).template_parts
                )
                Template.objects.update_or_create(
                    name=item.template, defaults={"content": content}
                )

        actions = [populate]


def register_rule_model(rule_class):
    pre_save.connect(
        save_previous_instance,
        rule_class.model,
        weak=False,
        dispatch_uid="save_previous_instance",
    )

    def apply_action(sender, instance, **kwargs):
        rule_class.invoke(instance)

    post_save.connect(apply_action, rule_class.model, weak=False)

    register_notification_model_admin(rule_class)

    return rule_class


def register_reminder_model(reminder_class):
    register_notification_model_admin(reminder_class)
    return reminder_class
