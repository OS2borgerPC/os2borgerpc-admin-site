# Generated by Django 4.2.1 on 2023-11-07 10:53

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("system", "0076_remove_site_cicero_password_remove_site_cicero_user_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="site",
            name="citizen_login_api_password",
            field=models.CharField(
                blank=True,
                help_text="Necessary for customers who wish to authenticate BorgerPC logins through an API (e.g. Cicero)",
                max_length=255,
                verbose_name="Password for login API (e.g. Cicero)",
            ),
        ),
    ]
