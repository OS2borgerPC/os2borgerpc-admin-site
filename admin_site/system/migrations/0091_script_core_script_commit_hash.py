# Generated migration for adding core_script_commit_hash field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('system', '0090_pc_client_key_hash'),
    ]

    operations = [
        migrations.AddField(
            model_name='script',
            name='core_script_commit_hash',
            field=models.CharField(blank=True, db_index=True, max_length=40, null=True, verbose_name='Core Script Commit Hash'),
        ),
    ]
