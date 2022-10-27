# Generated by Django 3.2.15 on 2022-10-26 12:45

import datetime
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('system', '0061_alter_batch_options'),
    ]

    operations = [
        migrations.CreateModel(
            name='WakeChangeEvent',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=60, verbose_name='name')),
                ('date_start', models.DateField(verbose_name='date start')),
                ('time_start', models.TimeField(blank=True, null=True, verbose_name='time start')),
                ('date_end', models.DateField(verbose_name='date end')),
                ('time_end', models.TimeField(blank=True, null=True, verbose_name='time end')),
                ('type', models.CharField(choices=[('ALTERED_HOURS', 'event_type:Altered Hours'), ('CLOSED', 'event_type:Closed')], default='ALTERED_HOURS', max_length=15, verbose_name='type')),
            ],
            options={
                'ordering': ['date_start'],
            },
        ),
        migrations.CreateModel(
            name='WakeWeekPlan',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=60, verbose_name='name')),
                ('enabled', models.BooleanField(default=True, verbose_name='enabled')),
                ('sleep_state', models.CharField(choices=[('STANDBY', 'sleep_state:Standby'), ('FREEZE', 'sleep_state:Freeze'), ('MEM', 'sleep_state:Mem'), ('OFF', 'sleep_state:Off')], default='OFF', max_length=10, verbose_name='sleep state')),
                ('monday_on', models.TimeField(blank=True, default=datetime.time(8, 0), null=True, verbose_name='monday on')),
                ('monday_off', models.TimeField(blank=True, default=datetime.time(20, 0), null=True, verbose_name='monday off')),
                ('monday_open', models.BooleanField(default=True, verbose_name='monday open')),
                ('tuesday_on', models.TimeField(blank=True, default=datetime.time(8, 0), null=True, verbose_name='tuesday on')),
                ('tuesday_off', models.TimeField(blank=True, default=datetime.time(20, 0), null=True, verbose_name='tuesday off')),
                ('tuesday_open', models.BooleanField(default=True, verbose_name='tuesday open')),
                ('wednesday_on', models.TimeField(blank=True, default=datetime.time(8, 0), null=True, verbose_name='wednesday on')),
                ('wednesday_off', models.TimeField(blank=True, default=datetime.time(20, 0), null=True, verbose_name='wednesday off')),
                ('wednesday_open', models.BooleanField(default=True, verbose_name='wednesday open')),
                ('thursday_on', models.TimeField(blank=True, default=datetime.time(8, 0), null=True, verbose_name='thursday on')),
                ('thursday_off', models.TimeField(blank=True, default=datetime.time(20, 0), null=True, verbose_name='thursday off')),
                ('thursday_open', models.BooleanField(default=True, verbose_name='thursday open')),
                ('friday_on', models.TimeField(blank=True, default=datetime.time(8, 0), null=True, verbose_name='friday on')),
                ('friday_off', models.TimeField(blank=True, default=datetime.time(20, 0), null=True, verbose_name='friday off')),
                ('friday_open', models.BooleanField(default=True, verbose_name='friday open')),
                ('saturday_on', models.TimeField(blank=True, default=datetime.time(8, 0), null=True, verbose_name='saturday on')),
                ('saturday_off', models.TimeField(blank=True, default=datetime.time(20, 0), null=True, verbose_name='saturday off')),
                ('saturday_open', models.BooleanField(default=False, verbose_name='saturday open')),
                ('sunday_on', models.TimeField(blank=True, default=datetime.time(8, 0), null=True, verbose_name='sunday on')),
                ('sunday_off', models.TimeField(blank=True, default=datetime.time(20, 0), null=True, verbose_name='sunday off')),
                ('sunday_open', models.BooleanField(default=False, verbose_name='sunday open')),
                ('site', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='wake_week_plans', to='system.site')),
                ('wake_change_events', models.ManyToManyField(related_name='wake_week_plans', to='system.WakeChangeEvent', verbose_name='wake change events')),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.AddField(
            model_name='pcgroup',
            name='wake_week_plan',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='groups', to='system.wakeweekplan'),
        ),
    ]
