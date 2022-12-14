# Generated by Django 3.2.15 on 2022-10-07 07:01

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='NotificationHistory',
            fields=[
                ('channel', models.PositiveSmallIntegerField(choices=[(100, 'push'), (200, 'email'), (300, 'sms'), (400, 'call'), (500, 'chat'), (600, 'slack'), (700, 'webhook'), (1000, 'console')])),
                ('subject', models.CharField(max_length=1024)),
                ('body', models.TextField(blank=True, null=True)),
                ('body_html', models.TextField(blank=True, null=True)),
                ('data', models.TextField(blank=True, null=True)),
                ('id', models.BigAutoField(primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(auto_now=True)),
                ('users', models.ManyToManyField(help_text='Users this notification was sent to', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'Notification history',
            },
        ),
        migrations.CreateModel(
            name='UserDevice',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=255, null=True, verbose_name='Name')),
                ('active', models.BooleanField(default=True, help_text='Inactive devices will not be sent notifications', verbose_name='Is active')),
                ('date_created', models.DateTimeField(auto_now_add=True, null=True, verbose_name='Creation date')),
                ('device_id', models.CharField(blank=True, db_index=True, help_text='Unique device identifier', max_length=255, null=True, verbose_name='Device ID')),
                ('registration_id', models.TextField(verbose_name='Registration token')),
                ('type', models.CharField(choices=[('ios', 'ios'), ('android', 'android'), ('web', 'web')], max_length=10)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'User device',
                'verbose_name_plural': 'User devices',
            },
        ),
        migrations.CreateModel(
            name='NotificationTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('channel', models.PositiveSmallIntegerField(choices=[(100, 'push'), (200, 'email'), (300, 'sms'), (400, 'call'), (500, 'chat'), (600, 'slack'), (700, 'webhook'), (1000, 'console')])),
                ('subject', models.CharField(max_length=1024)),
                ('body', models.TextField(blank=True, null=True)),
                ('body_html', models.TextField(blank=True, null=True)),
                ('data', models.TextField(blank=True, null=True)),
                ('slug', models.CharField(max_length=255, unique=True)),
                ('history', models.ManyToManyField(blank=True, to='df_notifications.NotificationHistory')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
