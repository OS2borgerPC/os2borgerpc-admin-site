# Generated by Django 3.2.14 on 2022-10-19 15:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('system', '0063_wakeweekplan_sleep_state'),
    ]

    operations = [
        migrations.AddField(
            model_name='script',
            name='is_hidden',
            field=models.BooleanField(default=False, verbose_name='hidden script'),
        ),
        migrations.AlterField(
            model_name='wakeweekplan',
            name='sleep_state',
            field=models.CharField(choices=[('STANDBY', 'sleep_state:Standby'), ('FREEZE', 'sleep_state:Freeze'), ('MEM', 'sleep_state:Mem'), ('OFF', 'sleep_state:Off')], default='OFF', max_length=10, verbose_name='sleep state'),
        ),
    ]