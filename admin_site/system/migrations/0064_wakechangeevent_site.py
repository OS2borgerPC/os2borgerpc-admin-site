# Generated by Django 3.2.15 on 2022-10-31 15:54

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('system', '0063_auto_20221027_1033'),
    ]

    operations = [
        migrations.AddField(
            model_name='wakechangeevent',
            name='site',
            field=models.ForeignKey(default=9, on_delete=django.db.models.deletion.CASCADE, related_name='wake_change_events', to='system.site'),
            preserve_default=False,
        ),
    ]
