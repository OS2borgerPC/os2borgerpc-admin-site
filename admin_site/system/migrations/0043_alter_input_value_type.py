# Generated by Django 3.2.9 on 2022-02-09 12:43

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("system", "0042_alter_imageversion_release_notes"),
    ]

    operations = [
        migrations.AlterField(
            model_name="input",
            name="value_type",
            field=models.CharField(
                choices=[
                    ("STRING", "String"),
                    ("INT", "Integer"),
                    ("DATE", "Date"),
                    ("FILE", "File"),
                    ("BOOLEAN", "Boolean"),
                ],
                max_length=10,
                verbose_name="value type",
            ),
        ),
    ]
