from celery import Celery

import os


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")

app = Celery("df-notifications")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
