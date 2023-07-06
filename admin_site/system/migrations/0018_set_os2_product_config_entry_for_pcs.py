from django.db import migrations, models


def set_os2_product_config_entry_for_pcs(apps, schema_editor):
    PC = apps.get_model("system", "PC")
    ConfigurationEntry = apps.get_model("system", "ConfigurationEntry")

    for pc in PC.objects.all():
        entries = pc.configuration.entries.all()
        os2borgerpc_flag = False

        for entry in entries:
            if entry.key == "os2borgerpc_version":
                os2borgerpc_flag = True

        if os2borgerpc_flag:
            product = "os2borgerpc"
        else:
            product = "os2displaypc"

        ConfigurationEntry.objects.create(
            key="os2_product", value=product, owner_configuration=pc.configuration
        )


class Migration(migrations.Migration):
    dependencies = [
        ("system", "0017_auto_20210712_1136"),
    ]

    operations = [migrations.RunPython(set_os2_product_config_entry_for_pcs)]
