#!/bin/bash
# Copyright (C) 2019 Magenta ApS, http://magenta.dk.
# Contact: info@magenta.dk.
#
################################################################################
# Changes to this file requires approval from Labs. Please add a person from   #
# Labs as required approval to your MR if you have any changes.                #
################################################################################

set -ex

if [ "$SKIP_MIGRATIONS" != "yes" ];
then
  # Run Migrate
  python ./manage.py migrate
fi

# Generate static content
python ./manage.py collectstatic --no-input --clear

exec "$@"
