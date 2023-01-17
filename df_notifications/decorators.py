from django.contrib import admin
from django.db.models.signals import post_save
from django.db.models.signals import pre_save


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
    class AdminProxyModel(admin.ModelAdmin):
        def get_list_display(self, request):
            return (
                "template_prefix",
                "channel",
                *model_class.admin_list_display,
            )


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
