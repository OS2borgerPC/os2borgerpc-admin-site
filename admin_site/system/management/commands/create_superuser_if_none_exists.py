from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from account.models import UserProfile

class Command(BaseCommand):

    """

    Create a superuser if none exist

    Example:

        manage.py createsuperuser_if_none_exists --usernarme admin --password changeme --email admin@test.com

    """

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)
        parser.add_argument("--password", required=True)
        parser.add_argument("--email", required=True)

    def handle(self, *args, **options):
        if User.objects.filter(is_superuser=True).exists():
            return
        username = options["username"]
        admin = User.objects.create_superuser(username=username, password=options["password"], email=options["email"])
        UserProfile.objects.create(user=admin)