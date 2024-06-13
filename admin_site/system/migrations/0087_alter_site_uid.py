# Generated by Django 4.2.11 on 2024-06-11 14:31

import django.core.validators
from django.db import migrations, models
import re


class Migration(migrations.Migration):
    dependencies = [
        ("system", "0086_remove_featurepermission_sites_remove_site_country_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="site",
            name="uid",
            field=models.CharField(
                help_text="Must be unique. Valid characters are a-z, A-Z, 0-9 and dashes, and the length must be between 2-40 characters. We suggest names like <organisation> or <organisation-location> (without brackets)",
                max_length=40,
                unique=True,
                validators=[
                    django.core.validators.RegexValidator(
                        re.compile("^[-a-zA-Z0-9]+\\Z"),
                        "Enter a valid “uid” consisting of letters, numbers or hyphens.",
                        "invalid",
                    )
                ],
                verbose_name="UID",
            ),
        ),
    ]
