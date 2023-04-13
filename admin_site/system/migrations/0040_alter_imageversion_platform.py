# Generated by Django 3.2.9 on 2022-01-10 14:44

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("system", "0039_auto_20211122_1511"),
    ]

    operations = [
        migrations.AlterField(
            model_name="imageversion",
            name="platform",
            field=models.CharField(
                choices=[
                    ("BORGERPC", "BorgerPC"),
                    ("BORGERPC_KIOSK", "BorgerPC Kiosk"),
                ],
                max_length=128,
            ),
        ),
    ]
