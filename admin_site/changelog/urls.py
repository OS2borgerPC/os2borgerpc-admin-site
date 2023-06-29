from django.urls import re_path

from changelog.views import (
    ChangelogListView,
)

urlpatterns = [
    re_path(
        r"^$",
        ChangelogListView.as_view(),
        name="changelogs",
    ),
]
