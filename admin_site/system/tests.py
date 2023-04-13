"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

import os

from django.conf import settings
from django.test import TestCase

from django.core.mail import EmailMessage
from django.contrib.auth.models import User
from account.models import UserProfile

print("FILE", os.path.dirname(__file__))

parent_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


# setup account_userprofile, auth_user, securityproblem
class SimpleTest(TestCase):
    def setUp(self):
        site_user = User.objects.create_superuser(
            "danni", "danni@magenta-aps.dk", "hejsa"
        )
        test_user = User.objects.create_superuser(
            "test", "test@magenta-aps.dk", "hejsa"
        )
        # security_problem = SecurityProblem.objects.create(name='Keyboard',
        # uid='KEYBOARD', description='Usb keyboard added.',
        # level='High', script_id=1, site_id=1)
        UserProfile.objects.create(user=site_user)
        UserProfile.objects.create(user=test_user)

    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

    def test_notify_user(self):
        data = "KEYBOARD, Summary, Raw data"
        split = data.split(",")
        email_list = []
        user_profiles = UserProfile.objects.all()
        for up in user_profiles:
            if up.user.email is not None:
                email_list.append(User.objects.get(id=up.user_id).email)

        message = EmailMessage(split[0], split[1], settings.ADMIN_EMAIL, email_list)

        self.assertEqual(len(email_list), 2)
        self.assertEqual(message.send(), 1)
