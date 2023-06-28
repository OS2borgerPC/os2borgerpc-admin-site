from django.core.management.base import BaseCommand
from system.models import Site, PC
from datetime import datetime


class Command(BaseCommand):
    help = "Check if any notifications need to be sent"

    def handle(self, *args, **options):
        sites = Site.objects.all()
        for site in sites:
            print(site.name)
        test = PC.objects.last()
        test.name = "haha"
        test.save()
