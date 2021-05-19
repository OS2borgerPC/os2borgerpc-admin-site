# -*- coding: utf-8 -*-
import os
import json
from datetime import datetime
from functools import cmp_to_key
from urllib.parse import quote

from django.http import HttpResponseRedirect, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from django.urls import reverse

from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic import (
    View,
    ListView,
    DetailView,
    RedirectView,
    TemplateView
)
from django.views.generic.list import BaseListView

from django.db import transaction
from django.db.models import Q
from django.conf import settings

from account.models import (
    UserProfile,
    SiteMembership,
)

from system.models import (
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
)
# PC Status codes
from system.forms import (
    SiteForm,
    GroupForm,
    ConfigurationEntryForm,
    ScriptForm,
    UserForm,
    ParameterForm,
    PCForm,
    SecurityProblemForm,
)


def set_notification_cookie(response, message, error=False):
    descriptor = {
        "message": message,
        "type": "success" if not error else "error"
    }

    response.set_cookie('bibos-notification',
                        quote(json.dumps(descriptor), safe='')
                        )


def get_no_of_sec_events(site):
    """Utility function to get number of security events."""
    no_of_sec_events = SecurityEvent.objects.filter(
        problem__site=site
    ).exclude(
        problem__level=SecurityProblem.NORMAL
    ).exclude(status=SecurityEvent.RESOLVED).count()
    return no_of_sec_events


def get_latest_security_event(pc):
    """Utility function to get latest security event for pc."""
    sc = ""
    try:
        sc = SecurityEvent.objects.filter(pc_id=pc.id).latest('reported_time')
    except SecurityEvent.DoesNotExist:
        sc = "Ingen hændelser"
    return sc


# Mixin class to require login
class LoginRequiredMixin(View):
    """Subclass in all views where login is required."""

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(LoginRequiredMixin, self).dispatch(*args, **kwargs)


class SuperAdminOnlyMixin(View):
    """Only allows access to super admins."""
    check_function = user_passes_test(lambda u: u.is_superuser, login_url='/')

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
        if 'site_uid' in kwargs:
            slug_field = 'site_uid'
        elif 'slug' in kwargs:
            slug_field = 'slug'
        # If none given, give up
        if slug_field:
            site = get_object_or_404(Site, uid=kwargs[slug_field])
        check_function = user_passes_test(
            lambda u:
            (u.is_superuser) or
            (site and site in u.bibos_profile.sites.all()), login_url='/'
        )
        wrapped_super = check_function(
            super(SuperAdminOrThisSiteMixin, self).dispatch
        )
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
    lookup_field = 'uid'
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

        display_name = (self.class_display_name if self.class_display_name else
                        self.selection_class.__name__.lower())
        if selected is not None:
            context['selected_{0}'.format(display_name)] = selected
        context['{0}_list'.format(display_name)] = self.get_list()
        return context


class JSONResponseMixin:
    """
    A mixin that can be used to render a JSON response.
    """
    def render_to_json_response(self, context, **response_kwargs):
        """
        Returns a JSON response, transforming 'context' to make the payload.
        """
        return JsonResponse(
            self.get_data(context),
            **response_kwargs
        )

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

    site_uid = 'site_uid'

    def get_context_data(self, **kwargs):
        context = super(SiteMixin, self).get_context_data(**kwargs)
        site = get_object_or_404(Site, uid=self.kwargs[self.site_uid])
        context['site'] = site
        # Add information about outstanding security events.
        no_of_sec_events = get_no_of_sec_events(site)
        context['sec_events'] = no_of_sec_events

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
    context_object_name = 'site_list'

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            qs = Site.objects.all()
        else:
            qs = user.bibos_profile.sites.all()
        return qs

    def get_context_data(self, **kwargs):
        context = super(SiteList, self).get_context_data(**kwargs)
        context["user"] = self.request.user
        return context


# Base class for Site-based passive (non-form) views
class SiteView(DetailView,  SuperAdminOrThisSiteMixin):
    """Base class for all views based on a single site."""
    model = Site
    slug_field = 'uid'

    def get_context_data(self, **kwargs):
        context = super(SiteView, self).get_context_data(**kwargs)
        site = self.get_object()
        # Add information about outstanding security events.
        no_of_sec_events = get_no_of_sec_events(site)
        context['sec_events'] = no_of_sec_events

        return context


class SiteDetailView(SiteView):
    """Class for showing the overview that is displayed when entering a site"""

    # For hver pc skal vi hente seneste security event.
    def get_context_data(self, **kwargs):
        context = super(SiteDetailView, self).get_context_data(**kwargs)
        # Top level list of new PCs etc.
        context['pcs'] = self.object.pcs.filter(Q(is_active=False))
        context['pcs'] = sorted(context['pcs'], key=lambda s: s.name.lower())

        site = context['site']
        active_pcs = site.pcs.filter(is_active=True)
        context['active_pcs'] = active_pcs.count()
        context['ls_pcs'] = site.pcs.all().order_by('last_seen')
        securityevents = []
        for pc in context['ls_pcs']:
            securityevents.append(get_latest_security_event(pc))

        context['security_events'] = securityevents
        return context


class SiteConfiguration(SiteView):
    template_name = 'system/site_configuration.html'

    def get_context_data(self, **kwargs):
        # First, get basic context from superclass
        context = super(SiteConfiguration, self).get_context_data(**kwargs)
        configs = self.object.configuration.entries.all()
        context['site_configs'] = configs.order_by('key')

        return context

    def post(self, request, *args, **kwargs):
        # Do basic method
        kwargs['updated'] = True
        response = self.get(request, *args, **kwargs)

        # Handle saving of data
        self.object.configuration.update_from_request(
            request.POST, 'site_configs'
        )

        set_notification_cookie(
            response,
            _('Configuration for %s updated') % kwargs['slug']
        )
        return response


# Now follows all site-based views, i.e. subclasses
# of SiteView.
class JobsView(SiteView):
    template_name = 'system/site_jobs.html'

    def get_context_data(self, **kwargs):
        # First, get basic context from superclass
        context = super(JobsView, self).get_context_data(**kwargs)
        site = context["site"]
        context['batches'] = site.batches.all()[:100]
        context['pcs'] = site.pcs.all()
        context['groups'] = site.groups.all()
        preselected = set([
            Job.NEW,
            Job.SUBMITTED,
            Job.RUNNING,
            Job.FAILED,
            Job.DONE,
        ])
        context['status_choices'] = [
            {
                'name': name,
                'value': value,
                'label': Job.STATUS_TO_LABEL[value],
                'checked':
                'checked="checked' if value in preselected else ''
            } for (value, name) in Job.STATUS_CHOICES
        ]
        params = self.request.GET or self.request.POST

        for k in ['batch', 'pc', 'group']:
            v = params.get(k, None)
            if v is not None and v.isdigit():
                context['selected_%s' % k] = int(v)

        return context


class JobSearch(SiteMixin, JSONResponseMixin, BaseListView):
    paginate_by = 20
    http_method_names = ['get']
    VALID_ORDER_BY = []
    for i in ['pk', 'batch__script__name', 'started', 'finished', 'status',
              'pc__name', 'batch__name']:
        VALID_ORDER_BY.append(i)
        VALID_ORDER_BY.append('-' + i)

    context_object_name = "jobs_list"

    def render_to_response(self, context, **response_kwargs):
        return self.render_to_json_response(context, **response_kwargs)

    def get_queryset(self):
        site = get_object_or_404(Site, uid=self.kwargs[self.site_uid])
        queryset = Job.objects.all()
        params = self.request.GET

        query = {"batch__site": site}

        if 'status' in params:
            query['status__in'] = params.getlist('status')

        for k in ['pc', 'batch']:
            v = params.get(k, '')
            if v != '':
                query[k] = v

        group = params.get('group', '')
        if group != '':
            query['pc__pc_groups'] = group

        orderby = params.get('orderby', '-pk')
        if orderby not in JobSearch.VALID_ORDER_BY:
            orderby = '-pk'

        queryset = queryset.filter(**query).order_by(
            orderby,
            'pk'
        )

        return queryset

    def get_data(self, context):
        site = context["site"]
        page_obj = context["page_obj"]
        paginator = context["paginator"]
        adjacent_pages = 2
        page_numbers = [
            n for n in range(
                page_obj.number - adjacent_pages,
                page_obj.number + adjacent_pages + 1
            ) if n > 0 and n <= paginator.num_pages
        ]

        result = {
            "count": paginator.count,
            "num_pages": paginator.num_pages,
            "page": page_obj.number,
            "page_numbers": page_numbers,
            "has_next": page_obj.has_next(),
            "next_page_number": (
                page_obj.next_page_number()
                if page_obj.has_next()
                else None
            ),
            "has_previous": page_obj.has_previous(),
            "previous_page_number": (
                page_obj.previous_page_number()
                if page_obj.has_previous()
                else None
            ),
            "results": [{
                'pk': job.pk,
                'script_name': job.batch.script.name,
                'started': job.started.strftime("%Y-%m-%d %H:%M:%S") if
                job.started else None,
                'finished': job.finished.strftime("%Y-%m-%d %H:%M:%S") if
                job.finished else None,
                'status': job.status_translated + '',
                'label': job.status_label,
                'pc_name': job.pc.name,
                'batch_name': job.batch.name,
                # Yep, it's meant to be double-escaped - it's HTML-escaped
                # content that will be stored in an HTML attribute
                'has_info': job.has_info,
                'restart_url': '/site/%s/jobs/%s/restart/' % (site.uid, job.pk)
            } for job in page_obj]
        }

        return result


class JobRestarter(DetailView, SuperAdminOrThisSiteMixin):
    template_name = 'system/jobs/restart.html'
    model = Job

    def status_fail_response(self):
        response = HttpResponseRedirect(self.get_success_url())
        set_notification_cookie(
            response,
            _('Can only restart jobs with status %s') % Job.FAILED
        )
        return response

    def get(self, request, *args, **kwargs):
        self.site = get_object_or_404(Site, uid=kwargs['site_uid'])
        self.object = self.get_object()

        # Only restart jobs that have failed
        if self.object.status != Job.FAILED:
            return self.status_fail_response()

        context = self.get_context_data(object=self.object)

        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super(JobRestarter, self).get_context_data(**kwargs)
        context['site'] = self.site
        context['selected_job'] = self.object
        return context

    def post(self, request, *args, **kwargs):
        self.site = get_object_or_404(Site, uid=kwargs['site_uid'])
        self.object = self.get_object()

        if self.object.status != Job.FAILED:
            return self.status_fail_response()

        new_job = self.object.restart(user=self.request.user)
        response = HttpResponseRedirect(self.get_success_url())
        set_notification_cookie(
            response,
            "Job %s restarted as job %s" % (self.object.pk, new_job.pk)
        )
        return response

    def get_success_url(self):
        return '/site/%s/jobs/' % self.kwargs['site_uid']


class JobInfo(DetailView, LoginRequiredMixin):
    template_name = 'system/jobs/info.html'
    model = Job

    def get(self, request, *args, **kwargs):
        self.site = get_object_or_404(Site, uid=kwargs['site_uid'])
        return super(JobInfo, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(JobInfo, self).get_context_data(**kwargs)
        if self.site != self.object.batch.site:
            raise Http404
        context['site'] = self.site
        context['job'] = self.object
        return context


class ScriptMixin(object):
    script = None
    script_inputs = ''
    is_security = False

    def setup_script_editing(self, **kwargs):
        # Get site
        self.site = get_object_or_404(Site, uid=kwargs['slug'])
        # Add the global and local script lists
        self.scripts = Script.objects.filter(
            Q(site=self.site) | Q(site=None),
            is_security_script=self.is_security,
            deleted=False
        ).exclude(
            site__name='system'
        )

        if 'script_pk' in kwargs:
            self.script = get_object_or_404(Script, pk=kwargs['script_pk'])

    def get(self, request, *args, **kwargs):
        self.setup_script_editing(**kwargs)
        return super(ScriptMixin, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.setup_script_editing(**kwargs)
        return super(ScriptMixin, self).post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        # Get context from super class
        context = super(ScriptMixin, self).get_context_data(**kwargs)
        context['site'] = self.site
        context['script_tags'] = ScriptTag.objects.all()

        def list_scripts_by_tag(scriptlist):
            # create a dict to store scripts by tag
            scriptdict = { 'untagged': [] }
            # create a dict key for every tag
            for tag in ScriptTag.objects.all():
                scriptdict[tag] = []
            # make a list of scripts for each tag key in dict
            for script in scriptlist:
                # check is script has no tags
                if script.tags.count() <= 0: 
                    # add untagged script to 'untagged' list
                    scriptdict['untagged'].append(script)
                else: 
                    for tag in script.tags.all():
                        scriptdict[tag].append(script)
            # run through the tags again to check for empty lists
            for tag in ScriptTag.objects.all():
                if len(scriptdict[tag]) <= 0:
                    # remove key if value is a list with zero length
                    scriptdict.pop(tag)
            # return the populated dict
            return scriptdict
        
        local_scripts = sorted(self.scripts.filter(site=self.site),
                               key=lambda s: s.name.lower())

        context['local_scripts'] = local_scripts
        context['local_scripts_by_tag'] = list_scripts_by_tag(local_scripts)

        global_scripts = sorted(self.scripts.filter(site=None),
                                key=lambda s: s.name.lower())

        context['global_scripts'] = global_scripts
        context['global_scripts_by_tag'] = list_scripts_by_tag(global_scripts)

        context['script_inputs'] = self.script_inputs
        context['is_security'] = self.is_security
        if self.is_security:
            context['script_url'] = 'security_script'
        else:
            context['script_url'] = 'script'

        # If we selected a script add it to context
        if self.script is not None:
            context['selected_script'] = self.script
            if self.script.site is None:
                context['global_selected'] = True
            if not context['script_inputs']:
                context['script_inputs'] = [
                    {
                        'pk': input.pk,
                        'name': input.name,
                        'value_type': input.value_type
                    } for input in self.script.ordered_inputs
                ]
        elif not context['script_inputs']:
            context['script_inputs'] = []

        context['script_inputs_json'] = json.dumps(context['script_inputs'])
        # Add information about outstanding security events.
        no_of_sec_events = get_no_of_sec_events(self.site)
        context['sec_events'] = no_of_sec_events

        return context

    def validate_script_inputs(self):
        params = self.request.POST
        num_inputs = params.get('script-number-of-inputs', 0)
        inputs = []
        success = True
        if int(num_inputs) > 0:
            for i in range(int(num_inputs)):
                data = {
                    'pk': params.get('script-input-%d-pk' % i, None),
                    'name': params.get('script-input-%d-name' % i, ''),
                    'value_type': params.get('script-input-%d-type' % i, ''),
                    'position': i,
                }

                if data['name'] is None or data['name'] == '':
                    data['name_error'] = 'Fejl: Du skal angive et navn'
                    success = False

                if data['value_type'] not in [value for (value, name)
                                              in Input.VALUE_CHOICES]:
                    data['type_error'] = 'Fejl: Du skal angive en korrekt type'
                    success = False

                inputs.append(data)

            self.script_inputs = inputs

        return success

    def save_script_inputs(self):
        seen = []
        for input_data in self.script_inputs:
            input_data['script'] = self.script

            pk = None
            if 'pk' in input_data:
                pk = input_data['pk'] or None
                del input_data['pk']

            if pk is None or pk == '':
                script_input = Input.objects.create(**input_data)
                script_input.save()
                seen.append(script_input.pk)
            else:
                Input.objects.filter(pk=pk).update(**input_data)
                seen.append(int(pk))

        for inp in self.script.inputs.all():
            if inp.pk not in seen:
                inp.delete()


class ScriptList(ScriptMixin, SiteView):

    def get(self, request, *args, **kwargs):
        self.setup_script_editing(**kwargs)
        try:
            # Sort by -site followed by lowercased name
            def sort_by(a, b):
                if a.site == b.site:
                    # cmp deprecated: cmp(a, b) has been changed to
                    # the ((a > b) - (a < b)) formats
                    return (
                            (a.name.lower() > b.name.lower())
                            - (a.name.lower() < b.name.lower())
                            )
                else:
                    if b.site is not None:
                        return 1
                    else:
                        return -1
            # cmp deprecated: cmp converted to key function
            script = sorted(self.scripts, key=cmp_to_key(sort_by))[0]
            return HttpResponseRedirect(
                script.get_absolute_url(site_uid=self.site.uid)
            )

        except IndexError:
            return HttpResponseRedirect(
                reverse("new_security_script", args=[self.site.uid])
                if self.is_security else
                reverse("new_script", args=[self.site.uid])
            )


class ScriptCreate(ScriptMixin, CreateView, SuperAdminOrThisSiteMixin):
    template_name = 'system/scripts/create.html'
    form_class = ScriptForm

    def get_context_data(self, **kwargs):
        context = super(ScriptCreate, self).get_context_data(**kwargs)
        context['type_choices'] = Input.VALUE_CHOICES
        return context

    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.get_form_class()
        form = super(ScriptCreate, self).get_form(form_class)
        form.prefix = 'create'
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
            return reverse(
                "security_script",
                args=[self.site.uid, self.script.pk]
            )
        else:
            return reverse("script", args=[self.site.uid, self.script.pk])


class ScriptUpdate(ScriptMixin, UpdateView, SuperAdminOrThisSiteMixin):
    template_name = 'system/scripts/update.html'
    form_class = ScriptForm

    def get_context_data(self, **kwargs):
        # Get context from super class
        context = super(ScriptUpdate, self).get_context_data(**kwargs)
        if self.script is not None and self.script.executable_code is not None:
            try:
                display_code = self.script.executable_code.read().decode(
                    "utf-8"
                )
            except UnicodeDecodeError:
                display_code = "<Kan ikke vise koden - binære data.>"
            except FileNotFoundError:
                display_code = "<Kan ikke vise koden - upload venligst igen.>"
            context[
                'script_preview'
            ] = display_code
        context['type_choices'] = Input.VALUE_CHOICES
        self.create_form = ScriptForm()
        self.create_form.prefix = 'create'
        context['create_form'] = self.create_form
        return context

    def get_object(self, queryset=None):
        return self.script

    def form_valid(self, form):
        if self.validate_script_inputs():
            # save the username for the AuditModelMixin.
            form.instance.user_modified = self.request.user.username
            self.save_script_inputs()
            response = super(ScriptUpdate, self).form_valid(form)
            set_notification_cookie(
                response,
                _('Script %s updated') % self.script.name
            )
            return response
        else:
            return self.form_invalid(form, transfer_inputs=False)

    def form_invalid(self, form, transfer_inputs=True):
        if transfer_inputs:
            self.validate_script_inputs()

        return super(ScriptUpdate, self).form_invalid(form)

    def get_success_url(self):
        if self.is_security:
            return reverse(
                "security_script",
                args=[self.site.uid, self.script.pk]
            )
        else:
            return reverse("script", args=[self.site.uid, self.script.pk])


class ScriptRun(SiteView):
    action = None
    form = None
    STEP1 = 'choose_pcs_and_groups'
    STEP2 = 'choose_parameters'
    STEP3 = 'run_script'

    def post(self, request, *args, **kwargs):
        return super(ScriptRun, self).get(request, *args, **kwargs)

    def step1(self, context):
        self.template_name = 'system/scripts/run_step1.html'
        context['pcs'] = self.object.pcs.all().order_by('name')
        context['groups'] = self.object.groups.all().order_by('name')
        context['action'] = ScriptRun.STEP2

    def step2(self, context):
        self.template_name = 'system/scripts/run_step2.html'
        if 'pcs' not in context:
            # Transfer chosen groups and PCs as PC pks
            pcs = [int(pk) for pk in self.request.POST.getlist('pcs', [])]
            for group_pk in self.request.POST.getlist('groups', []):
                group = PCGroup.objects.get(pk=group_pk)
                for pc in group.pcs.all():
                    pcs.append(int(pc.pk))
            # Uniquify
            context['pcs'] = list(set(pcs))

        if len(context['pcs']) == 0:
            context['message'] = _('You must specify at least one group or pc')
            self.step1(context)
            return

        # Set up the form
        if 'form' not in context:
            context['form'] = ParameterForm(script=context['script'])

        # Go to step3 on submit
        context['action'] = ScriptRun.STEP3

    def step3(self, context):
        self.template_name = 'system/scripts/run_step3.html'
        form = ParameterForm(self.request.POST,
                             self.request.FILES,
                             script=context['script'])
        context['form'] = form
        pcs = self.request.POST.getlist('pcs', [])

        context['num_pcs'] = len(pcs)
        if context['num_pcs'] == 0:
            context['message'] = _('You must specify at least one group or pc')
            self.step1(context)
            return

        if not form.is_valid():
            self.step2(context)
        else:
            args = []
            for i in range(0, context['script'].inputs.count()):
                args.append(form.cleaned_data['parameter_%s' % i])

            context['batch'] = context['script'].run_on(
                context['site'],
                PC.objects.filter(pk__in=pcs),
                *args,
                user=self.request.user
            )

    def get_context_data(self, **kwargs):
        context = super(ScriptRun, self).get_context_data(**kwargs)
        context['script'] = get_object_or_404(Script,
                                              pk=self.kwargs['script_pk'])

        action = self.request.POST.get('action', 'choose_pcs_and_groups')
        if action == ScriptRun.STEP1:
            self.step1(context)
        elif action == ScriptRun.STEP2:
            self.step2(context)
        elif action == ScriptRun.STEP3:
            self.step3(context)
        else:
            raise Exception(
                "POST to ScriptRun with wrong action %s" % self.action
            )

        return context


class ScriptDelete(ScriptMixin, SuperAdminOrThisSiteMixin, DeleteView):
    template_name = 'system/scripts/confirm_delete.html'
    model = Script

    def get_object(self, queryset=None):
        return Script.objects.get(
            pk=self.kwargs['script_pk'],
            site__uid=self.kwargs['slug']
        )

    def get_success_url(self):
        if self.is_security:
            return reverse(
                "security_scripts",
                kwargs={"slug": self.kwargs["slug"]}
            )
        else:
            return reverse(
                "scripts",
                kwargs={"slug": self.kwargs["slug"]}
            )

    def delete(self, request, *args, **kwargs):
        script = self.get_object()
        script.deleted = True
        script.save()

        return redirect(self.get_success_url())


class PCsView(SelectionMixin, SiteView):

    template_name = 'system/site_pcs.html'
    selection_class = PC

    def get_list(self):
        return self.object.pcs.all().extra(
            select={'lower_name': 'lower(name)'}
        ).order_by('lower_name')

    def render_to_response(self, context):
        if('selected_pc' in context):
            return HttpResponseRedirect('/site/%s/computers/%s/' % (
                context['site'].uid,
                context['selected_pc'].uid
            ))
        else:
            return super(PCsView, self).render_to_response(context)


class PCUpdate(SiteMixin, UpdateView, LoginRequiredMixin):
    template_name = 'system/pc_form.html'
    form_class = PCForm
    slug_field = 'uid'

    VALID_ORDER_BY = []
    for i in ['pk', 'batch__script__name', 'started', 'finished', 'status',
              'batch__name']:
        VALID_ORDER_BY.append(i)
        VALID_ORDER_BY.append('-' + i)

    def get_object(self, queryset=None):
        try:
            return PC.objects.get(uid=self.kwargs['pc_uid'])
        except PC.DoesNotExist:
            raise Http404(
                f"der findes ingen computer med id {self.kwargs['pc_uid']}"
            )

    def get_context_data(self, **kwargs):
        context = super(PCUpdate, self).get_context_data(**kwargs)

        site = context['site']
        form = context['form']
        pc = self.object
        params = self.request.GET or self.request.POST

        context['pc_list'] = site.pcs.all().extra(
            select={'lower_name': 'lower(name)'}
        ).order_by('lower_name')

        group_set = site.groups.all()

        selected_group_ids = form['pc_groups'].value()
        context['available_groups'] = group_set.exclude(
            pk__in=selected_group_ids
        )
        context['selected_groups'] = group_set.filter(
            pk__in=selected_group_ids
        )

        orderby = params.get('orderby', '-pk')
        if orderby not in JobSearch.VALID_ORDER_BY:
            orderby = '-pk'
        context['joblist'] = pc.jobs.order_by('status', 'pk').order_by(
            orderby,
            'pk'
        )

        if orderby.startswith('-'):
            context['orderby_key'] = orderby[1:]
            context['orderby_direction'] = 'desc'
        else:
            context['orderby_key'] = orderby
            context['orderby_direction'] = 'asc'

        context['orderby_base_url'] = pc.get_absolute_url() + '?'

        context['selected_pc'] = pc

        context['security_event'] = get_latest_security_event(pc)
        context['has_security_events'] = pc.securityevent_set.exclude(
            status=SecurityEvent.RESOLVED
        ).exclude(
            problem__level=SecurityProblem.NORMAL
        ).count() > 0

        return context

    def form_valid(self, form):
        pc = self.object
        groups_pre = set(pc.pc_groups.all())
        try:
            with transaction.atomic():
                pc.configuration.update_from_request(
                    self.request.POST, 'pc_config'
                )
                response = super(PCUpdate, self).form_valid(form)

                # If this PC has joined any groups that have policies attached
                # to them, then run their scripts (first making sure that this
                # PC is capable of doing so!)
                groups_post = set(pc.pc_groups.all())
                new_groups = groups_post.difference(groups_pre)
                supported = False
                for g in new_groups:
                    policy = g.ordered_policy
                    if policy:
                        if not supported:
                            if not pc.supports_ordered_job_execution():
                                raise OutdatedClientError(pc)
                            supported = True
                        for asc in policy:
                            asc.run_on(self.request.user, [pc])

        except OutdatedClientError as e:
            set_notification_cookie(
                response,
                _('Computer {0} must be upgraded in order to join a group '
                    'with scripts attached').format(e),
                error=True)
            return response

        set_notification_cookie(
            response,
            _('Computer %s updated') % pc.name
        )
        return response


class PCDelete(SiteMixin, SuperAdminOrThisSiteMixin, DeleteView):
    model = PC

    def get_object(self, queryset=None):
        return PC.objects.get(uid=self.kwargs['pc_uid'])

    def get_success_url(self):
        return '/site/{0}/computers/'.format(self.kwargs['site_uid'])


class GroupsView(SelectionMixin, SiteView):
    template_name = 'system/site_groups.html'
    selection_class = PCGroup
    class_display_name = 'group'

    def get_list(self):
        return self.object.groups.all().extra(
            select={'lower_name': 'lower(name)'}
        ).order_by('lower_name')

    def render_to_response(self, context):
        if('selected_group' in context):
            return HttpResponseRedirect('/site/%s/groups/%s/' % (
                context['site'].uid,
                context['selected_group'].url
            ))
        else:
            return HttpResponseRedirect(
                '/site/%s/groups/new/' % context['site'].uid,
            )


class UsersView(SelectionMixin, SiteView):

    template_name = 'system/site_users.html'
    selection_class = User
    lookup_field = 'username'

    def get_list(self):
        return self.object.users

    def render_to_response(self, context):
        if('selected_user' in context):
            return HttpResponseRedirect('/site/%s/users/%s/' % (
                context['site'].uid,
                context['selected_user'].username
            ))
        else:
            return HttpResponseRedirect(
                '/site/%s/new_user/' % context['site'].uid,
            )


class UsersMixin(object):
    def add_site_to_context(self, context):
        self.site = get_object_or_404(Site, uid=self.kwargs['site_uid'])
        context['site'] = self.site
        return context

    def add_userlist_to_context(self, context):
        if 'site' not in context:
            self.add_site_to_context(context)
        context['user_list'] = context['site'].users
        # Add information about outstanding security events.
        no_of_sec_events = get_no_of_sec_events(self.site)
        context['sec_events'] = no_of_sec_events
        return context


class UserCreate(CreateView, UsersMixin, SuperAdminOrThisSiteMixin):
    model = User
    form_class = UserForm
    lookup_field = 'username'
    template_name = 'system/users/create.html'

    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.get_form_class()
        form = super(UserCreate, self).get_form(form_class)
        form.prefix = 'create'
        return form

    def get_context_data(self, **kwargs):
        context = super(UserCreate, self).get_context_data(**kwargs)
        self.add_userlist_to_context(context)
        return context

    def form_valid(self, form):
        self.object = form.save()

        site = get_object_or_404(Site, uid=self.kwargs['site_uid'])
        user_profile = UserProfile.objects.create(
            user=self.object
        )
        SiteMembership.objects.create(
            user_profile=user_profile,
            site=site,
            site_user_type=form.cleaned_data["usertype"]
        )
        result = super(UserCreate, self).form_valid(form)
        return result

    def get_success_url(self):
        return '/site/%s/users/%s/' % (
            self.kwargs['site_uid'],
            self.object.username
        )


class UserUpdate(UpdateView, UsersMixin, SuperAdminOrThisSiteMixin):
    model = User
    form_class = UserForm
    template_name = 'system/users/update.html'

    def get_object(self, queryset=None):
        try:
            self.selected_user = User.objects.get(
                username=self.kwargs['username']
            )
        except User.DoesNotExist:
            raise Http404(
                f"der findes ingen bruger med id {self.kwargs['username']}"
            )
        return self.selected_user

    def get_context_data(self, **kwargs):
        self.context_object_name = 'selected_user'
        context = super(UserUpdate, self).get_context_data(**kwargs)
        self.add_userlist_to_context(context)

        site = get_object_or_404(Site, uid=self.kwargs['site_uid'])

        request_user = self.request.user
        user_profile = request_user.bibos_profile
        site_membership = user_profile.sitemembership_set.filter(
            site=site
        ).first()

        if site_membership:
            loginusertype = site_membership.site_user_type
        else:
            loginusertype = None

        context['selected_user'] = self.selected_user
        context['form'].setup_usertype_choices(
            loginusertype, request_user.is_superuser
        )

        context['create_form'] = UserForm(prefix='create')
        context['create_form'].setup_usertype_choices(
            loginusertype, request_user.is_superuser
        )

        return context

    def get_form_kwargs(self):
        kwargs = super(UserUpdate, self).get_form_kwargs()
        site = get_object_or_404(Site, uid=self.kwargs['site_uid'])
        kwargs["site"] = site

        return kwargs

    def form_valid(self, form):
        self.object = form.save()

        site = get_object_or_404(Site, uid=self.kwargs['site_uid'])
        user_profile = self.object.bibos_profile

        site_membership = user_profile.sitemembership_set.get(
            site=site,
            user_profile=user_profile
        )

        site_membership.site_user_type = form.cleaned_data["usertype"]
        site_membership.save()
        response = super(UserUpdate, self).form_valid(form)
        set_notification_cookie(
            response,
            _('User %s updated') % self.object.username
        )
        return response

    def get_success_url(self):
        return '/site/%s/users/%s/' % (
            self.kwargs['site_uid'],
            self.object.username
        )


class UserDelete(DeleteView, UsersMixin, SuperAdminOrThisSiteMixin):
    model = User
    template_name = 'system/users/delete.html'

    def get_object(self, queryset=None):
        self.selected_user = User.objects.get(username=self.kwargs['username'])
        return self.selected_user

    def get_context_data(self, **kwargs):
        context = super(UserDelete, self).get_context_data(**kwargs)
        self.add_userlist_to_context(context)
        context['selected_user'] = self.selected_user
        context['create_form'] = UserForm(prefix='create')

        return context

    def get_success_url(self):
        return '/site/%s/users/' % self.kwargs['site_uid']

    def delete(self, request, *args, **kwargs):
        response = super(UserDelete, self).delete(request, *args, **kwargs)
        set_notification_cookie(
            response,
            _('User %s deleted') % self.kwargs['username']
        )
        return response


class SiteCreate(CreateView, SuperAdminOnlyMixin):
    model = Site
    form_class = SiteForm
    slug_field = 'uid'

    def get_success_url(self):
        return '/sites/'


class SiteUpdate(UpdateView, SuperAdminOnlyMixin):
    model = Site
    form_class = SiteForm
    slug_field = 'uid'

    def get_success_url(self):
        return '/sites/'


class SiteDelete(DeleteView, SuperAdminOnlyMixin):
    model = Site
    slug_field = 'uid'

    def get_success_url(self):
        return '/sites/'


class ConfigurationEntryCreate(SiteMixin, CreateView,
                               SuperAdminOrThisSiteMixin):
    model = ConfigurationEntry
    form_class = ConfigurationEntryForm

    def form_valid(self, form):
        site = get_object_or_404(Site, uid=self.kwargs['site_uid'])
        self.object = form.save(commit=False)
        self.object.owner_configuration = site.configuration

        return super(ConfigurationEntryCreate, self).form_valid(form)

    def get_success_url(self):
        return '/site/{0}/configuration/'.format(self.kwargs['site_uid'])


class ConfigurationEntryUpdate(SiteMixin, UpdateView,
                               SuperAdminOrThisSiteMixin):
    model = ConfigurationEntry
    form_class = ConfigurationEntryForm

    def get_success_url(self):
        return '/site/{0}/configuration/'.format(self.kwargs['site_uid'])


class ConfigurationEntryDelete(SiteMixin, DeleteView,
                               SuperAdminOrThisSiteMixin):
    model = ConfigurationEntry

    def get_success_url(self):
        return '/site/{0}/configuration/'.format(self.kwargs['site_uid'])


class GroupCreate(SiteMixin, CreateView, SuperAdminOrThisSiteMixin):
    model = PCGroup
    form_class = GroupForm
    slug_field = 'uid'

    def get_context_data(self, **kwargs):
        context = super(GroupCreate, self).get_context_data(**kwargs)

        # We don't want to edit computers yet
        if 'pcs' in context['form'].fields:
            del context['form'].fields['pcs']

        return context

    def form_valid(self, form):
        site = get_object_or_404(Site, uid=self.kwargs['site_uid'])
        self.object = form.save(commit=False)
        self.object.site = site

        return super(GroupCreate, self).form_valid(form)


class Error(Exception):
    pass


class OutdatedClientError(Error):
    pass


class GroupUpdate(SiteMixin, SuperAdminOrThisSiteMixin, UpdateView):
    template_name = 'system/site_groups.html'
    form_class = GroupForm
    model = PCGroup

    def get_object(self, queryset=None):
        try:
            return PCGroup.objects.get(uid=self.kwargs['group_uid'])
        except PCGroup.DoesNotExist:
            raise Http404(
                f"der findes ingen gruppe med id {self.kwargs['group_uid']}"
            )

    def get_context_data(self, **kwargs):
        context = super(GroupUpdate, self).get_context_data(**kwargs)

        group = self.object
        form = context['form']
        site = context['site']

        pc_queryset = site.pcs.filter(is_active=True)
        form.fields['pcs'].queryset = pc_queryset

        selected_pc_ids = form['pcs'].value()
        context['available_pcs'] = pc_queryset.exclude(
            pk__in=selected_pc_ids
        )
        context['selected_pcs'] = pc_queryset.filter(
            pk__in=selected_pc_ids
        )

        context['selected_group'] = group

        context['newform'] = GroupForm()
        del context['newform'].fields['pcs']

        context['all_scripts'] = sorted(
            Script.objects.filter(
                Q(site=site) | Q(site=None),
                is_security_script=False
            ).exclude(
                site__name='system'
            ), key=lambda s: s.name.lower())

        return context

    def form_valid(self, form):
        # Capture a view of the group's PCs and policy scripts before the
        # update
        members_pre = set(self.object.pcs.all())
        policy_pre = set(self.object.policy.all())

        try:
            with transaction.atomic():
                self.object.configuration.update_from_request(
                    self.request.POST, 'group_configuration'
                )
                self.object.update_policy_from_request(
                    self.request, 'group_policies'
                )

                response = super(GroupUpdate, self).form_valid(form)

                members_post = set(self.object.pcs.all())
                policy_post = set(self.object.policy.all())

                # Work out which PCs and policy scripts have come and gone
                surviving_members = members_post.intersection(members_pre)
                new_members = members_post.difference(members_pre)
                new_policy = policy_post.difference(policy_pre)

                # If we have a policy, make sure all group members actually
                # support ordered job execution
                if len(policy_post) > 0:
                    for g in members_post:
                        if not g.supports_ordered_job_execution():
                            raise OutdatedClientError(g)

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
                    response,
                    _('Group %s updated') % self.object.name
                )
                return response
        except OutdatedClientError as e:
            set_notification_cookie(
                response,
                _('Computer {0} must be upgraded in order to join a group'
                    ' with scripts attached').format(e),
                error=True)
            return response
        except MandatoryParameterMissingError as e:
            # If this happens, it happens *before* we have a valid
            # HttpResponse, so make one with form_invalid()
            response = self.form_invalid(form)
            parameter = e.args[0]
            set_notification_cookie(
                response,
                _('No value was specified for the mandatory input "{0}"'
                    ' of script "{1}"').format(
                        parameter.name, parameter.script.name),
                error=True)
            return response

    def form_invalid(self, form):
        return super(GroupUpdate, self).form_invalid(form)


class GroupDelete(SiteMixin, SuperAdminOrThisSiteMixin, DeleteView):
    model = PCGroup

    def get_object(self, queryset=None):
        return PCGroup.objects.get(uid=self.kwargs['group_uid'])

    def get_success_url(self):
        return '/site/{0}/groups/'.format(self.kwargs['site_uid'])

    def delete(self, request, *args, **kwargs):
        name = self.get_object().name
        response = super(GroupDelete, self).delete(request, *args, **kwargs)
        set_notification_cookie(
            response,
            _('Group %s deleted') % name
        )
        return response


class SecurityProblemsView(SelectionMixin, SiteView):

    template_name = 'system/site_security_problems.html'
    selection_class = SecurityProblem
    class_display_name = 'security_problem'

    def get_list(self):
        return self.object.security_problems.all().extra(
            select={'lower_name': 'lower(name)'}
        ).order_by('lower_name')

    def render_to_response(self, context):
        if 'selected_security_problem' in context:
            return HttpResponseRedirect('/site/%s/security_problems/%s/' % (
                context['site'].uid,
                context['selected_security_problem'].uid
            ))
        else:
            """
            return HttpResponseRedirect(
                '/site/%s/security_problems/new/' % context['site'].uid,
            )
            """
            site = context['site']
            context['newform'] = SecurityProblemForm()
            context['newform'].fields[
                'alert_users'
            ].queryset = User.objects.filter(bibos_profile__sites=site)
            context['newform'].fields[
                'alert_groups'
            ].queryset = site.groups.all()
            # Limit list of scripts to only include security scripts.
            script_set = Script.objects.filter(
                Q(site__isnull=True) | Q(site=site)
            ).filter(is_security_script=True)
            context['newform'].fields['script'].queryset = script_set

            return super(
                SecurityProblemsView, self
            ).render_to_response(context)


class SecurityProblemCreate(SiteMixin, CreateView, SuperAdminOrThisSiteMixin):
    template_name = 'system/site_security_problems.html'
    model = SecurityProblem
    fields = '__all__'

    def get_success_url(self):
        return '/site/{0}/security_problems/'.format(self.kwargs['site_uid'])


class SecurityProblemUpdate(SiteMixin, UpdateView, SuperAdminOrThisSiteMixin):
    template_name = 'system/site_security_problems.html'
    model = SecurityProblem
    form_class = SecurityProblemForm

    def get_object(self, queryset=None):
        try:
            return SecurityProblem.objects.get(
                    uid=self.kwargs['uid'], site__uid=self.kwargs['site_uid']
            )
        except SecurityProblem.DoesNotExist:
            raise Http404(
                f"der findes ingen sikkerhedsregel med id {self.kwargs['uid']}"
            )

    def get_context_data(self, **kwargs):

        context = super(SecurityProblemUpdate, self).get_context_data(**kwargs)

        site = context['site']
        form = context['form']
        group_set = site.groups.all()
        selected_group_ids = form['alert_groups'].value()
        context['available_groups'] = group_set.exclude(
            pk__in=selected_group_ids
        )
        context['selected_groups'] = group_set.filter(
            pk__in=selected_group_ids
        )

        user_set = User.objects.filter(bibos_profile__sites=site)
        selected_user_ids = form['alert_users'].value()
        context['available_users'] = user_set.exclude(
            pk__in=selected_user_ids
        )
        context['selected_users'] = user_set.filter(
            pk__in=selected_user_ids
        )
        # Limit list of scripts to only include security scripts.
        script_set = Script.objects.filter(
            Q(site__isnull=True) | Q(site=site)
        ).filter(is_security_script=True)
        form.fields['script'].queryset = script_set

        # TODO: If the JS available/selected stuff above works out, the next
        # two lines can be deleted.
        form.fields['alert_users'].queryset = user_set
        form.fields['alert_groups'].queryset = group_set
        # Extra fields
        context['selected_security_problem'] = self.object
        context['newform'] = SecurityProblemForm()
        context['newform'].fields['script'].queryset = script_set
        context['newform'].fields['alert_users'].queryset = user_set
        context['newform'].fields['alert_groups'].queryset = group_set

        return context

    def get_success_url(self):
        return '/site/{0}/security_problems/'.format(self.kwargs['site_uid'])


class SecurityProblemDelete(SiteMixin, DeleteView, SuperAdminOrThisSiteMixin):
    model = SecurityProblem
    # form_class = <hopefully_not_necessary>

    def get_object(self, queryset=None):
        return SecurityProblem.objects.get(uid=self.kwargs['uid'],
                                           site__uid=self.kwargs['site_uid'])

    def get_success_url(self):
        return '/site/{0}/security_problems/'.format(self.kwargs['site_uid'])


class SecurityEventsView(SiteView):
    template_name = 'system/site_security.html'

    def get_context_data(self, **kwargs):
        # First, get basic context from superclass
        context = super(SecurityEventsView, self).get_context_data(**kwargs)
        # Supply extra info as needed.
        level_preselected = set([
            SecurityProblem.CRITICAL,
            SecurityProblem.HIGH
        ])
        context['level_choices'] = [
            {
                'name': name,
                'value': value,
                'label': SecurityProblem.LEVEL_TO_LABEL[value],
                'checked':
                'checked="checked' if value in level_preselected else ''
            } for (value, name) in SecurityProblem.LEVEL_CHOICES
        ]
        status_preselected = set([
            SecurityEvent.NEW,
            SecurityEvent.ASSIGNED
        ])
        context['status_choices'] = [
            {
                'name': name,
                'value': value,
                'label': SecurityEvent.STATUS_TO_LABEL[value],
                'checked':
                'checked="checked' if value in status_preselected else ''
            } for (value, name) in SecurityEvent.STATUS_CHOICES
        ]

        if 'pc_uid' in self.kwargs:
            context['pc_uid'] = self.kwargs['pc_uid']
        return context


class SecurityEventSearch(SiteMixin, JSONResponseMixin, BaseListView):
    paginate_by = 20
    http_method_names = ['get']
    VALID_ORDER_BY = []
    for i in [
        'pk', 'problem__name', 'occurred_time', 'assigned_user__username'
    ]:
        VALID_ORDER_BY.append(i)
        VALID_ORDER_BY.append('-' + i)

    def render_to_response(self, context, **response_kwargs):
        return self.render_to_json_response(context, **response_kwargs)

    def get_queryset(self):
        site = get_object_or_404(Site, uid=self.kwargs[self.site_uid])
        queryset = SecurityEvent.objects.all()
        params = self.request.GET

        query = {'problem__site': site}
        if params.get('pc', None):
            query['pc__uid'] = params['pc']

        if 'level' in params:
            query['problem__level__in'] = params.getlist('level')

        if 'status' in params:
            query['status__in'] = params.getlist('status')

        orderby = params.get('orderby', '-pk')
        if orderby not in SecurityEventSearch.VALID_ORDER_BY:
            orderby = '-pk'

        queryset = queryset.filter(**query).order_by(
            orderby,
            'pk'
        )

        return queryset

    def get_data(self, context):
        site = context["site"]
        page_obj = context["page_obj"]
        paginator = context["paginator"]
        adjacent_pages = 2
        page_numbers = [
            n for n in range(
                page_obj.number - adjacent_pages,
                page_obj.number + adjacent_pages + 1
            ) if n > 0 and n <= paginator.num_pages
        ]

        result = {
            "count": paginator.count,
            "num_pages": paginator.num_pages,
            "page": page_obj.number,
            "page_numbers": page_numbers,
            "has_next": page_obj.has_next(),
            "next_page_number": (
                page_obj.next_page_number()
                if page_obj.has_next()
                else None
            ),
            "has_previous": page_obj.has_previous(),
            "previous_page_number": (
                page_obj.previous_page_number()
                if page_obj.has_previous()
                else None
            ),
            "results": [{
                'pk': event.pk,
                'site_uid': site.uid,
                'problem_name': event.problem.name,
                'pc_id': event.pc.id,
                'occurred': event.ocurred_time.strftime("%Y-%m-%d %H:%M:%S"),
                'status': event.get_status_display(),
                'status_label': event.STATUS_TO_LABEL[event.status],
                'level': SecurityProblem.LEVEL_TO_LABEL[
                    event.problem.level
                ] + '',
                'pc_name': event.pc.name,
                'assigned_user': (event.assigned_user.username if
                                  event.assigned_user else '')
                } for event in page_obj]
        }

        return result


class SecurityEventUpdate(SiteMixin, UpdateView, SuperAdminOrThisSiteMixin):
    model = SecurityEvent
    fields = ['assigned_user', 'status', 'note']

    def get_object(self, queryset=None):
        return SecurityEvent.objects.get(id=self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        context = super(SecurityEventUpdate, self).get_context_data(**kwargs)

        qs = context["form"].fields["assigned_user"].queryset
        qs = qs.filter(
                Q(bibos_profile__sites=self.get_object().pc.site) |
                Q(is_superuser=True))
        context["form"].fields["assigned_user"].queryset = qs

        # Set fields to read-only
        return context

    def post(self, request, *args, **kwargs):
        result = super(SecurityEventUpdate,
                       self).post(request, *args, **kwargs)
        return result

    def get_success_url(self):
        return reverse("security_events", args=[self.kwargs['site_uid']])


documentation_menu_items = [
    ('', 'OS2borgerPC Administration'),
    ('status', 'Status'),
    ('site_configuration', 'Site-konfiguration'),
    ('computers', 'Computere'),
    ('groups', 'Grupper'),
    ('jobs', 'Jobs'),
    ('scripts', 'Scripts'),
    ('users', 'Brugere'),

    ('', 'Installation af OS2borgerPC'),
    ('install_dvd', 'Installation via DVD'),
    ('install_usb', 'Installation via USB'),
    ('install_network', 'Installation via netværk'),
    ('pdf_guide', 'Brugervenlig installationsguide (PDF)'),
    ('creating_security_problems',
     'Oprettelse af Sikkerhedsovervågning (PDF)'),

    ('', 'OS2borgerPC-gateway'),
    ('gateway_install', 'Installation af OS2borgerPC-gateway'),
    ('gateway_admin', 'Administration af gateway'),
    ('gateway_use', 'Anvendelse af gateway på OS2borgerPC-maskiner'),
    ('', 'Om OS2borgerPC-Admin'),
    ('om_os2borgerpc_admin', 'Om OS2borgerPC-Admin'),

    ('', 'Teknisk dokumentation'),
    ('tech/os2borgerpc-image', 'OS2borgerPC Desktop Image'),
    ('tech/os2borgerpc-admin', 'OS2borgerPC Admin Site'),
    ('tech/os2borgerpc-server-image', 'OS2borgerPC Server Image'),
    ('tech/os2borgerpc-client', 'OS2borgerPC Client'),

]


class DocView(TemplateView):
    docname = 'status'

    def template_exists(self, subpath):
        fullpath = os.path.join(settings.DOCUMENTATION_DIR, subpath)
        return os.path.isfile(fullpath)

    def get_context_data(self, **kwargs):  # noqa
        if 'name' in self.kwargs:
            self.docname = self.kwargs['name']
        else:
            # This will be mapped to documentation/index.html
            self.docname = 'index'

        if self.docname.find("..") != -1:
            raise Http404

        # Try <docname>.html and <docname>/index.html
        name_templates = [
            'documentation/{0}.html',
            'documentation/{0}/index.html'
        ]

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
        context['docmenuitems'] = documentation_menu_items
        docnames = self.docname.split("/")

        context['menu_active'] = docnames[0]

        # Set heading according to chosen item
        current_heading = None
        for link, name in context['docmenuitems']:
            if link == '':
                current_heading = name
            elif link == docnames[0]:
                context['docheading'] = current_heading
                break

        # Add a submenu if it exists
        submenu_template = "documentation/" + docnames[0] + "/__submenu__.html"
        if self.template_exists(submenu_template):
            context['submenu_template'] = submenu_template

        if len(docnames) > 1 and docnames[1]:
            # Don't allow direct access to submenus
            if docnames[1] == '__submenu__':
                raise Http404
            context['submenu_active'] = docnames[1]

        params = self.request.GET or self.request.POST
        back_link = params.get('back')
        if back_link is None:
            referer = self.request.META.get('HTTP_REFERER')
            if referer and referer.find("/documentation/") == -1:
                back_link = referer
        if back_link:
            context['back_link'] = back_link

        return context


class JSONSiteSummary(JSONResponseMixin, SiteView):
    """Produce a JSON document summarising the state of all of the computers in
    a site.
    """

    interesting_properties = [
        'id', 'name', 'description', 'configuration_id', 'site_id',
        'is_active', 'creation_time', 'last_seen', 'location']

    def get_context_data(self, **kwargs):
        pcs = []
        for p in self.object.pcs.all():
            pc = {}
            for pn in JSONSiteSummary.interesting_properties:
                pv = getattr(p, pn)
                # Don't convert these types to string representations...
                if (pv is None or isinstance(pv, bool)
                        or isinstance(pv, float) or isinstance(pv, int)):
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

    template_name = 'system/site_image_versions.html'
    model = ImageVersion
    context_object_name = 'image_versions'
    selection_class = ImageVersion
    class_display_name = 'image_version'

    def get_context_data(self, **kwargs):
        context = super(ImageVersionsView, self).get_context_data(**kwargs)

        site_uid = self.kwargs.get('site_uid')
        site_obj = Site.objects.get(uid=site_uid)
        last_pay_date = site_obj.last_version

        if not last_pay_date:

            context["site_allowed"] = False

        else:

            context["site_allowed"] = True

            # excluding versions where
            # image release date > client's last pay date.
            versions = ImageVersion.objects.exclude(rel_date__gt=last_pay_date)

            major_versions_set = set()
            for minor_version in versions:
                major_versions_set.add(minor_version.img_vers[:1])

            major_versions_list = list(major_versions_set)
            major_versions_list.sort(reverse=True)

            if len(major_versions_list) > 0:

                context["major_versions"] = major_versions_list

                url_ref_vers = self.kwargs.get(
                    'major_version',
                    major_versions_list[0]
                    )

                context["selected_image_version"] = url_ref_vers

                minor_versions = versions.filter(
                    img_vers__startswith=url_ref_vers
                    )

                context["minor_versions"] = minor_versions

        return context
