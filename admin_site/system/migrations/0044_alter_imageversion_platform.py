# Generated by Django 3.2.9 on 2022-02-23 16:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('system', '0043_alter_input_value_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='imageversion',
            name='platform',
            field=models.CharField(choices=[('BORGERPC', 'OS2borgerPC'), ('BORGERPC_KIOSK', 'OS2borgerPC Kiosk')], max_length=128),
        ),
    ]
