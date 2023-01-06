from django.db.models.signals import post_save
from django.db.models.signals import pre_save


def save_previous_instance(sender, instance, **kwargs):
    if instance.pk:
        instance._pre_save_instance = sender.objects.get(pk=instance.pk)
    else:
        instance._pre_save_instance = None


#
#
# def register_notification(model, slugs):
#     def decorator(func):
#         templates = NotificationTemplate.objects.filter(slug__in=slugs)
#
#         pre_save.connect(save_previous_instance, model, weak=False, dispatch_uid="")
#
#         @functools.wraps(func)
#         def wrapper(sender, instance, **kwargs):
#             for template in templates:
#                 func(
#                     prev=instance._pre_save_instance,
#                     next=instance,
#                     template=template,
#                     **kwargs
#                 )
#
#         post_save.connect(wrapper, model, weak=False)
#
#     return decorator


def register_action_model(action_class):
    pre_save.connect(
        save_previous_instance,
        action_class.model,
        weak=False,
        dispatch_uid="save_previous_instance",
    )

    def apply_action(sender, instance, **kwargs):
        action_class.invoke(instance)

    post_save.connect(apply_action, action_class.model, weak=False)
    return action_class
