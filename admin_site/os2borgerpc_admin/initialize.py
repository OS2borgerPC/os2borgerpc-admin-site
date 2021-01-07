# Copyright (C) 2021 Magenta ApS, http://magenta.dk.
# Contact: info@magenta.dk.
"""Functions for populating the database with initial data."""

import os

from django.core.management import call_command

from os2borgerpc_admin.settings import install_dir

fixtures_dir = os.path.join(install_dir, "system/fixtures")


def initialize():
    """Initialize all the basic data we want at start.

    Should be able to be run multiple times over without
    generating duplicates.
    """
    if os.path.exists(fixtures_dir) and os.path.isdir(fixtures_dir):
        initialize_sites()
        initialize_users()


def initialize_users():
    """Prime the system with some users to get started.

    Data should be the output of
    "manage.py dumpdata django.contrib.auth.models.User" and
    "manage.py dumpdata account.UserProfile".

    """
    if os.path.exists(os.path.join(fixtures_dir, "users.json")):
        call_command("loaddata", "users.json", app_label="system")
        call_command("loaddata", "user_profiles.json", app_label="system")


def initialize_sites():
    """Prime the system with some sites to get started.

    Data should be the output of "manage.py dumpdata system.Site"
    and "manage.py dumpdata system.Configuration".
    """
    if os.path.exists(os.path.join(fixtures_dir, "sites.json")):
        call_command(
            "loaddata", "site_configurations.json", app_label="system"
        )
        call_command("loaddata", "sites.json", app_label="system")
