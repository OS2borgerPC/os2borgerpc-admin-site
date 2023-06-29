from django.shortcuts import render

from changelog.models import (
    Changelog,
    ChangelogComment,
    ChangelogTag,
)

from django.core.paginator import Paginator
from django.views.generic import ListView, View
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

# Mixin class to require login - copied from system app
class LoginRequiredMixin(View):
    """Subclass in all views where login is required."""

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(LoginRequiredMixin, self).dispatch(*args, **kwargs)


class ChangelogListView(ListView):
    template_name = "list.html"

    def get_queryset(self, filter=None):
        if filter:
            return Changelog.objects.filter(
                Q(author__icontains=filter)
                | Q(title__icontains=filter)
                | Q(content__icontains=filter)
                | Q(description__icontains=filter)
                | Q(version__icontains=filter)
            )
        return Changelog.objects.all()

    def get_paginated_queryset(self, queryset, page):
        if not page:
            page = 1

        paginator = Paginator(queryset, 5)
        page_obj = paginator.get_page(page)

        return page_obj

    def get_context_data(self, **kwargs):
        context = super(ChangelogListView, self).get_context_data(**kwargs)

        context["tag_choices"] = ChangelogTag.objects.values("name", "pk")

        context["page"] = self.request.GET.get("page")

        # Get the search query (if any) and filter the queryset based on that
        search_query = self.request.GET.get("search")

        if search_query:
            queryset = self.get_queryset(search_query)
            context["search_query"] = search_query
        else:
            queryset = self.get_queryset()

        # Get the tag filter (if any) and filter the queryset accordingly
        context["tag_filter"] = self.request.GET.get("tag")

        if context["tag_filter"]:
            context["tag_filter"] = ChangelogTag.objects.get(pk=context["tag_filter"])
            queryset = queryset.filter(tags=context["tag_filter"])

        # Paginate the queryset and add it to the context
        context["entries"] = self.get_paginated_queryset(queryset, context["page"])

        # Add all comments that belong to the entries on the current page to the
        # context
        context["comments"] = ChangelogComment.objects.filter(
            Q(changelog__in=context["entries"].object_list) & Q(parent_comment=None)
        ).order_by("-created")

        return context

    def post(self, request, *args, **kwargs):
        req = request.POST

        comment = ChangelogComment()

        comment.user = get_object_or_404(User, pk=req["user"])
        comment.changelog = get_object_or_404(Changelog, pk=req["changelog"])
        comment.content = req["content"]

        if req["parent_comment"] != "None":
            comment.parent_comment = get_object_or_404(
                ChangelogComment, pk=req["parent_comment"]
            )

        comment.save()

        return redirect("changelogs")
