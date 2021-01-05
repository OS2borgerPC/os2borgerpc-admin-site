#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":

    install_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__))
    )

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "os2borgerpc_admin.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
