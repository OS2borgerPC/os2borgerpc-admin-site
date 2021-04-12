from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User

from system.models import Site


class UserProfile(models.Model):
    """BibOS Admin specific user profile."""
    # This is the user to which the profile belongs
    user = models.OneToOneField(User, unique=True,
                                related_name='bibos_profile',
                                on_delete=models.CASCADE)

    sites = models.ManyToManyField(
        Site, through='SiteMembership', related_name="user_profiles"
    )
    # TODO: Add more fields/user options as needed.
    # TODO: Make before_save integrity check that SITE_USER and
    # SITE_ADMIN users MUST be associated with a site.

    def __str__(self):
        return self.user.username

    def clean(self):
        from django.core.exceptions import ValidationError

        if not self.user.is_superuser and not self.sites.exists():
            raise ValidationError(_(
                'Non-admin users MUST be attached to a site'
            ))


class SiteMembership(models.Model):
    SITE_USER = 1
    SITE_ADMIN = 2
    type_choices = (
        (SITE_USER, _("Site User")),
        (SITE_ADMIN, _("Site Admin"))
    )

    # The choices that can be used on the non-admin part of the website
    NON_ADMIN_CHOICES = (
        (SITE_USER, _("Site User")),
        (SITE_ADMIN, _("Site Admin"))
    )

    site_user_type = models.IntegerField(
        choices=type_choices, default=SITE_USER
    )

    site = models.ForeignKey(Site, on_delete=models.CASCADE)
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user_profile} - {self.site}"

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=["site", "user_profile"],
            name="unique_site_user_profile")
        ]
