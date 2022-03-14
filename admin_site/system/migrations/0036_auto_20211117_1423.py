# Generated by Django 3.1.9 on 2021-11-17 14:23

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('system', '0035_auto_20211111_1330'),
    ]

    operations = [
        migrations.AlterField(
            model_name='securityevent',
            name='assigned_user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='assigned user'),
        ),
    ]