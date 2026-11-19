import django
from django.core.management.base import BaseCommand
from system.models import Script


class Command(BaseCommand):

    """
    Migrate scripts with NULL commit hash to a legacy hash.
    
    This command should be run once before updating to a new core script release.
    It preserves the history of existing scripts by assigning them a legacy hash.
    
    Example:
        manage.py migrate_legacy_scripts --legacyHash db319672efdcc0f7402c4a7370aa763be9960c38
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--legacyHash",
            required=True,
            help="The commit hash to assign to existing scripts with NULL hash"
        )

    def handle(self, *args, **options):
        legacy_hash = options['legacyHash']
        
        null_hash_scripts = Script.objects.filter(core_script_commit_hash__isnull=True)
        
        if not null_hash_scripts.exists():
            self.stdout.write("No scripts with NULL hash found. Nothing to migrate.")
            return
        
        count = null_hash_scripts.update(core_script_commit_hash=legacy_hash)
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully migrated {count} scripts to legacy hash: {legacy_hash}"
            )
        )
