# Good info on syntax: https://cheatography.com/linux-china/cheat-sheets/justfile/
# Easiest way to install on Ubuntu: 
# $ snap install --edge --classic just

# Default shell and settings used in the recipes
set shell := ["bash", "-uc"]

# Aliases
alias r := run
alias rd := run-debug
alias fp := fix-permissions

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
  if ! which fzf > /dev/null; then echo "fzf not installed. If on Ubuntu: Install the fzf package." && exit 1; fi
  @just --choose

# Help command, which lists available recipes
help:
  @just --list

# A helper recipe that ensures that a given docker container is running
verify-container-running container:
  #!/usr/bin/env sh
  # this shebang is to prevent just complaining about whitespace
  # https://github.com/casey/just#indentation
  if ! sudo docker ps | grep "{{container}}"; then
    printf  "%s\n" "Container not running. Exiting."
    exit 1
  fi

bash: (verify-container-running django_container)
  sudo docker exec -i --tty {{django_container}} /bin/bash

# Run bash in the django container without first running migrations
# Very convenient for running migrations when the container won't start due to changes in models
bash-no-migrate:
  sudo docker-compose run --rm --entrypoint bash {{compose_django_service}}

# Runs black on the python codebase
black:
  black --extend-exclude="/migrations/" admin_site

# Dump the database to a file named {{db_data_file}}
dump-db-data: (verify-container-running django_container)
  sudo docker exec {{django_container}} django-admin dumpdata > {{db_data_file}}

# Dump the database structure to a file named db-structure.psql
dump-db-structure: (verify-container-running django_container)
  sudo docker exec -i --tty {{db_container}} pg_dump -U postgres --schema-only bpc > {{db_structure_file}}

# View the db file contents from a dumped db
# it can also be viewed with fx.: jq . < out.json | view
view-dumped-db-data:
  if ! which nvim > /dev/null; then jq . {{db_data_file}} | less; else nvim -c ":%! jq ." {{db_data_file}}; fi

# Fix adminsite permissions in case you get "Permission Denied" errors
fix-permissions:
  #!/usr/bin/env sh
  if ! which fd > /dev/null; then
    printf '%s\n' "fd not installed. If on Ubuntu: Install the fd-find package, and create a symlink like this:" \
         "sudo ln -s /usr/bin/fdfind /usr/local/bin/fd"
    exit 1
  fi
  sudo fd --hidden -x chmod 777

# Run arbitrary manage.py commands. Examples: makemigrations/migrate/showmigrations/shell_plus
managepy +COMMANDS: (verify-container-running django_container)
  sudo docker exec -i --tty {{django_container}} ./manage.py {{COMMANDS}}

# Useful if changing requirements.txt and ...?
recreate-django:
  sudo docker-compose up --build

# Recreate the django database, replacing what you have with what's in the fixtures
recreate-db:
  sudo docker-compose down --volumes

# Start the admin-site stack
run:
  sudo docker-compose up
  printf '%s' "If permissions fail, verify umask and/or manually check if the permissions differ on the file mentioned, e.g. initialize.py"

# Start the admin-site stack in the background and attach specifically to the django container - so python breakpoints work
run-debug:
  sudo docker-compose up -d {{compose_django_service}} {{compose_db_service}}
  sudo docker attach {{django_container}}

# Run django's make-messages for translations
translations-make-messages: (verify-container-running django_container)
  @just managepy makemessages --all --ignore venv

# Run django's compile-messages (usually after make-messages) for translations
translations-compile-messages: (verify-container-running django_container)
  @just managepy compilemessages --locale da --locale sv

# Replace all the fixtures (test data) with what you currently have in your local adminsite db
update-test-data: (verify-container-running django_container)
  sudo docker-compose exec -u 0 {{compose_django_service}} python manage.py dumpdata --indent 4 auth > dev-environment/system_fixtures/050_auth.json
  sudo docker-compose exec -u 0 {{compose_django_service}} python manage.py dumpdata --indent 4 system > dev-environment/system_fixtures/100_system.json
  sudo docker-compose exec -u 0 {{compose_django_service}} python manage.py dumpdata --indent 4 account > dev-environment/system_fixtures/150_account.json
  printf '%s' 'NOTE: This may add unwanted log output to the top of the files! Verify and clean them up before commiting if so.'

# Create a graph of the django models to a file named models_graphed.png
graph-models: (verify-container-running django_container)
  # Tried using pip install instead but it kept complaining about missing graphviz binaries
  sudo docker exec -it -u 0 {{django_container}} apt-get update
  sudo docker exec -it -u 0 {{django_container}} apt-get install --assume-yes python3-pydotplus # alternately pytnho3-pygraphviz
  sudo docker exec -it -u 0 {{django_container}} pip install pydotplus
  @just managepy graph_models -a -g -o /tmp/{{models_output_file_name}}
  # docker cp is not part of docker-compose, so can't docker-compose exec that
  sudo docker cp {{django_container}}:/tmp/{{models_output_file_name}} {{models_output_file_name}}
