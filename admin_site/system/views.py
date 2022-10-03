# -*- coding: utf-8 -*-
import os
import json
from datetime import datetime
from functools import cmp_to_key
from re import search
from urllib.parse import quote

from django.http import HttpResponseRedirect, Http404, JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import dateformat
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.utils.translation import gettext
from django.contrib.auth.models import User
from django.urls import reverse

from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic import View, ListView, DetailView, RedirectView, TemplateView
from django.views.generic.list import BaseListView

from django.db import transaction
from django.db.models import Q, F
from django.db.models.functions import Lower
from django.conf import settings

from django.core.paginator import Paginator

from account.models import (
    UserProfile,
    SiteMembership,
)

from system.models import (
    ChangelogTag,
    Site,
    PC,
    PCGroup,
    ConfigurationEntry,
    Job,
    Script,
    Input,
    SecurityProblem,
    SecurityEvent,
    MandatoryParameterMissingError,
    ImageVersion,
    ScriptTag,
    AssociatedScriptParameter,
    Changelog,
    ChangelogComment,
)

# PC Status codes
from system.forms import (
    SiteForm,
    PCGroupForm,
    ConfigurationEntryForm,
    ScriptForm,
    UserForm,
    ParameterForm,
    PCForm,
    SecurityProblemForm,
    ChangelogCommentForm,
    SecurityEventForm,
)


def set_notification_cookie(response, message, error=False):
    descriptor = {"message": message, "type": "success" if not error else "error"}

    response.set_cookie("bibos-notification", quote(json.dumps(descriptor), safe=""))


# Mixin class to require login
class LoginRequiredMixin(View):
    """Subclass in all views where login is required."""

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(LoginRequiredMixin, self).dispatch(*args, **kwargs)


class SuperAdminOnlyMixin(View):
    """Only allows access to super admins."""

    check_function = user_passes_test(lambda u: u.is_superuser, login_url="/")

    @method_decorator(login_required)
    @method_decorator(check_function)
    def dispatch(self, *args, **kwargs):
        return super(SuperAdminOnlyMixin, self).dispatch(*args, **kwargs)


class SuperAdminOrThisSiteMixin(View):
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        """Limit access to super users or users belonging to THIS site."""
        site = None
        slug_field = None
        # Find out which field is used as site slug
        if "site_uid" in kwargs:
            slug_field = "site_uid"
        elif "slug" in kwargs:
            slug_field = "slug"
        # If none given, give up
        if slug_field:
            site = get_object_or_404(Site, uid=kwargs[slug_field])
        check_function = user_passes_test(
            lambda u: (u.is_superuser)
            or (site and site in u.bibos_profile.sites.all()),
            login_url="/",
        )
        wrapped_super = check_function(super(SuperAdminOrThisSiteMixin, self).dispatch)
        return wrapped_super(*args, **kwargs)


# Mixin class for list selection (single select).
class SelectionMixin(View):
    """This supplies the ability to highlight a selected object of a given
    class. This is useful if a Detail view contains a list of children which
    the user is allowed to select."""

    # The Python class of the Django model corresponding to the objects you
    # want to be able to select. MUST be specified in subclass.
    selection_class = None
    # A callable which will return a list of objects which SHOULD belong to the
    # class specified by selection_class. MUST be specified in subclass.
    get_list = None
    # The field which is used to look up the selected object.
    lookup_field = "uid"
    # Overrides the default class name in context.
    class_display_name = None

    def get_context_data(self, **kwargs):
        # First, call superclass
        context = super(SelectionMixin, self).get_context_data(**kwargs)
        # Then get selected object, if any
        if self.lookup_field in self.kwargs:
            lookup_val = self.kwargs[self.lookup_field]
            lookup_params = {self.lookup_field: lookup_val}
            selected = get_object_or_404(self.selection_class, **lookup_params)
        else:
            selected = self.get_list()[0] if self.get_list() else None

        display_name = (
            self.class_display_name
            if self.class_display_name
            else self.selection_class.__name__.lower()
        )
        if selected is not None:
            context["selected_{0}".format(display_name)] = selected
        context["{0}_list".format(display_name)] = self.get_list()
        return context


class JSONResponseMixin:
    """
    A mixin that can be used to render a JSON response.
    """

    def render_to_json_response(self, context, **response_kwargs):
        """
        Returns a JSON response, transforming 'context' to make the payload.
        """
        return JsonResponse(self.get_data(context), **response_kwargs)

    def get_data(self, context):
        """
        Returns an object that will be serialized as JSON by json.dumps().
        """
        # Note: This is *EXTREMELY* naive; in reality, you'll need
        # to do much more complex handling to ensure that arbitrary
        # objects -- such as Django model instances or querysets
        # -- can be serialized as JSON.
        return context


# Mixin class for CRUD views that use site_uid in URL
# The "site_uid" slug is configurable, but please avoid clashes
class SiteMixin(View):
    """Mixin class to extract site UID from URL"""

    site_uid = "site_uid"

    def get_context_data(self, **kwargs):
        context = super(SiteMixin, self).get_context_data(**kwargs)
        site = get_object_or_404(Site, uid=self.kwargs[self.site_uid])
        context["site"] = site
        # Add information about outstanding security events.
        no_of_sec_events = SecurityEvent.objects.priority_events_for_site(site).count()
        context["sec_events"] = no_of_sec_events

        return context


# Main index/site root view
class AdminIndex(RedirectView, LoginRequiredMixin):
    """Redirects to admin overview (sites list) or site main page."""

    def get_redirect_url(self, **kwargs):
        """Redirect based on user. This view will use the RequireLogin mixin,
        so we'll always have a logged-in user."""
        user = self.request.user
        profile = user.bibos_profile

        # If user only has one site, redirect to that.
        if profile.sites.count() == 1:
            site = profile.sites.first()
            return reverse("site", kwargs={"slug": site.url})
        # In all other cases we can redirect to list of sites.
        return reverse("sites")


class SiteList(ListView, LoginRequiredMixin):
    """
    Site overview.

    Provides a list of sites a user has access to.
    """

    model = Site
    context_object_name = "site_list"

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            qs = Site.objects.all()
        else:
            qs = user.bibos_profile.sites.all()
        return qs

    def get_context_data(self, **kwargs):
        context = super(SiteList, self).get_context_data(**kwargs)
        context["pcs_count"] = PC.objects.filter(site__in=self.get_queryset()).count()
        context["user"] = self.request.user
        return context


# Base class for Site-based passive (non-form) views
class SiteView(DetailView, SuperAdminOrThisSiteMixin):
    """Base class for all views based on a single site."""

    model = Site
    slug_field = "uid"

    def get_context_data(self, **kwargs):
        context = super(SiteView, self).get_context_data(**kwargs)
        site = self.get_object()
        # Add information about outstanding security events.
        no_of_sec_events = SecurityEvent.objects.priority_events_for_site(site).count()
        context["sec_events"] = no_of_sec_events

        return context


class SiteDetailView(SiteView):
    """Class for showing the overview that is displayed when entering a site"""

    template_name = "system/site_status.html"

    # For hver pc skal vi hente seneste security event.
    def get_context_data(self, **kwargs):
        context = super(SiteDetailView, self).get_context_data(**kwargs)
        # Top level list of new PCs etc.
        not_activated_pcs = self.object.pcs.filter(is_activated=False)

        site = context["site"]
        site_pcs = site.pcs.all()
        context["ls_pcs"] = site_pcs.order_by(
            "is_activated", F("last_seen").desc(nulls_last=True)
        )

        context["total_pcs"] = context["ls_pcs"].count()
        context["activated_pcs"] = context["total_pcs"] - not_activated_pcs.count()
        activated_pcs = site_pcs.filter(is_activated=True)
        context["online_pcs"] = len([pc for pc in activated_pcs if pc.online])

        return context


class SiteSettings(UpdateView, SiteView):
    form_class = SiteForm
    template_name = "system/site_settings.html"

    def get_context_data(self, **kwargs):
        # First, get basic context from superclass
        context = super(SiteSettings, self).get_context_data(**kwargs)
        context["site_configs"] = self.object.configuration.entries.all()

        return context

    def post(self, request, *args, **kwargs):
        # Do basic method
        kwargs["updated"] = True
        response = self.get(request, *args, **kwargs)

        # Handle saving of site settings data
        super(SiteSettings, self).post(request, *args, **kwargs)

        # Handle saving of site configs data
        self.object.configuration.update_from_request(request.POST, "site_configs")

        set_notification_cookie(response, _("Settings for %s updated") % kwargs["slug"])
        return response


class TwoFactor(SiteView, SuperAdminOrThisSiteMixin, SiteMixin):
    template_name = "system/site_two_factor.html"


# Now follows all site-based views, i.e. subclasses
# of SiteView.
class JobsView(SiteView):
    template_name = "system/site_jobs.html"

    def get_context_data(self, **kwargs):
        # First, get basic context from superclass
        context = super(JobsView, self).get_context_data(**kwargs)
        site = context["site"]
        context["batches"] = site.batches.all()[:100]
        context["pcs"] = site.pcs.all()
        context["groups"] = site.groups.all()
        preselected = set(
            [
                Job.NEW,
                Job.SUBMITTED,
                Job.RUNNING,
                Job.FAILED,
                Job.DONE,
            ]
        )
        context["status_choices"] = [
            {
                "name": name,
                "value": value,
                "label": Job.STATUS_TO_LABEL[value],
                "checked": 'checked="checked' if value in preselected else "",
            }
            for (value, name) in Job.STATUS_CHOICES
        ]
        params = self.request.GET or self.request.POST

        for k in ["batch", "pc", "group"]:
            v = params.get(k, None)
            if v is not None and v.isdigit():
                context["selected_%s" % k] = int(v)

        return context


class JobSearch(SiteMixin, JSONResponseMixin, BaseListView, SuperAdminOrThisSiteMixin):
    paginate_by = 20
    http_method_names = ["get"]
    VALID_ORDER_BY = []
    for i in [
        "pk",
        "batch__script__name",
        "created",
        "started",
        "finished",
        "status",
        "pc__name",
        "batch__name",
        "user__username",
    ]:
        VALID_ORDER_BY.append(i)
        VALID_ORDER_BY.append("-" + i)

    context_object_name = "jobs_list"

    def render_to_response(self, context, **response_kwargs):
        return self.render_to_json_response(context, **response_kwargs)

    def get_queryset(self):
        site = get_object_or_404(Site, uid=self.kwargs[self.site_uid])
        queryset = Job.objects.all()
        params = self.request.GET

        query = {"batch__site": site}

        if "status" in params:
            query["status__in"] = params.getlist("status")

        for k in ["pc", "batch"]:
            v = params.get(k, "")
            if v != "":
                query[k] = v

        group = params.get("group", "")
        if group != "":
            query["pc__pc_groups"] = group

        orderby = params.get("orderby", "-pk")
        if orderby not in JobSearch.VALID_ORDER_BY:
            orderby = "-pk"

        queryset = queryset.filter(**query).order_by(orderby, "pk")

        return queryset

    # for admin users the user_url is a redirect to our job docs
    # explaining scripts run as "Magenta"
    def get_username(self, user):
        if user:
            if user and user.is_superuser:
                return "Magenta"
            else:
                return user.username
        else:
            return ""

    def get_user_url(self, user, uid):
        if user:
            if user.is_superuser:
                return reverse("doc", kwargs={"name": "jobs"})
            else:
                return (reverse("user", args=[uid, user.username]),)
        else:
            return ""

    def get_data(self, context):
        site = context["site"]
        page_obj = context["page_obj"]
        paginator = context["paginator"]
        adjacent_pages = 2
        page_numbers = [
            n
            for n in range(
                page_obj.number - adjacent_pages, page_obj.number + adjacent_pages + 1
            )
            if n > 0 and n <= paginator.num_pages
        ]

        page = {
            "count": paginator.count,
            "num_pages": paginator.num_pages,
            "page": page_obj.number,
            "page_numbers": page_numbers,
            "has_next": page_obj.has_next(),
            "next_page_number": (
                page_obj.next_page_number() if page_obj.has_next() else None
            ),
            "has_previous": page_obj.has_previous(),
            "previous_page_number": (
                page_obj.previous_page_number() if page_obj.has_previous() else None
            ),
            "results": [
                {
                    "pk": job.pk,
                    "script_name": job.batch.script.name,
                    "started": job.started.strftime("%Y-%m-%d %H:%M:%S")
                    if job.started
                    else "-",
                    "finished": job.finished.strftime("%Y-%m-%d %H:%M:%S")
                    if job.finished
                    else "-",
                    "created": job.created.strftime("%Y-%m-%d %H:%M:%S")
                    if job.created
                    else "-",
                    "status": job.status_translated + "",
                    "label": job.status_label,
                    "pc_name": job.pc.name,
                    "batch_name": job.batch.name,
                    "user": self.get_username(job.user),
                    "user_url": self.get_user_url(job.user, site.uid),
                    "has_info": job.has_info,
                    "script_url": reverse(
                        "script", args=[site.uid, job.batch.script.id]
                    ),
                    "pc_url": reverse("computer", args=[site.uid, job.pc.uid]),
                    "restart_url": reverse("restart_job", args=[site.uid, job.pk]),
                }
                for job in page_obj
            ],
        }

        return page


class JobRestarter(DetailView, SuperAdminOrThisSiteMixin):
    template_name = "system/jobs/restart.html"
    model = Job

    def status_fail_response(self):
        response = HttpResponseRedirect(self.get_success_url())
        set_notification_cookie(
            response, _("Can only restart jobs with status %s") % Job.FAILED
        )
        return response

    def get(self, request, *args, **kwargs):
        self.site = get_object_or_404(Site, uid=kwargs["site_uid"])
        self.object = self.get_object()

        # Only restart jobs that have failed
        if self.object.status != Job.FAILED:
            return self.status_fail_response()

        context = self.get_context_data(object=self.object)

        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super(JobRestarter, self).get_context_data(**kwargs)
        context["site"] = self.site
        context["selected_job"] = self.object
        return context

    def post(self, request, *args, **kwargs):
        self.site = get_object_or_404(Site, uid=kwargs["site_uid"])
        self.object = self.get_object()

        if self.object.status != Job.FAILED:
            return self.status_fail_response()

        self.object.restart(user=self.request.user)
        response = HttpResponseRedirect(self.get_success_url())
        set_notification_cookie(
            response,
            _("The script %s is being rerun on the computer %s")
            % (self.object.batch.script.name, self.object.pc.name),
        )
        return response

    def get_success_url(self):
        return "/site/%s/jobs/" % self.kwargs["site_uid"]


class JobInfo(DetailView, LoginRequiredMixin):
    template_name = "system/jobs/info.html"
    model = Job

    def get(self, request, *args, **kwargs):
        self.site = get_object_or_404(Site, uid=kwargs["site_uid"])
        return super(JobInfo, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(JobInfo, self).get_context_data(**kwargs)
        if self.site != self.object.batch.site:
            raise Http404
        context["site"] = self.site
        context["job"] = self.object
        return context


class ScriptMixin(object):
    script = None
    script_inputs = ""
    is_security = False

    def setup_script_editing(self, **kwargs):
        # Get site
        self.site = get_object_or_404(Site, uid=kwargs["slug"])
        # Add the global and local script lists
        self.scripts = Script.objects.filter(
            Q(site=self.site) | Q(site=None), is_security_script=self.is_security
        )

        if "script_pk" in kwargs:
            self.script = get_object_or_404(Script, pk=kwargs["script_pk"])
            if self.script.site and self.script.site != self.site:
                raise Http404(f"Du har intet script med id {self.kwargs['script_pk']}")

    def get(self, request, *args, **kwargs):
        self.setup_script_editing(**kwargs)
        return super(ScriptMixin, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.setup_script_editing(**kwargs)
        return super(ScriptMixin, self).post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        # Get context from super class
        context = super(ScriptMixin, self).get_context_data(**kwargs)
        context["site"] = self.site
        context["script_tags"] = ScriptTag.objects.all()

        local_scripts = self.scripts.filter(site=self.site).order_by(Lower("name"))
        context["local_scripts"] = local_scripts
        global_scripts = self.scripts.filter(site=None).order_by(Lower("name"))
        context["global_scripts"] = global_scripts

        # Create a tag->scripts dict for tags that has local scripts.
        local_tag_scripts_dict = {
            tag: local_scripts.filter(tags=tag)
            for tag in ScriptTag.objects.all()
            if local_scripts.filter(tags=tag).exists()
        }
        # Add scripts with no tags as untagged.
        if local_scripts.filter(tags=None).exists():
            local_tag_scripts_dict["untagged"] = local_scripts.filter(tags=None)

        context["local_scripts_by_tag"] = local_tag_scripts_dict

        # Create a tag->scripts dict for tags that has global scripts.
        global_tag_scripts_dict = {
            tag: global_scripts.filter(tags=tag)
            for tag in ScriptTag.objects.all()
            if global_scripts.filter(tags=tag).exists()
        }
        # Add scripts with no tags as untagged.
        if global_scripts.filter(tags=None).exists():
            global_tag_scripts_dict["untagged"] = global_scripts.filter(tags=None)

        context["global_scripts_by_tag"] = global_tag_scripts_dict

        context["script_inputs"] = self.script_inputs
        context["is_security"] = self.is_security
        if self.is_security:
            context["script_url"] = "security_script"
        else:
            context["script_url"] = "script"

        # If we selected a script add it to context
        if self.script is not None:
            context["selected_script"] = self.script
            if self.script.site is None:
                context["global_selected"] = True
            if not context["script_inputs"]:
                context["script_inputs"] = [
                    {
                        "pk": input.pk,
                        "name": input.name,
                        "value_type": input.value_type,
                        "mandatory": input.mandatory,
                    }
                    for input in self.script.ordered_inputs
                ]
        elif not context["script_inputs"]:
            context["script_inputs"] = []

        context["script_inputs_json"] = json.dumps(context["script_inputs"])
        # Add information about outstanding security events.
        no_of_sec_events = SecurityEvent.objects.priority_events_for_site(
            self.site
        ).count()
        context["sec_events"] = no_of_sec_events

        return context

    def validate_script_inputs(self):
        params = self.request.POST
        num_inputs = params.get("script-number-of-inputs", 0)
        inputs = []
        success = True
        if int(num_inputs) > 0:
            for i in range(int(num_inputs)):
                data = {
                    "pk": params.get("script-input-%d-pk" % i, None),
                    "name": params.get("script-input-%d-name" % i, ""),
                    "value_type": params.get("script-input-%d-type" % i, ""),
                    "position": i,
                    "mandatory": params.get(
                        "script-input-%d-mandatory" % i, "unchecked"
                    ),
                }

                if data["name"] is None or data["name"] == "":
                    data["name_error"] = "Fejl: Du skal angive et navn"
                    success = False

                if data["value_type"] not in [
                    value for (value, name) in Input.VALUE_CHOICES
                ]:
                    data["type_error"] = "Fejl: Du skal angive en korrekt type"
                    success = False

                data["mandatory"] = data["mandatory"] != "unchecked"

                inputs.append(data)

            self.script_inputs = inputs

        return success

    def save_script_inputs(self):
        # First delete the existing inputs not found in the new inputs.
        pks = [
            script_input.get("pk")
            for script_input in self.script_inputs
            if script_input.get("pk")
        ]
        self.script.inputs.exclude(pk__in=pks).delete()

        for input_data in self.script_inputs:
            input_data["script"] = self.script

            if "pk" in input_data and not input_data["pk"]:
                del input_data["pk"]

            Input.objects.update_or_create(pk=input_data.get("pk"), defaults=input_data)

    def create_associated_script_parameters(self):
        for associated_script in self.script.associations.all():
            for script_input in self.script.ordered_inputs:
                par = AssociatedScriptParameter.objects.filter(
                    associated_script=associated_script, input=script_input
                ).first()
                if not par:
                    par = AssociatedScriptParameter(
                        associated_script=associated_script, input=script_input
                    )
                    par.save()


class ScriptList(ScriptMixin, SiteView):
    def get(self, request, *args, **kwargs):
        self.setup_script_editing(**kwargs)
        try:
            # Sort by -site followed by lowercased name
            def sort_by(a, b):
                if a.site == b.site:
                    # cmp deprecated: cmp(a, b) has been changed to
                    # the ((a > b) - (a < b)) formats
                    return (a.name.lower() > b.name.lower()) - (
                        a.name.lower() < b.name.lower()
                    )
                else:
                    if b.site is not None:
                        return 1
                    else:
                        return -1

            # cmp deprecated: cmp converted to key function
            script = sorted(self.scripts, key=cmp_to_key(sort_by))[0]
            return HttpResponseRedirect(script.get_absolute_url(site_uid=self.site.uid))

        except IndexError:
            return HttpResponseRedirect(
                reverse("new_security_script", args=[self.site.uid])
                if self.is_security
                else reverse("new_script", args=[self.site.uid])
            )


class ScriptCreate(ScriptMixin, CreateView, SuperAdminOrThisSiteMixin):
    template_name = "system/scripts/create.html"
    form_class = ScriptForm

    def get_context_data(self, **kwargs):
        context = super(ScriptCreate, self).get_context_data(**kwargs)
        context["type_choices"] = Input.VALUE_CHOICES
        return context

    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.get_form_class()
        form = super(ScriptCreate, self).get_form(form_class)
        form.prefix = "create"
        return form

    def form_valid(self, form):
        if self.validate_script_inputs():
            # save the username for the AuditModelMixin.
            form.instance.user_created = self.request.user.username
            self.object = form.save()
            self.script = self.object
            if self.is_security:
                self.object.is_security_script = True
                self.object.save()
            self.save_script_inputs()
            return HttpResponseRedirect(self.get_success_url())
        else:
            return self.form_invalid(form, transfer_inputs=False)

    def form_invalid(self, form, transfer_inputs=True):
        if transfer_inputs:
            self.validate_script_inputs()

        return super(ScriptCreate, self).form_invalid(form)

    def get_success_url(self):
        if self.is_security:
            return reverse("security_script", args=[self.site.uid, self.script.pk])
        else:
            return reverse("script", args=[self.site.uid, self.script.pk])


class ScriptUpdate(ScriptMixin, UpdateView, SuperAdminOrThisSiteMixin):
    template_name = "system/scripts/update.html"
    form_class = ScriptForm

    def get_context_data(self, **kwargs):
        # Get context from super class
        context = super(ScriptUpdate, self).get_context_data(**kwargs)
        if self.script is not None and self.script.executable_code is not None:
            try:
                display_code = self.script.executable_code.read().decode("utf-8")
            except UnicodeDecodeError:
                display_code = "<Kan ikke vise koden - binære data.>"
            except FileNotFoundError:
                display_code = "<Kan ikke vise koden - upload venligst igen.>"
            context["script_preview"] = display_code
        context["type_choices"] = Input.VALUE_CHOICES
        self.create_form = ScriptForm()
        self.create_form.prefix = "create"
        context["create_form"] = self.create_form
        request_user = self.request.user
        site = get_object_or_404(Site, uid=self.kwargs["slug"])
        if not request_user.is_superuser:
            context[
                "user_type_for_site"
            ] = request_user.bibos_profile.sitemembership_set.get(
                site_id=site.id
            ).site_user_type
        return context

    def get_object(self, queryset=None):
        return self.script

    def form_valid(self, form):
        if self.validate_script_inputs():
            # save the username for the AuditModelMixin.
            form.instance.user_modified = self.request.user.username
            self.save_script_inputs()
            self.create_associated_script_parameters()
            response = super(ScriptUpdate, self).form_valid(form)
            set_notification_cookie(response, _("Script %s updated") % self.script.name)

            return response
        else:
            return self.form_invalid(form, transfer_inputs=False)

    def form_invalid(self, form, transfer_inputs=True):
        if transfer_inputs:
            self.validate_script_inputs()

        return super(ScriptUpdate, self).form_invalid(form)

    def get_success_url(self):
        if self.is_security:
            return reverse("security_script", args=[self.site.uid, self.script.pk])
        else:
            return reverse("script", args=[self.site.uid, self.script.pk])


class ScriptRun(SiteView):
    action = None
    form = None
    STEP1 = "choose_pcs_and_groups"
    STEP2 = "choose_parameters"
    STEP3 = "run_script"

    def post(self, request, *args, **kwargs):
        return super(ScriptRun, self).get(request, *args, **kwargs)

    def fetch_pcs_from_request(self):
        # Transfer chosen groups and PCs as PC pks
        pcs = [int(pk) for pk in self.request.POST.getlist("pcs", [])]
        for group_pk in self.request.POST.getlist("groups", []):
            group = PCGroup.objects.get(pk=group_pk)
            for pc in group.pcs.all():
                pcs.append(int(pc.pk))
        # Uniquify
        selected_pcs_groups_set = list(set(pcs))
        return (selected_pcs_groups_set, len(selected_pcs_groups_set))

    def step1(self, context):
        self.template_name = "system/scripts/run_step1.html"
        context["pcs"] = self.object.pcs.all().order_by("name")
        all_groups = self.object.groups.all().order_by("name")
        context["groups"] = [group for group in all_groups if group.pcs.count() > 0]

        if len(context["script"].ordered_inputs) > 0:
            context["action"] = ScriptRun.STEP2
        else:
            context["action"] = ScriptRun.STEP3

    def step2(self, context):
        self.template_name = "system/scripts/run_step2.html"

        context["pcs"], context["num_pcs"] = self.fetch_pcs_from_request()
        if context["num_pcs"] == 0:
            context["message"] = _("You must specify at least one group or pc")
            self.step1(context)
            return

        # Set up the form
        if "form" not in context:
            context["form"] = ParameterForm(script=context["script"])

        # Go to step3 on submit
        context["action"] = ScriptRun.STEP3

    def step3(self, context):
        self.template_name = "system/scripts/run_step3.html"
        form = ParameterForm(
            self.request.POST, self.request.FILES, script=context["script"]
        )
        context["form"] = form

        # When run in step 3 and step 2 wasn't bypassed, don't do this calculation again
        if "selected_pcs" not in context:
            context["selected_pcs"], context["num_pcs"] = self.fetch_pcs_from_request()
        if context["num_pcs"] == 0:
            context["message"] = _("You must specify at least one group or pc")
            self.step1(context)
            return

        if not form.is_valid():
            self.step2(context)
        else:
            args = []
            for i in range(0, context["script"].inputs.count()):
                # Non-mandatory Integer and Date fields send "None", which causes an IntegrityError since string_value isn't null=True
                args.append(
                    ""
                    if form.cleaned_data[f"parameter_{i}"] is None
                    else form.cleaned_data[f"parameter_{i}"]
                )

            context["batch"] = context["script"].run_on(
                context["site"],
                PC.objects.filter(pk__in=context["selected_pcs"]),
                *args,
                user=self.request.user,
            )

    def get_context_data(self, **kwargs):
        context = super(ScriptRun, self).get_context_data(**kwargs)
        context["script"] = get_object_or_404(Script, pk=self.kwargs["script_pk"])

        action = self.request.POST.get("action", "choose_pcs_and_groups")
        if action == ScriptRun.STEP1:
            self.step1(context)
        elif action == ScriptRun.STEP2:
            self.step2(context)
        elif action == ScriptRun.STEP3:
            self.step3(context)
        else:
            raise Exception("POST to ScriptRun with wrong action %s" % self.action)

        return context


class ScriptDelete(ScriptMixin, SuperAdminOrThisSiteMixin, DeleteView):
    template_name = "system/scripts/confirm_delete.html"
    model = Script

    def get_object(self, queryset=None):
        return Script.objects.get(
            pk=self.kwargs["script_pk"], site__uid=self.kwargs["slug"]
        )

    def get_success_url(self):
        if self.is_security:
            return reverse("security_scripts", kwargs={"slug": self.kwargs["slug"]})
        else:
            return reverse("scripts", kwargs={"slug": self.kwargs["slug"]})

    @transaction.atomic
    def delete(self, request, *args, **kwargs):
        script = self.get_object()

        # Fetch the PCGroups for which it's an AssociatedScript before
        # we delete it from them
        # We create a list as the next command would change it
        scripts_pcgroups = list(PCGroup.objects.filter(policy__script=script))

        response = super(ScriptDelete, self).delete(request, *args, **kwargs)

        # For each of those groups update the script positions to avoid gaps
        for spcg in scripts_pcgroups:
            spcg.update_associated_script_positions()

        return response


class PCsView(SelectionMixin, SiteView, SuperAdminOrThisSiteMixin):

    template_name = "system/site_pcs.html"
    selection_class = PC

    def get_list(self):
        return (
            self.object.pcs.all()
            .extra(select={"lower_name": "lower(name)"})
            .order_by("lower_name")
        )

    def render_to_response(self, context):
        if "selected_pc" in context:
            return HttpResponseRedirect(
                "/site/%s/computers/%s/"
                % (context["site"].uid, context["selected_pc"].uid)
            )
        else:
            return super(PCsView, self).render_to_response(context)


class PCUpdate(SiteMixin, UpdateView, LoginRequiredMixin, SuperAdminOrThisSiteMixin):
    template_name = "system/pc_form.html"
    form_class = PCForm
    slug_field = "uid"

    VALID_ORDER_BY = []
    for i in [
        "pk",
        "batch__script__name",
        "started",
        "finished",
        "status",
        "batch__name",
    ]:
        VALID_ORDER_BY.append(i)
        VALID_ORDER_BY.append("-" + i)

    def get_object(self, queryset=None):
        try:
            site_id = Site.objects.get(uid=self.kwargs["site_uid"])
            return PC.objects.get(uid=self.kwargs["pc_uid"], site=site_id)
        except PC.DoesNotExist:
            raise Http404(f"Du har ingen computer med id {self.kwargs['pc_uid']}")

    def get_context_data(self, **kwargs):
        context = super(PCUpdate, self).get_context_data(**kwargs)

        site = context["site"]
        form = context["form"]
        pc = self.object
        params = self.request.GET or self.request.POST

        context["pc_list"] = (
            site.pcs.all()
            .extra(select={"lower_name": "lower(name)"})
            .order_by("lower_name")
        )

        group_set = site.groups.all()

        selected_group_ids = form["pc_groups"].value()
        # template picklist requires the form pk, name, url (u)id.
        context["available_groups"] = group_set.exclude(
            pk__in=selected_group_ids
        ).values_list("pk", "name", "pk")
        context["selected_groups"] = group_set.filter(
            pk__in=selected_group_ids
        ).values_list("pk", "name", "pk")

        orderby = params.get("orderby", "-pk")
        if orderby not in JobSearch.VALID_ORDER_BY:
            orderby = "-pk"
        context["joblist"] = pc.jobs.order_by("status", "pk").order_by(orderby, "pk")

        if orderby.startswith("-"):
            context["orderby_key"] = orderby[1:]
            context["orderby_direction"] = "desc"
        else:
            context["orderby_key"] = orderby
            context["orderby_direction"] = "asc"

        context["orderby_base_url"] = pc.get_absolute_url() + "?"

        context["selected_pc"] = pc

        context["security_event"] = pc.security_events.latest_event()
        context["has_security_events"] = (
            pc.security_events.exclude(status=SecurityEvent.RESOLVED)
            .exclude(problem__level=SecurityProblem.NORMAL)
            .count()
            > 0
        )

        return context

    def form_valid(self, form):
        pc = self.object
        groups_pre = set(pc.pc_groups.all())

        with transaction.atomic():
            pc.configuration.update_from_request(self.request.POST, "pc_config")
            response = super(PCUpdate, self).form_valid(form)

            # If this PC has joined any groups that have policies attached
            # to them, then run their scripts (first making sure that this
            # PC is capable of doing so!)
            groups_post = set(pc.pc_groups.all())
            new_groups = groups_post.difference(groups_pre)
            for g in new_groups:
                policy = g.ordered_policy
                if policy:
                    for asc in policy:
                        asc.run_on(self.request.user, [pc])

        set_notification_cookie(response, _("Computer %s updated") % pc.name)
        return response


class PCDelete(SiteMixin, SuperAdminOrThisSiteMixin, DeleteView):
    model = PC

    def get_object(self, queryset=None):
        return PC.objects.get(uid=self.kwargs["pc_uid"])

    def get_success_url(self):
        return "/site/{0}/computers/".format(self.kwargs["site_uid"])


class PCGroupsView(SelectionMixin, SiteView):
    template_name = "system/site_groups.html"
    selection_class = PCGroup
    class_display_name = "group"

    def get_list(self):
        return (
            self.object.groups.all()
            .extra(select={"lower_name": "lower(name)"})
            .order_by("lower_name")
        )

    def render_to_response(self, context):
        if "selected_group" in context:
            return HttpResponseRedirect(
                "/site/%s/groups/%s/"
                % (context["site"].uid, context["selected_group"].url)
            )
        else:
            return HttpResponseRedirect(
                "/site/%s/groups/new/" % context["site"].uid,
            )


class UsersView(SelectionMixin, SiteView):

    template_name = "system/site_users.html"
    selection_class = User
    lookup_field = "username"

    def get_list(self):
        return self.object.users

    def render_to_response(self, context):
        if "selected_user" in context:
            # Select your own user by default if you have a UserProfile on the site
            # Fx. relevant to password changes

            if context["site"] in self.request.user.bibos_profile.sites.all():
                user = self.request.user.username
            else:
                user = context["selected_user"].username
            return HttpResponseRedirect(
                "/site/%s/users/%s/" % (context["site"].uid, user)
            )
        else:
            return HttpResponseRedirect(
                "/site/%s/new_user/" % context["site"].uid,
            )


class UsersMixin(object):
    def add_site_to_context(self, context):
        self.site = get_object_or_404(Site, uid=self.kwargs["site_uid"])
        context["site"] = self.site
        return context

    def add_userlist_to_context(self, context):
        if "site" not in context:
            self.add_site_to_context(context)
        context["user_list"] = context["site"].users
        # Add information about outstanding security events.
        no_of_sec_events = SecurityEvent.objects.priority_events_for_site(
            self.site
        ).count()
        context["sec_events"] = no_of_sec_events
        return context


class UserCreate(CreateView, UsersMixin, SuperAdminOrThisSiteMixin):
    model = User
    form_class = UserForm
    lookup_field = "username"
    template_name = "system/users/create.html"

    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.get_form_class()
        form = super(UserCreate, self).get_form(form_class)
        form.prefix = "create"
        return form

    def get_context_data(self, **kwargs):
        context = super(UserCreate, self).get_context_data(**kwargs)
        self.add_userlist_to_context(context)
        return context

    def form_valid(self, form):
        site = get_object_or_404(Site, uid=self.kwargs["site_uid"])

        if (
            self.request.user.bibos_profile.sitemembership_set.get(
                site=site
            ).site_user_type
            == 2
            or self.request.user.is_superuser
        ):
            self.object = form.save()
            user_profile = UserProfile.objects.create(user=self.object)
            SiteMembership.objects.create(
                user_profile=user_profile,
                site=site,
                site_user_type=form.cleaned_data["usertype"],
            )
            result = super(UserCreate, self).form_valid(form)
            return result
        else:
            raise Exception("Not site-admin or superuser")

    def get_success_url(self):
        return "/site/%s/users/%s/" % (self.kwargs["site_uid"], self.object.username)


class UserUpdate(UpdateView, UsersMixin, SuperAdminOrThisSiteMixin):
    model = User
    form_class = UserForm
    template_name = "system/users/update.html"

    def get_object(self, queryset=None):
        try:
            self.selected_user = User.objects.get(username=self.kwargs["username"])
        except User.DoesNotExist:
            raise Http404(f"Du har ingen bruger med id {self.kwargs['username']}")
        return self.selected_user

    def get_context_data(self, **kwargs):
        self.context_object_name = "selected_user"
        context = super(UserUpdate, self).get_context_data(**kwargs)
        self.add_userlist_to_context(context)

        site = get_object_or_404(Site, uid=self.kwargs["site_uid"])

        request_user = self.request.user
        user_profile = request_user.bibos_profile
        site_membership = user_profile.sitemembership_set.filter(site=site).first()

        if site_membership:
            loginusertype = site_membership.site_user_type
        else:
            loginusertype = None

        context["selected_user"] = self.selected_user
        context["form"].setup_usertype_choices(loginusertype, request_user.is_superuser)

        context["create_form"] = UserForm(prefix="create")
        context["create_form"].setup_usertype_choices(
            loginusertype, request_user.is_superuser
        )
        if not request_user.is_superuser:
            context[
                "user_type_for_site"
            ] = request_user.bibos_profile.sitemembership_set.get(
                site_id=site.id
            ).site_user_type
        return context

    def get_form_kwargs(self):
        kwargs = super(UserUpdate, self).get_form_kwargs()
        site = get_object_or_404(Site, uid=self.kwargs["site_uid"])
        kwargs["site"] = site

        return kwargs

    def form_valid(self, form):
        self.object = form.save()

        site = get_object_or_404(Site, uid=self.kwargs["site_uid"])
        user_profile = self.object.bibos_profile

        site_membership = user_profile.sitemembership_set.get(
            site=site, user_profile=user_profile
        )

        site_membership.site_user_type = form.cleaned_data["usertype"]
        site_membership.save()
        response = super(UserUpdate, self).form_valid(form)
        set_notification_cookie(response, _("User %s updated") % self.object.username)
        return response

    def get_success_url(self):
        return "/site/%s/users/%s/" % (self.kwargs["site_uid"], self.object.username)


class UserDelete(DeleteView, UsersMixin, SuperAdminOrThisSiteMixin):
    model = User
    template_name = "system/users/delete.html"

    def get_object(self, queryset=None):
        self.selected_user = User.objects.get(username=self.kwargs["username"])
        return self.selected_user

    def get_context_data(self, **kwargs):
        context = super(UserDelete, self).get_context_data(**kwargs)
        self.add_userlist_to_context(context)
        context["selected_user"] = self.selected_user
        context["create_form"] = UserForm(prefix="create")

        return context

    def get_success_url(self):
        return "/site/%s/users/" % self.kwargs["site_uid"]

    def delete(self, request, *args, **kwargs):
        response = super(UserDelete, self).delete(request, *args, **kwargs)
        set_notification_cookie(
            response, _("User %s deleted") % self.kwargs["username"]
        )
        return response


class ConfigurationEntryCreate(SiteMixin, CreateView, SuperAdminOrThisSiteMixin):
    model = ConfigurationEntry
    form_class = ConfigurationEntryForm

    def form_valid(self, form):
        site = get_object_or_404(Site, uid=self.kwargs["site_uid"])
        self.object = form.save(commit=False)
        self.object.owner_configuration = site.configuration

        return super(ConfigurationEntryCreate, self).form_valid(form)

    def get_success_url(self):
        return "/site/{0}/settings/".format(self.kwargs["site_uid"])


class ConfigurationEntryUpdate(SiteMixin, UpdateView, SuperAdminOrThisSiteMixin):
    model = ConfigurationEntry
    form_class = ConfigurationEntryForm

    def get_success_url(self):
        return "/site/{0}/settings/".format(self.kwargs["site_uid"])


class ConfigurationEntryDelete(SiteMixin, DeleteView, SuperAdminOrThisSiteMixin):
    model = ConfigurationEntry

    def get_success_url(self):
        return "/site/{0}/settings/".format(self.kwargs["site_uid"])


class PCGroupCreate(SiteMixin, CreateView, SuperAdminOrThisSiteMixin):
    model = PCGroup
    form_class = PCGroupForm
    slug_field = "uid"

    def get_context_data(self, **kwargs):
        context = super(PCGroupCreate, self).get_context_data(**kwargs)

        # We don't want to edit computers yet
        if "pcs" in context["form"].fields:
            del context["form"].fields["pcs"]

        return context

    def form_valid(self, form):
        site = get_object_or_404(Site, uid=self.kwargs["site_uid"])
        self.object = form.save(commit=False)
        self.object.site = site

        return super(PCGroupCreate, self).form_valid(form)


class PCGroupUpdate(SiteMixin, SuperAdminOrThisSiteMixin, UpdateView):
    template_name = "system/site_groups.html"
    form_class = PCGroupForm
    model = PCGroup

    def get_object(self, queryset=None):
        site = Site.objects.get(uid=self.kwargs["site_uid"])
        try:
            return PCGroup.objects.get(id=self.kwargs["group_id"], site=site)
        except PCGroup.DoesNotExist:
            raise Http404(f"Du har ingen gruppe med id {self.kwargs['group_id']}")

    def get_context_data(self, **kwargs):
        context = super(PCGroupUpdate, self).get_context_data(**kwargs)

        group = self.object
        form = context["form"]
        site = context["site"]

        pc_queryset = site.pcs.filter(is_activated=True)
        form.fields["pcs"].queryset = pc_queryset

        selected_pc_ids = form["pcs"].value()
        context["available_pcs"] = pc_queryset.exclude(
            pk__in=selected_pc_ids
        ).values_list("pk", "name", "uid")
        context["selected_pcs"] = pc_queryset.filter(
            pk__in=selected_pc_ids
        ).values_list("pk", "name", "uid")

        context["selected_group"] = group

        context["newform"] = PCGroupForm()
        del context["newform"].fields["pcs"]

        context["all_scripts"] = sorted(
            Script.objects.filter(
                Q(site=site) | Q(site=None), is_security_script=False
            ),
            key=lambda s: s.name.lower(),
        )

        return context

    def form_valid(self, form):
        # Capture a view of the group's PCs and policy scripts before the
        # update
        members_pre = set(self.object.pcs.all())
        policy_pre = set(self.object.policy.all())

        try:
            with transaction.atomic():
                self.object.configuration.update_from_request(
                    self.request.POST, "group_configuration"
                )
                self.object.update_policy_from_request(self.request, "group_policies")

                response = super(PCGroupUpdate, self).form_valid(form)

                members_post = set(self.object.pcs.all())
                policy_post = set(self.object.policy.all())

                # Work out which PCs and policy scripts have come and gone
                surviving_members = members_post.intersection(members_pre)
                new_members = members_post.difference(members_pre)
                new_policy = policy_post.difference(policy_pre)

                # Run all policy scripts on new PCs...
                if new_members:
                    ordered_policy = list(policy_post)
                    ordered_policy.sort(key=lambda asc: asc.position)
                    for asc in ordered_policy:
                        asc.run_on(self.request.user, new_members)

                new_policy = list(new_policy)
                new_policy.sort(key=lambda asc: asc.position)
                # ... and run new policy scripts on old PCs
                for asc in new_policy:
                    asc.run_on(self.request.user, surviving_members)

                set_notification_cookie(
                    response, _("Group %s updated") % self.object.name
                )

                return response
        except MandatoryParameterMissingError as e:
            # If this happens, it happens *before* we have a valid
            # HttpResponse, so make one with form_invalid()
            response = self.form_invalid(form)
            parameter = e.args[0]
            set_notification_cookie(
                response,
                _(
                    'No value was specified for the mandatory input "{0}"'
                    ' of script "{1}"'
                ).format(parameter.name, parameter.script.name),
                error=True,
            )
            return response

    def form_invalid(self, form):
        return super(PCGroupUpdate, self).form_invalid(form)


class PCGroupDelete(SiteMixin, SuperAdminOrThisSiteMixin, DeleteView):
    model = PCGroup

    def get_object(self, queryset=None):
        site = Site.objects.get(uid=self.kwargs["site_uid"])
        return PCGroup.objects.get(id=self.kwargs["group_id"], site=site)

    def get_success_url(self):
        return "/site/{0}/groups/".format(self.kwargs["site_uid"])

    def delete(self, request, *args, **kwargs):
        name = self.get_object().name
        response = super(PCGroupDelete, self).delete(request, *args, **kwargs)
        set_notification_cookie(response, _("Group %s deleted") % name)
        return response


class SecurityProblemsView(SelectionMixin, SiteView):

    template_name = "system/site_security_problems.html"
    selection_class = SecurityProblem
    class_display_name = "security_problem"

    def get_list(self):
        return (
            self.object.security_problems.all()
            .extra(select={"lower_name": "lower(name)"})
            .order_by("lower_name")
        )

    def render_to_response(self, context):
        if "selected_security_problem" in context:
            return HttpResponseRedirect(
                "/site/%s/security_problems/%s/"
                % (context["site"].uid, context["selected_security_problem"].uid)
            )
        else:
            """
            return HttpResponseRedirect(
                '/site/%s/security_problems/new/' % context['site'].uid,
            )
            """
            site = context["site"]
            context["newform"] = SecurityProblemForm()
            user_set = User.objects.filter(bibos_profile__sites=site)
            group_set = site.groups.all()
            context["newform"].fields["alert_users"].queryset = user_set
            context["newform"].fields["alert_groups"].queryset = group_set

            # Limit list of scripts to only include security scripts.
            script_set = Script.objects.filter(
                Q(site__isnull=True) | Q(site=site),
                is_security_script=True,
            )
            context["newform"].fields["security_script"].queryset = script_set
            # Pass users and groups to context
            # that are available for a 'new' security problem.
            context["alert_users"] = user_set.values_list("pk", "username", "username")
            context["alert_groups"] = group_set.values_list("pk", "name", "pk")

            return super(SecurityProblemsView, self).render_to_response(context)


class SecurityProblemCreate(SiteMixin, CreateView, SuperAdminOrThisSiteMixin):
    template_name = "system/site_security_problems.html"
    model = SecurityProblem
    fields = "__all__"

    def get_success_url(self):
        return "/site/{0}/security_problems/".format(self.kwargs["site_uid"])


class SecurityProblemUpdate(SiteMixin, UpdateView, SuperAdminOrThisSiteMixin):
    template_name = "system/site_security_problems.html"
    model = SecurityProblem
    form_class = SecurityProblemForm

    def get_object(self, queryset=None):
        try:
            return SecurityProblem.objects.get(
                uid=self.kwargs["uid"], site__uid=self.kwargs["site_uid"]
            )
        except SecurityProblem.DoesNotExist:
            raise Http404(f"Du har ingen sikkerhedsregel med id {self.kwargs['uid']}")

    def get_context_data(self, **kwargs):

        context = super(SecurityProblemUpdate, self).get_context_data(**kwargs)

        site = context["site"]
        form = context["form"]
        group_set = site.groups.all()
        selected_group_ids = form["alert_groups"].value()
        # template picklist requires the form pk, name, url (u)id.
        context["available_groups"] = group_set.exclude(
            pk__in=selected_group_ids
        ).values_list("pk", "name", "pk")
        context["selected_groups"] = group_set.filter(
            pk__in=selected_group_ids
        ).values_list("pk", "name", "pk")

        user_set = User.objects.filter(bibos_profile__sites=site)
        selected_user_ids = form["alert_users"].value()
        context["available_users"] = user_set.exclude(
            pk__in=selected_user_ids
        ).values_list("pk", "username", "username")
        context["selected_users"] = user_set.filter(
            pk__in=selected_user_ids
        ).values_list("pk", "username", "username")
        # Limit list of scripts to only include security scripts.
        script_set = Script.objects.filter(
            Q(site__isnull=True) | Q(site=site),
            is_security_script=True,
        )
        form.fields["security_script"].queryset = script_set

        # Extra fields
        context["selected_security_problem"] = self.object
        context["newform"] = SecurityProblemForm()
        context["newform"].fields["security_script"].queryset = script_set
        context["newform"].fields["alert_users"].queryset = user_set
        context["newform"].fields["alert_groups"].queryset = group_set
        # Pass users and groups to context
        # that are available for a 'new' security problem.
        context["alert_users"] = user_set.values_list("pk", "username", "username")
        # template picklist requires the form pk, name, url (u)id.
        context["alert_groups"] = group_set.values_list("pk", "name", "pk")

        return context

    def get_success_url(self):
        return "/site/{0}/security_problems/".format(self.kwargs["site_uid"])


class SecurityProblemDelete(SiteMixin, DeleteView, SuperAdminOrThisSiteMixin):
    model = SecurityProblem
    # form_class = <hopefully_not_necessary>

    def get_object(self, queryset=None):
        return SecurityProblem.objects.get(
            uid=self.kwargs["uid"], site__uid=self.kwargs["site_uid"]
        )

    def get_success_url(self):
        return "/site/{0}/security_problems/".format(self.kwargs["site_uid"])


class SecurityEventsView(SiteView):
    template_name = "system/site_security_events.html"

    def get_context_data(self, **kwargs):
        # First, get basic context from superclass
        context = super(SecurityEventsView, self).get_context_data(**kwargs)
        # Supply extra info as needed.
        level_preselected = set([SecurityProblem.CRITICAL, SecurityProblem.HIGH])
        context["level_choices"] = [
            {
                "name": name,
                "value": value,
                "label": SecurityProblem.LEVEL_TO_LABEL[value],
                "checked": 'checked="checked' if value in level_preselected else "",
            }
            for (value, name) in SecurityProblem.LEVEL_CHOICES
        ]
        status_preselected = set([SecurityEvent.NEW, SecurityEvent.ASSIGNED])
        context["status_choices"] = [
            {
                "name": name,
                "value": value,
                "label": SecurityEvent.STATUS_TO_LABEL[value],
                "checked": 'checked="checked' if value in status_preselected else "",
            }
            for (value, name) in SecurityEvent.STATUS_CHOICES
        ]

        if "pc_uid" in self.kwargs:
            context["pc_uid"] = self.kwargs["pc_uid"]

        context["form"] = SecurityEventForm()
        qs = context["form"].fields["assigned_user"].queryset
        qs = qs.filter(Q(bibos_profile__sites=self.get_object()) | Q(is_superuser=True))
        context["form"].fields["assigned_user"].queryset = qs

        return context


class SecurityEventSearch(SiteMixin, JSONResponseMixin, BaseListView):
    paginate_by = 20
    http_method_names = ["get"]
    VALID_ORDER_BY = []
    for i in ["pk", "problem__name", "occurred_time", "assigned_user__username"]:
        VALID_ORDER_BY.append(i)
        VALID_ORDER_BY.append("-" + i)

    def render_to_response(self, context, **response_kwargs):
        return self.render_to_json_response(context, **response_kwargs)

    def get_queryset(self):
        site = get_object_or_404(Site, uid=self.kwargs[self.site_uid])
        queryset = SecurityEvent.objects.all()
        params = self.request.GET

        query = {"problem__site": site}
        if params.get("pc", None):
            query["pc__uid"] = params["pc"]

        if "level" in params:
            query["problem__level__in"] = params.getlist("level")

        if "status" in params:
            query["status__in"] = params.getlist("status")

        orderby = params.get("orderby", "-occurred_time")
        if orderby not in SecurityEventSearch.VALID_ORDER_BY:
            orderby = "-occurred_time"

        queryset = queryset.filter(**query).order_by(orderby, "pk")

        return queryset

    def get_data(self, context):
        site = context["site"]
        page_obj = context["page_obj"]
        paginator = context["paginator"]
        adjacent_pages = 2
        page_numbers = [
            n
            for n in range(
                page_obj.number - adjacent_pages, page_obj.number + adjacent_pages + 1
            )
            if n > 0 and n <= paginator.num_pages
        ]

        result = {
            "count": paginator.count,
            "num_pages": paginator.num_pages,
            "page": page_obj.number,
            "page_numbers": page_numbers,
            "has_next": page_obj.has_next(),
            "next_page_number": (
                page_obj.next_page_number() if page_obj.has_next() else None
            ),
            "has_previous": page_obj.has_previous(),
            "previous_page_number": (
                page_obj.previous_page_number() if page_obj.has_previous() else None
            ),
            "results": [
                {
                    "pk": event.pk,
                    "site_uid": site.uid,
                    "problem_name": event.problem.name,
                    "problem_url": reverse(
                        "security_problem", args=[site.uid, event.problem.uid]
                    ),
                    "pc_id": event.pc.id,
                    "occurred": event.occurred_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "reported": event.reported_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "status": event.get_status_display(),
                    "status_label": event.STATUS_TO_LABEL[event.status],
                    "level": SecurityProblem.LEVEL_TRANSLATIONS[event.problem.level],
                    "level_label": SecurityProblem.LEVEL_TO_LABEL[event.problem.level]
                    + "",
                    "pc_name": event.pc.name,
                    "pc_url": reverse("computer", args=[site.uid, event.pc.uid]),
                    "assigned_user": (
                        event.assigned_user.username if event.assigned_user else ""
                    ),
                    "assigned_user_url": (
                        reverse("user", args=[site.uid, event.assigned_user.username])
                        if event.assigned_user
                        else ""
                    ),
                    "summary": event.summary,
                    "note": event.note,
                }
                for event in page_obj
            ],
        }

        return result


class SecurityEventsUpdate(SiteMixin, SuperAdminOrThisSiteMixin, ListView):
    http_method_names = ["post"]
    model = SecurityEvent

    def get_queryset(self):
        queryset = super().get_queryset()
        site = get_object_or_404(Site, uid=self.kwargs[self.site_uid])
        params = self.request.POST
        ids = params.getlist("ids")
        queryset = queryset.filter(id__in=ids, pc__site=site)

        return queryset

    def post(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        params = self.request.POST

        status = params.get("status")
        assigned_user = params.get("assigned_user")
        note = params.get("note")

        queryset.update(status=status, assigned_user=assigned_user, note=note)

        return HttpResponse("OK")


documentation_menu_items = [
    ("", "Administrationssiden"),
    ("om_os2borgerpc_admin", "Om"),
    ("status", "Status"),
    ("computers", "Computere"),
    ("groups", "Grupper"),
    ("jobs", "Jobs"),
    ("scripts", "Scripts"),
    ("security_scripts", "Sikkerhedsscripts"),
    ("users", "Brugere"),
    ("configuration", "Konfigurationer"),
    ("creating_security_problems", "Oprettelse af Sikkerhedsovervågning (PDF)"),
    ("changelogs", "Nyhedssiden"),
    ("", "OS2borgerPC"),
    ("os2borgerpc_installation_guide", "Installationsguide (PDF)"),
    ("os2borgerpc_installation_guide_old", "Gammel installationsguide (PDF)"),
    ("", "OS2borgerPC Kiosk"),
    ("os2borgerpc_kiosk_installation_guide", "Installationsguide"),
    ("os2borgerpc_kiosk_wifi_guide", "Opdatering af Wi-Fi opsætning"),
    ("", "Opsætning af Gateway"),
    ("gateway_install", "Installation af gateway"),
    ("gateway_admin", "Administration af gateway"),
    ("gateway_use", "Anvendelse af gateway"),
    ("", "Teknisk dokumentation"),
    ("tech/os2borgerpc-image", "OS2borgerPC Image"),
    ("tech/os2borgerpc-admin", "OS2borgerPC Admin Site"),
    ("tech/os2borgerpc-server-image", "OS2borgerPC Kiosk Image"),
    ("tech/os2borgerpc-client", "OS2borgerPC Client"),
]


class DocView(TemplateView):
    docname = "status"

    def template_exists(self, subpath):
        fullpath = os.path.join(settings.DOCUMENTATION_DIR, subpath)
        return os.path.isfile(fullpath)

    def get_context_data(self, **kwargs):  # noqa
        if "name" in self.kwargs:
            self.docname = self.kwargs["name"]
        else:
            # This will be mapped to documentation/index.html
            self.docname = "index"

        if self.docname.find("..") != -1:
            raise Http404

        # Try <docname>.html and <docname>/index.html
        name_templates = ["documentation/{0}.html", "documentation/{0}/index.html"]

        templatename = None
        for nt in name_templates:
            expanded = nt.format(self.docname)
            if self.template_exists(expanded):
                templatename = expanded
                break

        if templatename is None:
            raise Http404
        else:
            self.template_name = templatename

        context = super(DocView, self).get_context_data(**kwargs)
        context["docmenuitems"] = documentation_menu_items
        docnames = self.docname.split("/")

        context["menu_active"] = docnames[0]

        # Set heading according to chosen item
        current_heading = None
        for link, name in context["docmenuitems"]:
            if link == "":
                current_heading = name
            elif link == docnames[0]:
                context["docheading"] = current_heading
                break

        # Add a submenu if it exists
        submenu_template = "documentation/" + docnames[0] + "/__submenu__.html"
        if self.template_exists(submenu_template):
            context["submenu_template"] = submenu_template

        if len(docnames) > 1 and docnames[1]:
            # Don't allow direct access to submenus
            if docnames[1] == "__submenu__":
                raise Http404
            context["submenu_active"] = docnames[1]

        params = self.request.GET or self.request.POST
        back_link = params.get("back")
        if back_link is None:
            referer = self.request.META.get("HTTP_REFERER")
            if referer and referer.find("/documentation/") == -1:
                back_link = referer
        if back_link:
            context["back_link"] = back_link

        return context


class JSONSiteSummary(JSONResponseMixin, SiteView):
    """Produce a JSON document summarising the state of all of the computers in
    a site.
    """

    interesting_properties = [
        "id",
        "name",
        "description",
        "configuration_id",
        "site_id",
        "is_activated",
        "created",
        "last_seen",
        "location",
    ]

    def get_context_data(self, **kwargs):
        pcs = []
        for p in self.object.pcs.all():
            pc = {}
            for pn in JSONSiteSummary.interesting_properties:
                pv = getattr(p, pn)
                # Don't convert these types to string representations...
                if (
                    pv is None
                    or isinstance(pv, bool)
                    or isinstance(pv, float)
                    or isinstance(pv, int)
                ):
                    pass
                # ... use the right date format for datetimes...
                elif isinstance(pv, datetime):
                    pv = pv.isoformat()
                # ... and use simple string representations for everything else
                else:
                    pv = str(pv)
                pc[pn] = pv
            pcs.append(pc)
        return pcs


class ImageVersionsView(SiteMixin, SuperAdminOrThisSiteMixin, ListView):
    """Displays all of the image versions that this site has access to (i.e.,
    all versions released before the site's last_version datestamp).
    """

    template_name = "system/site_image_versions.html"
    model = ImageVersion
    context_object_name = "image_versions"
    selection_class = ImageVersion
    class_display_name = "image_version"

    def get_context_data(self, **kwargs):
        context = super(ImageVersionsView, self).get_context_data(**kwargs)

        site_uid = self.kwargs.get("site_uid")
        site_obj = Site.objects.get(uid=site_uid)
        last_pay_date = site_obj.paid_for_access_until

        if not last_pay_date:

            context["site_allowed"] = False

        else:

            context["site_allowed"] = True

            # excluding versions where
            # image release date > client's last pay date.
            versions = ImageVersion.objects.exclude(release_date__gt=last_pay_date)

            platform_choice = self.kwargs.get(
                "platform", ImageVersion.platform_choices[0][0]
            ).upper()

            selected_platform = next(
                (x for x in ImageVersion.platform_choices if x[0] == platform_choice),
                ImageVersion.platform_choices[0][0],
            )
            context["selected_platform"] = selected_platform
            context["selected_platform_images"] = versions.filter(
                platform=selected_platform[0]
            ).order_by("-release_date", "-id")
            context["platform_choices"] = dict(ImageVersion.platform_choices)

        return context


class ChangelogListView(ListView):
    template_name = "system/changelog/list.html"

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

        # Filter the queryset based on which site is viewing the site if the slug is
        # 'global' it means the user is not logged in and therefore needs a different
        # context
        if context["view"].kwargs.get("slug") != "global":
            context["site"] = get_object_or_404(Site, uid=self.kwargs["slug"])
            context["site_extension"] = "site_with_navigation.html"
            context["global_view"] = False
            queryset = queryset.filter(Q(site=context["site"]) | Q(site=None))
        else:
            context["site_extension"] = "sitebase.html"
            context["global_view"] = True
            queryset = queryset.filter(site=None)

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

        response = self.get(request, *args, **kwargs)

        comment = ChangelogComment()

        comment.user = get_object_or_404(User, pk=req["user"])
        comment.changelog = get_object_or_404(Changelog, pk=req["changelog"])
        comment.content = req["content"]

        if req["parent_comment"] != "None":
            comment.parent_comment = get_object_or_404(
                ChangelogComment, pk=req["parent_comment"]
            )

        comment.save()
        return response
