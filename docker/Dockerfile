# Copyright (C) 2021 Magenta ApS, http://magenta.dk.
# Contact: info@magenta.dk.

FROM node:16 as frontend

WORKDIR /code/nodejs

COPY nodejs .
RUN npm ci \
 && npm run build
CMD ["/bin/sh", "-c", "npm run watch-sass"]

FROM python:3.8 AS os2borgerpc

LABEL org.opencontainers.image.title="OS2borgerPC" \
      org.opencontainers.image.vendor="Magenta ApS" \
      org.opencontainers.image.licenses="GPL" \
      org.opencontainers.image.url="https://os2.eu/produkt/os2borgerpc"\
      org.opencontainers.image.source="https://github.com/OS2borgerPC/admin-site"

ENV PYTHONUNBUFFERED=1 \
  BPC_USER_CONFIG_PATH=/user-settings.ini \
  PYTHONPATH=/code/admin_site/:$PYTHONPATH\
  DJANGO_SETTINGS_MODULE=os2borgerpc_admin.settings

WORKDIR /code/
COPY admin_site/sys-requirements.txt sys-requirements.txt

# hadolint ignore=SC2046,DL3008
RUN set -ex \
  # Add a bpc group and user. Note: this is a system user/group, but have
  # UID/GID above the normal SYS_UID_MAX/SYS_GID_MAX of 999, but also above the
  # automatic ranges of UID_MAX/GID_MAX used by useradd/groupadd. See
  # `/etc/login.defs`. Hopefully there will be no conflicts with users of the
  # host system or users of other docker containers.
  && groupadd -g 75030 -r bpc\
  && useradd -u 75030 --no-log-init -r -g bpc bpc \
  # Install system dependencies from file.
  && apt-get -y update \
  && apt-get -y install --no-install-recommends $(grep -o '^[^#][[:alnum:].-]*' sys-requirements.txt) \
  # clean up after apt-get and man-pages
  && apt-get clean \
  && rm -rf "/var/lib/apt/lists/*"  "/tmp/*"  "/var/tmp/*"  "/usr/share/man/??"  "/usr/share/man/??_*" \
 # create folders at easily mountable paths for output from django
 && install -o bpc -g bpc -d /log \
 && install -o bpc -g bpc -d /media

VOLUME /log
VOLUME /media

WORKDIR /code/

COPY VERSION /code/VERSION

# Install requirements.
COPY admin_site/requirements.txt /code/admin_site/requirements.txt
RUN pip3 install --no-cache-dir -r  admin_site/requirements.txt

# Install supercronic
ENV SUPERCRONIC_URL=https://github.com/aptible/supercronic/releases/download/v0.2.25/supercronic-linux-amd64 \
    SUPERCRONIC=supercronic-linux-amd64 \
    SUPERCRONIC_SHA1SUM=642f4f5a2b67f3400b5ea71ff24f18c0a7d77d49

# hadolint ignore=DL4006
RUN curl -fsSLO "$SUPERCRONIC_URL" \
 && echo "${SUPERCRONIC_SHA1SUM}  ${SUPERCRONIC}" | sha1sum -c - \
 && chmod +x "$SUPERCRONIC" \
 && mv "$SUPERCRONIC" "/usr/local/bin/${SUPERCRONIC}" \
 && ln -s "/usr/local/bin/${SUPERCRONIC}" /usr/local/bin/supercronic

# Copy backend code.
COPY README.rst .
COPY LICENSE .
COPY docker ./docker
COPY admin_site ./admin_site

# Copy crontab-file
COPY crontab /crontab

WORKDIR /code/admin_site

# Copy frontend static files.
COPY --from=frontend \
  /code/nodejs/dist/css/bootstrap.* \
  /code/nodejs/node_modules/bootstrap-table/dist/bootstrap-table.min.css \
  /frontend/css/
COPY --from=frontend \
  /code/nodejs/node_modules/bootstrap/dist/js/bootstrap.bundle.min.js* \
  /code/nodejs/node_modules/jquery/dist/jquery.min.js \
  /code/nodejs/node_modules/qrcodejs/qrcode.min.js \
  /code/nodejs/node_modules/bootstrap-table/dist/bootstrap-table.min.js \
  /code/nodejs/node_modules/bootstrap-table/dist/locale/bootstrap-table-da-DK.min.js \
  /frontend/js/

# Unfortunately, `collectstatic` requires all settings to be set. We include a
# set of insecure setting here for only this purpose. We make sure to delete it
# afterward. If `insecure-settings.ini` is found in any production image,
# consider it a bug. See `insecure-settings.ini` for a detailed explanation.
ENV DB_NAME="dummy" \
    DB_USER="dummy" \
    DB_PASSWORD="dummy" \
    DB_HOST="dummy" \
    DB_PORT="dummy"
RUN set -ex \
  && BPC_USER_CONFIG_PATH=/code/docker/insecure-settings.ini python ./manage.py collectstatic --no-input --clear \
  && BPC_USER_CONFIG_PATH=/code/docker/insecure-settings.ini python ./manage.py compilemessages \
  && rm /code/docker/insecure-settings.ini

# Run the server as the bpc user on port 9999
USER bpc:bpc
EXPOSE 9999
EXPOSE 8080
ENTRYPOINT ["/code/docker/docker-entrypoint.sh"]
CMD bash -c "gunicorn --bind 0.0.0.0:8080 os2borgerpc_admin.jobsWsgi & \
             gunicorn --config /code/docker/gunicorn-settings.py os2borgerpc_admin.wsgi"
