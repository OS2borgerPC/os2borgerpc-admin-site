# Generated by Django 3.1.9 on 2021-11-18 12:48

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("system", "0036_auto_20211117_1423"),
    ]

    operations = [
        migrations.AddField(
            model_name="site",
            name="user_login_duration",
            field=models.DurationField(
                blank=True,
                default=datetime.timedelta(seconds=3600),
                null=True,
                verbose_name="Login duration",
            ),
        ),
        migrations.AddField(
            model_name="site",
            name="user_quarantine_duration",
            field=models.DurationField(
                blank=True,
                default=datetime.timedelta(seconds=14400),
                null=True,
                verbose_name="Quarantine duration",
            ),
        ),
    ]
