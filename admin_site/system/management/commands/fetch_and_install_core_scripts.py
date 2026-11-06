import django
from django.core.management.base import BaseCommand
from system.models import CoreScriptLibrary, Script, ScriptTag, Input
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
        version_tag = options['versionTag']
        commit_hash = options['commitHash']

        self.stdout.write(f"Fetching scripts from {repo_url} repository...")
        scripts = fetch_scripts(repo_url, version_tag, commit_hash)

        library, _ = CoreScriptLibrary.objects.get_or_create(
            commit_hash=commit_hash,
            defaults={
                "repo_url": repo_url,
                "tag": version_tag,
                "is_active": False,
            },
        )
        if version_tag and library.tag != version_tag:
            library.tag = version_tag
            library.repo_url = repo_url
            library.save(update_fields=["tag", "repo_url"])

        for script in scripts:
            versionedName = f'{script.title} (version: {script.version})'
            script_filters = {"core_script_library": library}
            if script.uid:
                script_filters["uid"] = script.uid
            else:
                script_filters["name"] = versionedName

            db_script, created = Script.objects.get_or_create(
                defaults={
                    "name": versionedName,
                    "description": script.description,
                    "site": None,  # None means global script
                    "executable_code": None,
                    "is_security_script": script.security,
                    "is_hidden": script.hidden,
                    "maintained_by_magenta": False,
                    "feature_permission": None,
                    "uid": script.uid,
                    "core_script_version": script.version,
                    "core_script_library": library,
                },
                **script_filters,
            )

            if not created:
                db_script.name = versionedName
                db_script.description = script.description
                db_script.is_security_script = script.security
                db_script.is_hidden = script.hidden
                db_script.uid = script.uid
                db_script.core_script_version = script.version
                db_script.core_script_library = library

            with open(script.sourcePath, 'rb') as file:
                db_script.executable_code.save(f"{script.uid or script.title}.sh", django.core.files.File(file), save=False)

            db_script.save()

            tag, created = ScriptTag.objects.get_or_create(name=script.tag)
            db_script.tags.clear()
            db_script.tags.add(tag)

            position = 0
            db_script.inputs.all().delete()
            for parameter in script.parameters:
                Input.objects.create(
                    script=db_script,
                    name=parameter.name,
                    value_type=parameter.type,
                    default_value=parameter.default,
                    position=position,
                    mandatory=parameter.mandatory,
                )
                position += 1
