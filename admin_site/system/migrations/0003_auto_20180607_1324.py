# -*- coding: utf-8 -*-
# Generated by Django 1.11.9 on 2018-06-07 13:24
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("system", "0002_pc_location"),
    ]

    operations = [
        migrations.AddField(
            model_name="job",
            name="user",
            field=models.ForeignKey(
                default=108,
                on_delete=django.db.models.deletion.CASCADE,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="pc",
            name="mac",
            field=models.CharField(blank=True, max_length=255, verbose_name="mac"),
        ),
        migrations.AlterField(
            model_name="input",
            name="value_type",
            field=models.CharField(
                choices=[
                    ("STRING", "String"),
                    ("INT", "Integer"),
                    ("DATE", "Date"),
                    ("FILE", "File"),
                ],
                max_length=10,
                verbose_name="value type",
            ),
        ),
        migrations.AlterField(
            model_name="job",
            name="status",
            field=models.CharField(
                choices=[
                    ("NEW", "jobstatus:New"),
                    ("SUBMITTED", "jobstatus:Submitted"),
                    ("RUNNING", "jobstatus:Running"),
                    ("FAILED", "jobstatus:Failed"),
                    ("DONE", "jobstatus:Done"),
                    ("RESOLVED", "jobstatus:Resolved"),
                ],
                default="NEW",
                max_length=10,
            ),
        ),
        migrations.AlterField(
            model_name="pc",
            name="location",
            field=models.CharField(
                blank=True, default="", max_length=1024, verbose_name="location"
            ),
        ),
        migrations.AlterField(
            model_name="script",
            name="executable_code",
            field=models.FileField(
                upload_to="script_uploads", verbose_name="executable code"
            ),
        ),
        migrations.AlterField(
            model_name="securityevent",
            name="status",
            field=models.CharField(
                choices=[
                    ("NEW", "eventstatus:New"),
                    ("ASSIGNED", "eventstatus:Assigned"),
                    ("RESOLVED", "eventstatus:Resolved"),
                ],
                default="NEW",
                max_length=10,
            ),
        ),
        migrations.AlterField(
            model_name="securityproblem",
            name="level",
            field=models.CharField(
                choices=[
                    ("Critical", "securitylevel:Critical"),
                    ("High", "securitylevel:High"),
                    ("Normal", "securitylevel:Normal"),
                ],
                default="High",
                max_length=10,
            ),
        ),
    ]
