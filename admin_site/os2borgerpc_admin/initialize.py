# Copyright (C) 2019 Magenta ApS, http://magenta.dk.
# Contact: info@magenta.dk.
"""Functions for populating the database with initial data."""

from django.core.management import call_command

from django.contrib.auth.models import User

from account.models import UserProfile
from system.models import Site, Configuration


def initialize():
    """Initialize all the basic data we want at start.

    Should be able to be run multiple times over without
    generating duplicates.
    """
    initialize_sites()
    initialize_users()


def initialize_users():
    """Prime the system with some users to get started.

    Data should be the output of 
    "manage.py dumpdata django.contrib.auth.models.User" and 
    "manage.py dumpdata account.UserProfile".

    """
    call_command("loaddata", "users.json", app_label="system")
    call_command("loaddata", "user_profiles.json", app_label="system")


def initialize_sites():
    """Prime the system with some sites to get started.

    Data should be the output of "manage.py dumpdata system.Site"
    and "manage.py dumpdata system.Configuration".
    """
    call_command("loaddata", "site_configurations.json", app_label="system")
    call_command("loaddata", "sites.json", app_label="system")
