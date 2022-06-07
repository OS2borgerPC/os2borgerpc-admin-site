# Copyright (C) 2021 Magenta ApS, https://magenta.dk.
# Contact: info@magenta.dk.

from django.core.management.base import (
    BaseCommand,
    CommandError,
)
from django.db import transaction
from django.contrib.auth import get_user_model
from system.models import (
    Site,
    Script,
    Batch,
    Job,
    PCGroup,
    PC,
)

User = get_user_model()


class Command(BaseCommand):
    """
    Run a script on pcs, group or site as maintenance jobs.

    NOTE: Only scripts without arguments are supported for now.

    Form:
        $ python manage.py run_maintenance_script <username> <script> <site> --pcs
    Examples:

        $ python manage.py run_maintenance_script shg 1 magenta --pcs 5 6 7 8
        $ python manage.py run_maintenance_script shg 2 magenta --sites 1 2
        $ python manage.py run_maintenance_script shg 3 magenta --groups 1 2

    """

    help = "Run a maintenance job script on pcs, groups or sites"

    def add_arguments(self, parser):
        parser.add_argument(
            "username", nargs="?", type=str, help="username of the user"
        )
        parser.add_argument("script", nargs="?", type=int, help="the id of the script")
        parser.add_argument(
            "script_site", nargs="?", type=str, help="the uid of the site"
        )
        parser.add_argument("--pcs", nargs="*", type=int, help="a list of pc uids")
        parser.add_argument("--sites", nargs="*", type=str, help="the uid of a site")
        parser.add_argument("--groups", nargs="*", type=str, help="the uid of a group")

    @transaction.atomic
    def handle(self, *args, **options):
        script_id = options["script"]
        script_site_uid = options["script_site"]
        username = options["username"]

        user = User.objects.filter(is_superuser=True, username=username).first()
        if not user:
            raise CommandError(f"User with username: {username} does not exist")

        script = Script.objects.filter(id=script_id).first()
        if not script:
            raise CommandError(f"Script with ID: {script_id} does not exist")

        script_site = Site.objects.filter(uid=script_site_uid).first()
        if not script_site:
            raise CommandError(f"Site with UID: {script_site_uid} does not exist")

        if options["pcs"]:
            pcs = PC.objects.filter(id__in=options["pcs"])
        elif options["sites"]:
            site_uids = options["sites"]
            sites = Site.objects.filter(uid__in=site_uids)
            pcs = PC.objects.filter(site__in=sites)
        elif options["groups"]:
            group_ids = options["groups"]
            pc_groups = PCGroup.objects.filter(uid__in=group_ids)
            pcs = PC.objects.filter(pc_groups__in=pc_groups)
        else:
            raise CommandError("--pcs, --site or --group needs to be given")

        self.stdout.write(
            self.style.SUCCESS(
                f"Do you want to run {script} on site {script_site}"
                f" as user {username} for {pcs.count()} PCs? (Y/y for yes)"
            )
        )
        confirmation = input()
        if confirmation in ["y", "Y"]:
            batch = Batch.objects.create(site=script_site, script=script, name="")
            for pc in pcs:
                Job.objects.create(user=user, batch=batch, pc=pc)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Maintenance job was created for pc: {pc}"
                        f" for site: {script_site}"
                    )
                )
        else:
            self.stdout.write(self.style.WARNING("Aborting"))
