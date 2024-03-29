# Generated by Django 4.2.5 on 2023-11-16 09:35

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("df_notifications", "0007_custompushmessage"),
    ]

    operations = [
        migrations.AlterField(
            model_name="custompushmessage",
            name="action_url",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name="custompushmessage",
            name="audience",
            field=models.ManyToManyField(
                blank=True,
                help_text="Leave blank to send to all users",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="custompushmessage",
            name="sent",
            field=models.DateTimeField(
                blank=True, db_index=True, editable=False, null=True
            ),
        ),
    ]
