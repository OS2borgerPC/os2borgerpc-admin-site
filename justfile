# Good info on syntax: https://cheatography.com/linux-china/cheat-sheets/justfile/
# Easiest way to install on Ubuntu:
# $ snap install --edge --classic just

# Default shell and settings used in the recipes
set shell := ["bash", "-uc"]

# Set user ID and group ID dynamically. These are in turn used in docker compose when mounting volumes.
# This should get us closer to being able to remove "privileged", and make permissions errors (and "just fix-permissions") less relevant
export UID := `id -u`
export GID := `id -g`

# Aliases
alias r := run
alias rd := run-debug
alias fp := fix-permissions
alias tmm := translations-make-messages
alias tcm := translations-compile-messages

# Variables
django_container := "bpc_admin_site_django"
compose_django_service := "os2borgerpc-admin"

db_container := "bpc_admin_site_db"
compose_db_service := "db"
db_data_file := "db-data.json"
db_structure_file := "db-structure.psql"

models_output_file_name := "models_graphed.png"

# The default recipe, if none is specified
@default:
  @just --list

# Help command, which lists available recipes
help:
  @just --list

# A helper recipe that ensures that a given docker container is running
verify-container-running container:
  #!/usr/bin/env sh
  # this shebang is to prevent just complaining about whitespace
  # https://github.com/casey/just#indentation
  if ! docker ps | grep "{{container}}"; then
    printf  "%s\n" "Container not running. Exiting."
    exit 1
  fi

bash-django: (verify-container-running django_container)
  docker exec -i --tty {{django_container}} /bin/bash

# Run bash in a django container without first running migrations - convenient for e.g. makemigrations
bash-django-skip-entrypoint:
  docker compose run --rm --entrypoint bash {{compose_django_service}}

# Runs black on the python codebase
black:
  black admin_site

# Dump the database to a file named {{db_data_file}}
dump-db-data: (verify-container-running django_container)
  docker exec {{django_container}} django-admin dumpdata > {{db_data_file}}

# Dump the database structure to a file named db-structure.psql
dump-db-structure: (verify-container-running django_container)
  docker exec -i --tty {{db_container}} pg_dump -U postgres --schema-only bpc > {{db_structure_file}}

# View the db file contents from a dumped db
# it can also be viewed with fx.: jq . < out.json | view
view-dumped-db-data:
  if ! which nvim > /dev/null; then jq . {{db_data_file}} | less; else nvim -c ":%! jq ." {{db_data_file}}; fi

# Fix adminsite permissions in case you get "Permission Denied" errors
fix-permissions:
  #!/usr/bin/env sh
  # Setting all directories to 777, all files to 666 and finally set the executable bit for the few files needing that
  if ! which fd > /dev/null; then
    printf '%s\n' "fd not installed. If on Ubuntu: Install the fd-find package, and create a symlink like this:" \
         "sudo ln -s /usr/bin/fdfind /usr/local/bin/fd"
    exit 1
  fi
  sudo fd --hidden --type directory -x chmod 777
  sudo fd --hidden --type file -x chmod 666
  sudo chmod 755 justfile docker/docker-entrypoint.sh scripts/cleanup_old_media_files/cleanup_old_media_files.py admin_site/manage.py

# Run arbitrary manage.py commands. Examples: makemigrations/migrate/showmigrations/shell_plus
managepy +COMMAND: (verify-container-running django_container)
  docker exec -i --tty {{django_container}} ./manage.py {{COMMAND}}

# Related to: https://docs.djangoproject.com/en/4.2/howto/upgrade-version/
# Checks for any deprecation warnings in your project
check-deprecation-warnings: (verify-container-running django_container)
  docker exec -i --tty {{django_container}} python -Wa manage.py test

# Useful if changing requirements.txt and ...?
recreate-django:
  docker compose up --build

# Recreate the django database, replacing what you have with what's in the fixtures
recreate-db:
  docker compose down --volumes

# Start the admin-site stack
run:
  docker compose up
  printf '%s' "If permissions fail, verify umask and/or manually check if the permissions differ on the file mentioned, e.g. initialize.py"

# Start the admin-site stack in the background and attach specifically to the django container - so python breakpoints work
run-debug:
  docker compose up -d
  docker attach {{django_container}}

# Run django's make-messages for translations, including translations for javascript files (djangojs)
# --no-obsolete removes unused translations, --add-location file is there to make diffs clearer by skipping line
# numbers, so a change early in views.py doesn't make makemessages update hundreds of line references
# TODO: makemessages sometimes suddenly makes changes to where it line wraps, making diffs hard to read. Seemingly there's
# no hard line wrap set, and the only option is to disable line wrap completely which doesn't seem ideal. Hopefully a
# future Django version provides a solution.
translations-make-messages: (verify-container-running django_container) fix-permissions
  @just managepy makemessages --all --ignore venv --add-location file --no-obsolete
  @just managepy makemessages --all --ignore venv --add-location file --no-obsolete -d djangojs

# Run django's compile-messages (usually after make-messages) for translations
translations-compile-messages: (verify-container-running django_container)
  @just managepy compilemessages --locale da --locale sv

# Replace all the fixtures (test data) with what you currently have in your local adminsite db
update-test-data: (verify-container-running django_container)
  docker compose exec -u 0 -T {{compose_django_service}} python manage.py dumpdata --indent 4 auth > dev-environment/system_fixtures/050_auth.json
  docker compose exec -u 0 -T {{compose_django_service}} python manage.py dumpdata --indent 4 system > dev-environment/system_fixtures/100_system.json
  docker compose exec -u 0 -T {{compose_django_service}} python manage.py dumpdata --indent 4 account > dev-environment/system_fixtures/150_account.json
  docker compose exec -u 0 -T {{compose_django_service}} python manage.py dumpdata --indent 4 changelog > dev-environment/changelog_fixtures/100_changelog.json

# Create a graph of the django models to a file named models_graphed.png
graph-models: (verify-container-running django_container)
  # Tried using pip install instead but it kept complaining about missing graphviz binaries
  docker exec -it -u 0 {{django_container}} apt-get update
  docker exec -it -u 0 {{django_container}} apt-get install --assume-yes python3-pydotplus # alternately pytnho3-pygraphviz
  docker exec -it -u 0 {{django_container}} pip install pydotplus
  @just managepy graph_models -a -g -o /tmp/{{models_output_file_name}}
  # docker cp is not part of docker compose, so can't docker compose exec that
  docker cp {{django_container}}:/tmp/{{models_output_file_name}} {{models_output_file_name}}
