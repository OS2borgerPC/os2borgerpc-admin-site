# Generated by Django 3.1.4 on 2021-04-09 12:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0003_migrate_from_single_site_to_multiple_sites'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='userprofile',
            name='site',
        ),
        migrations.RemoveField(
            model_name='userprofile',
            name='type',
        ),
    ]