from django.db import models
from django.utils.translation import ugettext_lazy as _


class AuditModelMixin(models.Model):
    """Mixin for tracking created/modified datetime and user."""

    created = models.DateTimeField(
        auto_now_add=True, null=True, verbose_name=_("created")
    )
    modified = models.DateTimeField(
        auto_now=True, null=True, verbose_name=_("modified")
    )

    user_created = models.CharField(
        blank=True,
        max_length=128,
        editable=False,
        verbose_name=_("created by user"),
    )
    user_modified = models.CharField(
        blank=True,
        max_length=128,
        editable=False,
        verbose_name=_("last modified by user"),
    )

    class Meta:
        abstract = True
