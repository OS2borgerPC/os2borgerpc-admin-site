from django.db import migrations

# Governing/trust config keys. Kept inline (not imported from rpc.py) so this
# migration stays self-contained and stable even if that set changes later.
# Mirrors READ_ONLY_IN_UI_CONFIG_KEYS in system/rpc.py at the time of writing.
READ_ONLY_CONFIG_KEYS = [
    "admin_url",
    "xml_rpc_url",
    "os2borgerpc_client_package",
    "os2borgerpc_client_version",
]


def mark_read_only(apps, schema_editor):
    """Protect governing keys on already-registered machines.

    Entries created before the read_only field existed all default to False,
    so without this backfill the anti-bricking protection would only cover
    newly registered machines. This marks existing governing-key entries so
    the current fleet is protected too.
    """
    ConfigurationEntry = apps.get_model("system", "ConfigurationEntry")
    ConfigurationEntry.objects.filter(key__in=READ_ONLY_CONFIG_KEYS).update(
        read_only=True
    )


def unmark_read_only(apps, schema_editor):
    ConfigurationEntry = apps.get_model("system", "ConfigurationEntry")
    ConfigurationEntry.objects.filter(key__in=READ_ONLY_CONFIG_KEYS).update(
        read_only=False
    )


class Migration(migrations.Migration):

    dependencies = [
        ("system", "0088_configurationentry_read_only"),
    ]

    operations = [
        migrations.RunPython(mark_read_only, unmark_read_only),
    ]
