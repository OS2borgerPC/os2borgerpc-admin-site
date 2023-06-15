# Copyright (C) 2021 Magenta ApS, https://magenta.dk.
# Contact: info@magenta.dk.

from collections import defaultdict

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

    Notes:
    Only scripts without arguments are supported for now.
    Sites and Groups arguments take UID's while the PC argument takes ID's.
    The script does not validate that a given group, site or PC exists. In case one doesn't match, it's silently ignored.

    Form:
            $ python manage.py run_maintenance_script <user_username> <script_uid_to_run> {--pcs <target_pc_ids...> | --groups <target_group_uids...>| --sites <target_site_uids...>}
    Examples:

        $ python manage.py run_maintenance_script shg 1 magenta --pcs 1 4
        $ python manage.py run_maintenance_script jabbi 3 magenta-test --groups group1
        $ python manage.py run_maintenance_script gitte 2 magenta --sites magenta mag test


    """

    help = "Run a maintenance job script on pcs, groups or sites"

    def add_arguments(self, parser):
        parser.add_argument(
            "username", nargs="?", type=str, help="username of the user"
        )
        parser.add_argument("script", nargs="?", type=int, help="the id of the script")
        parser.add_argument("--pcs", nargs="*", type=int, help="a list of pc uids")
        parser.add_argument("--sites", nargs="*", type=str, help="the uid of a site")
        parser.add_argument("--groups", nargs="*", type=str, help="the uid of a group")

    @transaction.atomic
    def handle(self, *args, **options):
        script_id = options["script"]
        username = options["username"]

        user = User.objects.filter(is_superuser=True, username=username).first()
        if not user:
            raise CommandError(f"User with username: {username} does not exist")

        script = Script.objects.filter(id=script_id).first()
        if not script:
            raise CommandError(f"Script with ID: {script_id} does not exist")

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

        site_pcs_dict = defaultdict(list)
        for pc in pcs.order_by("site"):
            site_pcs_dict[pc.site].append(pc)

        self.stdout.write(
            self.style.SUCCESS(
                f"Do you want to run {script} on sites: "
                f"{', '.join([s.name for s in site_pcs_dict.keys()])}"
                f" as user {username} for {pcs.count()} PCs? (Y/y for yes)"
            )
        )
        confirmation = input()
        if confirmation in ["y", "Y"]:
            for site, pcs_list in site_pcs_dict.items():
                batch = Batch.objects.create(site=site, script=script, name="")
                for pc in pcs_list:
                    Job.objects.create(user=user, batch=batch, pc=pc)
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Maintenance job was created for pc: {pc}"
                            f" for site: {site}"
                        )
                    )
        else:
            self.stdout.write(self.style.WARNING("Aborting"))
