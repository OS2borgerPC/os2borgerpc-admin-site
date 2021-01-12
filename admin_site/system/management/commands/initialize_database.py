# Copyright (C) 2021 Magenta ApS, https://magenta.dk.
# Contact: info@magenta.dk.

from django.core.management.base import BaseCommand
from os2borgerpc_admin.initialize import initialize
from django.conf import settings


class Command(BaseCommand):
    """
    Initialize database.
    Helper command to seed database with (static) basic data.

    :Reference: :mod:`bevillingsplatform.initialize`

    Should be able to be run multiple times over without generating
duplicates.

    Example:

                $ python manage.py initialize_database

    """

    help = "Call initialize function to seed the database"

    def handle(self, *args, **options):
        if not settings.INITIALIZE_DATABASE:
            return

        # Display action
        print("Seed database with (static) basic data")

        # Run script
        initialize()

        # Inform user that the operation is complete
        # Assuming that if any of the underlying functions fail
        # the process is stopped/caught in place
        print("Database seeded with (static) basic data")
