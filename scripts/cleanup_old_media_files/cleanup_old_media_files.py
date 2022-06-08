#! /usr/bin/env python3

# Author: mfm@magenta.dk
# License: MIT
# Source partially based off:
# https://github.com/django-extensions/django-extensions/blob/main/django_extensions/management/commands/unreferenced_files.py

import os
import subprocess
import logging
import argparse

# HANDLE ARGUMENTS
parser = argparse.ArgumentParser()
# Overwriting what dry-run is saved as to have a properly named variable
# action and default are set so --dry-run is enough, without needing true/false
parser.add_argument('--dry-run', dest='dry_run',
                    help="Only print unreferenced files, don't delete them.",
                    action='store_true',
                    default=False)
parser.add_argument('CONTAINER',
                    help="The container name/ID, wherein django is running.")
parser.add_argument('HOST_PATH_TO_MEDIA_FILES',
                    help="The directory to the media files on the host.")
parser.add_argument('CONTAINER_PATH_TO_DJANGO',
                    help="The path to the django project within the container")
args = parser.parse_args()
if args.dry_run:
    DRY_RUN = True
else:
    DRY_RUN = False

# SETUP LOGGING
log = logging.getLogger(__name__)
# Effectively disable log messages in this script:
if DRY_RUN:
    # Effectively enable log messages in this script:
    log.setLevel(logging.DEBUG)
else:
    log.setLevel(logging.CRITICAL)
logging.basicConfig()

# GET A LIST FILES IN THE DB

# Convert bytes to a UTF-8 string to a list to a set
# Convert between the path inside the container to the path outside
referenced = set(subprocess.check_output(
    f"docker exec -it {args.CONTAINER} ./manage.py print_db_files", shell=True)
    .decode('utf-8')
    .replace(args.CONTAINER_PATH_TO_DJANGO, args.HOST_PATH_TO_MEDIA_FILES)
    .splitlines())

log.debug("Files in DB:")
log.debug(referenced)

# GET A LIST OF ALL FILES UNDER MEDIA_ROOT
media = set()
for root, dirs, files in os.walk(args.HOST_PATH_TO_MEDIA_FILES):
    for f in files:
        media.add(os.path.abspath(os.path.join(root, f)))
log.debug("Files on disk:")
log.debug(media)

# PRINT EACH FILE IN MEDIA_ROOT THAT IS NOT REFERENCED IN THE DATABASE
log.debug("Files on disk which are not in the DB:")
not_referenced = media - referenced
for f in not_referenced:
    if DRY_RUN:
        log.debug(f)
    else:
        os.remove(f)
