from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("system", "0089_backfill_read_only_config_keys"),
    ]

    operations = [
        migrations.AddField(
            model_name="pc",
            name="client_key_hash",
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
    ]
