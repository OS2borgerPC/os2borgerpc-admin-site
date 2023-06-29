from django.core.management.base import BaseCommand
from system.models import Site, PC
from datetime import datetime


class Command(BaseCommand):
    help = "Check if any notifications need to be sent"

    def handle(self, *args, **options):
        # PCS = relevant_object.pcs.exclude(recently_online=False)
        # now = datetime.now()
        # for pc in PCS:
        #     if (now - pc.last_seen).seconds > offline_timer:
        #         pc.recently_online = False
        #         pc.save()

        sites = Site.objects.all()
        for site in sites:
            print(site.name)
        test = PC.objects.last()
        test.name = "haha"
        test.save()
