from django.db import models

from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib.auth.models import User

from markdownx.utils import markdownify
from markdownx.models import MarkdownxField


# A model to sort Changelog entries into categories
class ChangelogTag(models.Model):
    name = models.CharField(verbose_name=_("name"), max_length=255)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


# A model that represents one changelog entry, used to showcase changes/new features to users
class Changelog(models.Model):
    title = models.CharField(verbose_name=_("title"), max_length=100)
    description = models.TextField(verbose_name=_("description"), max_length=240)
    content = MarkdownxField(verbose_name=_("content"))
    tags = models.ManyToManyField(ChangelogTag, related_name="changelogs", blank=True)
    created = models.DateTimeField(verbose_name=_("created"), default=timezone.now)
    updated = models.DateTimeField(verbose_name=_("updated"), default=timezone.now)
    published = models.BooleanField(verbose_name=_("published (visible)"), default=True)

    def get_tags(self):
        return self.tags.values("name", "pk")

    def render_content(self):
        # This method returns the markdown text of the 'content' field as html code.
        return markdownify(self.content)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ["-created"]


class ChangelogComment(models.Model):
    content = models.TextField(verbose_name=_("content"), max_length=240)
    created = models.DateTimeField(
        verbose_name=_("created"), editable=False, auto_now_add=True
    )
    changelog = models.ForeignKey(
        Changelog, related_name="comments", on_delete=models.CASCADE, null=True
    )
    user = models.ForeignKey(User, related_name="comments", on_delete=models.CASCADE)
    parent_comment = models.ForeignKey(
        "self",
        default=None,
        null=True,
        blank=True,
        related_name="comment_children",
        on_delete=models.CASCADE,
    )

    def get_user(self):
        if self.user:
            return User.objects.get(pk=self.user)

    class Meta:
        ordering = ["created"]
