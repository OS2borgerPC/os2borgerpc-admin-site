from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from account.models import UserProfile, SiteMembership
from system.models import Site, Configuration, Customer, Country, FeaturePermission

class Command(BaseCommand):

    """

    Create a superuser if none exist. Also creates a default site, and assigns the superuser as a customer admin to this site.

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
        user_profile = UserProfile.objects.create(user=admin)

        # Create a default site for the superuser
        configuration = Configuration.objects.create(name="default")

        country = Country.objects.create(name="Default")
        customer = Customer.objects.create(
                name="Default",
                country=country,
                is_test=False
            )

        site = Site.objects.create(
            name="Default",
            uid="default",
            configuration=configuration,
            customer=customer
        )

        SiteMembership.objects.create(
            site=site,
            user_profile=user_profile,
            site_user_type=SiteMembership.CUSTOMER_ADMIN
        )

        # Create and add permission to edit the wake/sleep time plan from the admin-site UI
        featurePermission = FeaturePermission.objects.create(
            name="Default",
            uid="wake_plan"
        )
        featurePermission.customers.add(customer)