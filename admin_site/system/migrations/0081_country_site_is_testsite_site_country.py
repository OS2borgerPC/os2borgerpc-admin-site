# Generated by Django 4.2.1 on 2024-02-22 10:37

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("system", "0080_alter_eventruleserver_level_alter_job_status_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="Country",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255, verbose_name="country_name")),
            ],
            options={
                "ordering": ["name"],
            },
        ),
        migrations.AddField(
            model_name="site",
            name="is_testsite",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="site",
            name="country",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="sites",
                to="system.country",
            ),
        ),
    ]
