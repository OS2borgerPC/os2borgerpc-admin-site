from django.core.management.base import BaseCommand
from system.models import SecurityEvent, Citizen
from datetime import datetime, timedelta


class Command(BaseCommand):
    help = "Remove old unnecessary database objects"

    def handle(self, *args, **options):
        """Remove security events older than a year and citizens whose last successful login
        was more than two days ago"""

        now = datetime.now()
        a_year_ago = now - timedelta(days=365)
        two_days_ago = now - timedelta(days=2)

        # Delete old security events
        SecurityEvent.objects.filter(reported_time__lt=a_year_ago).delete()
        # Delete old citizen objects
        Citizen.objects.filter(last_successful_login__lt=two_days_ago).delete()
