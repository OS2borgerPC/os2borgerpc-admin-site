#!/bin/bash
# Copyright (C) 2019 Magenta ApS, http://magenta.dk.
# Contact: info@magenta.dk.

set -ex

./manage.py ensure_db_connection --wait 30

if [ "$SKIP_MIGRATIONS" != "yes" ];
then
  # Run Migrate
  python ./manage.py migrate
fi

./manage.py createsuperuser_if_none_exists --username $ADMIN_USERNAME --email $ADMIN_EMAIL --password $ADMIN_PASSWORD

exec "$@"