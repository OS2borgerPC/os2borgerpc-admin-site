# Copyright (C) 2021 Magenta ApS, http://magenta.dk.
# Contact: info@magenta.dk.
"""Functions for populating the database with initial data."""

import os
import glob

from django.core.management import call_command

from os2borgerpc_admin.settings import install_dir

fixtures_dir = os.path.join(install_dir, "system/fixtures")


def initialize():
    """Initialize all the basic data we want at start.

    Should be able to be run multiple times over without
    generating duplicates.
    """
    if os.path.exists(fixtures_dir) and os.path.isdir(fixtures_dir):
        for file in glob.glob(os.path.join(fixtures_dir, "*.json")):
            if os.path.isfile(file):
                call_command("loaddata", file)
