from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('system', '0019_auto_20210713_1549'),
    ]

    operations = [
        migrations.RenameField(
            model_name='imageversion',
            old_name='img_vers',
            new_name='image_version',
        ),
        migrations.RenameField(
            model_name='imageversion',
            old_name='rel_date',
            new_name='release_date',
        ),
        migrations.RenameField(
            model_name='imageversion',
            old_name='rel_notes',
            new_name='release_notes',
        ),
        migrations.AlterModelOptions(
            name='imageversion',
            options={'ordering': ['platform', '-image_version']},
        ),
        migrations.AddField(
            model_name='imageversion',
            name='platform',
            field=models.CharField(choices=[('BORGERPC', 'BorgerPC'), ('DISPLAYPC', 'DisplayPC')], default='BORGERPC', max_length=128),
            preserve_default=False,
        ),
    ]
