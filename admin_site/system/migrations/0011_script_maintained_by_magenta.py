# Generated by Django 3.1.4 on 2021-04-09 11:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('system', '0010_auto_20210628_1127'),
    ]

    operations = [
        migrations.AddField(
            model_name='script',
            name='maintained_by_magenta',
            field=models.BooleanField(default=False, verbose_name='maintained by Magenta'),
        ),
    ]
