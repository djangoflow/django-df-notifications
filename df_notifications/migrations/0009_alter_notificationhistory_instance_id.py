# Generated by Django 4.2.5 on 2024-03-19 15:31

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("df_notifications", "0008_alter_custompushmessage_action_url_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="notificationhistory",
            name="instance_id",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]