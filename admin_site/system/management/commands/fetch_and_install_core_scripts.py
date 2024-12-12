import django
from django.core.management.base import BaseCommand
from system.models import Script, ScriptTag, Input
from system.script_fetcher import fetch_scripts

class Command(BaseCommand):

    """
    Get core scripts from a (correctly formatted) git repo, and insert them in the database, so they can be accessed by site users.
    For security and consistency reasons, the matching commit hash (SHA-256) for the tag must also be specified, as the tag can easily be updated to point to 
    other (ill-intended) code. Using the hash, this is prevented.

    Example:
        manage.py fetch_and_install_core_scripts --versionTag v0.1.2 --commitHash b3a791b52bc9937c6cb168c706ee003b0666fc93
    """

    def add_arguments(self, parser):
        parser.add_argument("--versionTag", required=True)
        parser.add_argument("--commitHash", required=True)

    def handle(self, *args, **options):
        repo_url = "https://github.com/OS2borgerPC/os2borgerpc-core-scripts.git"
        self.stdout.write(f"Fetching scripts from {repo_url} repository...")
        scripts = fetch_scripts("https://github.com/OS2borgerPC/os2borgerpc-core-scripts.git", options['versionTag'], options['commitHash'])

        for script in scripts:
            versionedName = script.title + " " + options['versionTag']
            uid = script.metadata.get("uid", None)
            is_security_script = script.metadata.get("security", False)
            is_hidden = script.metadata.get("hidden", False)

            if uid and Script.objects.filter(uid=uid).exists():
                Script.objects.filter(uid=uid).delete()

            if not Script.objects.filter(name=versionedName).exists():
                with open(script.sourcePath, 'rb') as file:
                    # Get only the base file name
                    db_script = Script.objects.create(
                        name=versionedName,
                        description=script.description,
                        site=None, # None means global script
                        executable_code=django.core.files.File(file),
                        is_security_script=is_security_script,
                        is_hidden=is_hidden,
                        maintained_by_magenta=False,
                        feature_permission=None,
                        uid=uid
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