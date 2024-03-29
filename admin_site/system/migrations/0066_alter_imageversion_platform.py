# Generated by Django 3.2.17 on 2023-05-25 13:06

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("system", "0065_input_default_value"),
    ]

    operations = [
        migrations.AlterField(
            model_name="imageversion",
            name="platform",
            field=models.CharField(
                choices=[
                    ("BORGERPC", "OS2borgerPC"),
                    ("BORGERPC_KIOSK", "OS2borgerPC Kiosk"),
                    ("MEDBORGARPC", "Sambruk MedborgarPC"),
                ],
                max_length=128,
            ),
        ),
    ]
