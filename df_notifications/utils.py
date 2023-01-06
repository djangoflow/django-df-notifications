def save_previous_instance(sender, instance, **kwargs):
    if instance.pk:
        instance._pre_save_instance = sender.objects.get(pk=instance.pk)
    else:
        instance._pre_save_instance = None
