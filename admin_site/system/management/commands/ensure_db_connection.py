# Copyright (C) 2019 Magenta ApS, http://magenta.dk.
# Contact: info@magenta.dk.
#

import sys
import time
from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError


class Command(BaseCommand):
    help = "Check the connection to the database."

    def add_arguments(self, parser):
        parser.add_argument(
            "-w",
            "--wait",
            default=1,
            type=int,
            help="Retry the connection for every second for WAIT seconds.",
        )

    def handle(self, *args, **options):
        for i in range(0, options["wait"]):
            attempt = "%02d/%02d " % (i + 1, options["wait"])
            try:
                connections["default"].ensure_connection()
                self.stdout.write("%s Connected to database." % attempt)
                sys.exit(0)
            except OperationalError as e:
                self.stdout.write(str(e))
                self.stdout.write(
                    "%s Unable to connect to database." % attempt
                )
                if i < options["wait"] - 1:
                    time.sleep(1)
        self.stdout.write("%s Giving up." % attempt)
        sys.exit(1)

