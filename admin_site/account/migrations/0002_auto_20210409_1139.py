# Generated by Django 3.1.4 on 2021-04-09 11:39

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('system', '0008_auto_20201210_0950'),
        ('account', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='SiteMembership',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('site_user_type', models.IntegerField(choices=[(1, 'Site User'), (2, 'Site Admin')], default=1)),
                ('site', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='system.site')),
                ('user_profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='account.userprofile')),
            ],
        ),
        migrations.AddField(
            model_name='userprofile',
            name='sites',
            field=models.ManyToManyField(related_name='user_profiles', through='account.SiteMembership', to='system.Site'),
        ),
        migrations.AddConstraint(
            model_name='sitemembership',
            constraint=models.UniqueConstraint(fields=('site', 'user_profile'), name='unique_site_user_profile'),
        ),
    ]
