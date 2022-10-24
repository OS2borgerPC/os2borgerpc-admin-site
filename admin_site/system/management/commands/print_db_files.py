# This is a command for Django's manage.py
# Source heavily based off:
# https://github.com/django-extensions/django-extensions/blob/main/django_extensions/management/commands/unreferenced_files.py
# Minor rewrites by: mfm@magenta.dk

# -*- coding: utf-8 -*-
import os
from collections import defaultdict

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import models

from django_extensions.management.utils import signalcommand


class Command(BaseCommand):
    help = "Prints a list of all files referenced in the database."

    @signalcommand
    def handle(self, *args, **options):

        # Get list of all fields (value) for each model (key)
        # that is a FileField or subclass of a FileField
        model_dict = defaultdict(list)
        for model in apps.get_models():
            for field in model._meta.fields:
                if issubclass(field.__class__, models.FileField):
                    model_dict[model].append(field)

        # Get a list of all files referenced in the database
        referenced = set()
        for model in model_dict:
            all = model.objects.all().iterator()
            for object in all:
                for field in model_dict[model]:
                    target_file = getattr(object, field.name)
                    if target_file:
                        # mfm: Using target_file.name instead of
                        # target_file.path to work with GCS and S3
                        # See: https://stackoverflow.com/a/48785695
                        referenced.add(os.path.abspath(target_file.name))
        # mfm: Linewise output for easy conversion to a list/set
        for ref in referenced:
            print(ref)
