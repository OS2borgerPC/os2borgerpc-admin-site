import django
from django.core.management.base import BaseCommand
from system.models import Script, ScriptTag, Input
from system.script_fetcher import fetch_scripts

class Command(BaseCommand):

    """
    Get core scripts from the OS2 docs repo (which include scripts), and insert them in the database, so they can be accessed by site users.
    For security and consistency reasons, the matching commit hash (SHA-256) for the tag must also be specified, as the tag can easily be updated to point to 
    other (ill-intended) code. Using the hash, this is prevented.

    Example:
        manage.py fetch_and_install_core_scripts --versionTag v1.2.0 --commitHash 1c1c65e8f2de96f1f1dd8a3b574871477a13cc8fbd46b591e988206170735238
    """

    def add_arguments(self, parser):
        parser.add_argument("--versionTag", required=False)
        parser.add_argument("--commitHash", required=True)

    def handle(self, *args, **options):
        #Script.objects.all().delete() # TODO-script remove
        #Input.objects.all().delete() # TODO-script remove
        for script in fetch_scripts(options['versionTag'], options['commitHash']):
            versionedName = script.title + " " + "v0.0.0" # options['versionTag'] # TODO-script
            if not Script.objects.filter(name=versionedName).exists():
                with open(script.sourcePath, 'rb') as file:
                    # Get only the base file name
                    db_script = Script.objects.create(
                        name=versionedName,
                        description=script.description,
                        site=None, # None means global script
                        executable_code=django.core.files.File(file),
                        is_security_script=False,
                        is_hidden=False,
                        maintained_by_magenta=False,
                        feature_permission=None
                    )
                    tag, created = ScriptTag.objects.get_or_create(name=script.tag)
                    db_script.tags.add(tag)

                    position = 1
                    for parameter in script.parameters:
                      Input.objects.create(
                          script=db_script,
                          name=parameter.name,
                          value_type=parameter.type,
                          default_value=parameter.default,
                          position=position,
                          mandatory=parameter.mandatory
                      )
                      position += 1
                # TODO-script product?