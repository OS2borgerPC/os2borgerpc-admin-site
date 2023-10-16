import datetime
from email.policy import default
import random
from statistics import mode
import string

from dateutil.relativedelta import relativedelta

from django.db import models, transaction
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.validators import MinValueValidator

from markdownx.utils import markdownify
from markdownx.models import MarkdownxField

from system.mixins import AuditModelMixin
from system.managers import SecurityEventQuerySet

"""The following variables define states of objects like jobs or PCs. It is
used for labeling in the GUI."""

# PC States
NEW = _("status:New")
FAIL = _("status:Fail")
OK = ""

# Priorities
INFO = "info"
WARNING = "warning"
IMPORTANT = "important"
NONE = ""


# Consider adding SecurityEvent states to this as well if that can make sense/work
class EventLevels:
    CRITICAL = "Critical"
    HIGH = "High"
    NORMAL = "Normal"

    LEVEL_TRANSLATIONS = {
        CRITICAL: _("securitylevel:Critical"),
        HIGH: _("securitylevel:High"),
        NORMAL: _("securitylevel:Normal"),
    }

    LEVEL_CHOICES = (
        (CRITICAL, LEVEL_TRANSLATIONS[CRITICAL]),
        (HIGH, LEVEL_TRANSLATIONS[HIGH]),
        (NORMAL, LEVEL_TRANSLATIONS[NORMAL]),
    )

    LEVEL_TO_LABEL = {
        CRITICAL: "label-important",
        HIGH: "label-warning",
        NORMAL: "label-gentle-warning",
    }


class Configuration(models.Model):
    """This class contains/represents the configuration of a Site, a
    a PC Group or a PC."""

    # Doesn't need any actual fields, it seems. Should not exist independently
    # of the classes to which it may be aggregated.
    name = models.CharField(max_length=255, unique=True)

    def update_from_request(self, req_params, submit_name):
        seen_set = set()

        existing_set = set(cnf.pk for cnf in self.entries.all())

        unique_names = set(req_params.getlist(submit_name, []))
        for pk in unique_names:
            key_param = "%s_%s_key" % (submit_name, pk)
            value_param = "%s_%s_value" % (submit_name, pk)

            key = req_params.getlist(key_param, "")
            value = req_params.getlist(value_param, "")

            if pk.startswith("new_"):
                # Create one or more new entries
                for k, v in zip(key, value):
                    cnf = ConfigurationEntry(key=k, value=v, owner_configuration=self)
                    cnf.save()
            else:
                # Update submitted entry
                cnf = ConfigurationEntry.objects.get(pk=pk)
                cnf.key = key[0]
                cnf.value = value[0]
                seen_set.add(cnf.pk)
                cnf.save()

        # Delete entries that were not in the submitted data
        for pk in existing_set - seen_set:
            cnf = ConfigurationEntry.objects.get(pk=pk)
            cnf.delete()

    def remove_entry(self, key):
        return self.entries.filter(key=key).delete()

    def update_entry(self, key, value):
        try:
            e = self.entries.get(key=key)
            e.value = value
        except ConfigurationEntry.DoesNotExist:
            e = ConfigurationEntry(owner_configuration=self, key=key, value=value)
        finally:
            e.save()

    def get(self, key, default=None):
        """Return value of the entry corresponding to key if it exists, None
        otherwise."""
        result = None
        try:
            e = self.entries.get(key=key)
            result = e.value
        except ConfigurationEntry.DoesNotExist:
            if default is not None:
                result = default
            else:
                raise

        return result

    def __str__(self):
        return self.name


class ConfigurationEntry(models.Model):
    """A single configuration entry - always part of an entire
    configuration."""

    key = models.CharField(max_length=32)
    value = models.CharField(max_length=4096)
    owner_configuration = models.ForeignKey(
        Configuration,
        related_name="entries",
        verbose_name=_("owner configuration"),
        on_delete=models.CASCADE,
    )

    class Meta:
        ordering = ["key"]


class Site(models.Model):
    """A site which we wish to admin"""

    name = models.CharField(verbose_name=_("name"), max_length=255)
    uid = models.CharField(verbose_name=_("UID"), max_length=255, unique=True)
    configuration = models.ForeignKey(Configuration, on_delete=models.PROTECT)
    paid_for_access_until = models.DateField(
        verbose_name=_("Paid for access until this date"), null=True, blank=True
    )
    created = models.DateTimeField(
        verbose_name=_("created"), auto_now_add=True, null=True
    )
    # Official library number
    # https://slks.dk/omraader/kulturinstitutioner/biblioteker/biblioteksstandardisering/biblioteksnumre

    # Necessary for customers who wish to integrate with standard library login.
    isil = models.CharField(
        verbose_name="ISIL",
        max_length=10,
        blank=True,
        help_text=_(
            "Necessary for customers who wish to"
            " integrate with standard library login"
        ),
    )
    cicero_user = models.CharField(
        verbose_name=_("Username for Cicero API"),
        max_length=100,
        blank=True,
        help_text=_("Necessary for customers who wish to integrate with Cicero login"),
    )
    cicero_password = models.CharField(
        verbose_name=_("Password for Cicero API"),
        max_length=255,
        blank=True,
    )
    user_login_duration = models.DurationField(
        verbose_name=_("Login duration"),
        help_text=_("Login duration when integrating with library login"),
        null=True,
        blank=True,
        default=datetime.timedelta(hours=1),
    )
    user_quarantine_duration = models.DurationField(
        verbose_name=_("Quarantine duration"),
        help_text=_("Quarantine period when integrating with library login"),
        null=True,
        blank=True,
        default=datetime.timedelta(hours=4),
    )
    rerun_asc = models.BooleanField(
        verbose_name=_(
            "Automatically rerun associated scripts when you update their arguments"
        ),
        default=False,
    )

    class Meta:
        ordering = ["name"]

    @property
    def users(self):
        users = (
            User.objects.filter(user_profile__sites=self)
            .extra(select={"lower_name": "lower(username)"})
            .order_by("lower_name")
        )

        return users

    @property
    def url(self):
        return self.uid

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Customize behaviour when saving a site object."""
        # Before actual save
        # 1. uid should consist of lowercase letters.
        self.uid = self.uid.lower()
        # 2. Create related configuration object if necessary.
        is_new = self.id is None

        try:
            conf = self.configuration
        except Configuration.DoesNotExist:
            conf = None

        if is_new and conf is None:
            try:
                self.configuration = Configuration.objects.get(name=self.uid)
            except Configuration.DoesNotExist:
                self.configuration = Configuration.objects.create(name=self.uid)

        # Perform save
        super(Site, self).save(*args, **kwargs)

        # After save
        pass

    def get_absolute_url(self):
        return reverse("settings", kwargs={"slug": self.uid})


class FeaturePermission(models.Model):
    name = models.CharField(verbose_name=_("name"), max_length=255)
    uid = models.CharField(verbose_name=_("UID"), max_length=255, unique=True)
    sites = models.ManyToManyField(
        Site,
        related_name="feature_permission",
        verbose_name=_("sites with access"),
        blank=True,
    )

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


class Error(Exception):
    pass


class MandatoryParameterMissingError(Error):
    pass


class WakeChangeEvent(models.Model):
    EVENT_TYPE_CHOICES = (
        ("ALTERED_HOURS", _("event_type:Altered Hours")),
        ("CLOSED", _("event_type:Closed")),
    )

    name = models.CharField(verbose_name=_("name"), max_length=60)
    date_start = models.DateField(verbose_name=_("date start"))
    time_start = models.TimeField(verbose_name=_("time start"), null=True, blank=True)
    date_end = models.DateField(verbose_name=_("date end"))
    time_end = models.TimeField(verbose_name=_("time end"), null=True, blank=True)
    # Represented by an on-off switch in the frontend
    type = models.CharField(
        verbose_name=_("type"),
        max_length=15,
        choices=EVENT_TYPE_CHOICES,
        default=EVENT_TYPE_CHOICES[0][0],
    )
    site = models.ForeignKey(
        Site, related_name="wake_change_events", on_delete=models.CASCADE
    )

    def __str__(self):
        return (
            f"{self.name}: {self.date_start.day}/{self.date_start.month}/{str(self.date_start.year)[2:]}"
            + (
                f" - {self.date_end.day}/{self.date_end.month}/{str(self.date_end.year)[2:]}"
                if self.date_start != self.date_end
                else ""
            )
        )

    def get_absolute_url(self):
        return reverse("wake_change_event", args=(self.site.uid, self.id))

    class Meta:
        ordering = ["date_start"]


class WakeWeekPlan(models.Model):
    # Sleep state choices for the field below - and their translations
    # These are based on what "rtcwake" supports
    SLEEP_STATE_CHOICES = (
        ("STANDBY", _("sleep_state:Standby")),
        ("FREEZE", _("sleep_state:Freeze")),
        ("MEM", _("sleep_state:Mem")),
        ("OFF", _("sleep_state:Off")),
    )

    default_open = datetime.time(8, 0, 0, 0)
    default_close = datetime.time(20, 0, 0, 0)

    name = models.CharField(verbose_name=_("name"), max_length=60)
    enabled = models.BooleanField(verbose_name=_("enabled"), default=True)
    sleep_state = models.CharField(
        verbose_name=_("sleep state"),
        max_length=10,
        choices=SLEEP_STATE_CHOICES,
        default=SLEEP_STATE_CHOICES[3][0],
    )
    monday_on = models.TimeField(
        verbose_name=_("monday on"), null=True, blank=True, default=default_open
    )
    monday_off = models.TimeField(
        verbose_name=_("monday off"), null=True, blank=True, default=default_close
    )
    monday_open = models.BooleanField(verbose_name=_("monday open"), default=True)
    tuesday_on = models.TimeField(
        verbose_name=_("tuesday on"), null=True, blank=True, default=default_open
    )
    tuesday_off = models.TimeField(
        verbose_name=_("tuesday off"), null=True, blank=True, default=default_close
    )
    tuesday_open = models.BooleanField(verbose_name=_("tuesday open"), default=True)
    wednesday_on = models.TimeField(
        verbose_name=_("wednesday on"), null=True, blank=True, default=default_open
    )
    wednesday_off = models.TimeField(
        verbose_name=_("wednesday off"), null=True, blank=True, default=default_close
    )
    wednesday_open = models.BooleanField(verbose_name=_("wednesday open"), default=True)
    thursday_on = models.TimeField(
        verbose_name=_("thursday on"), null=True, blank=True, default=default_open
    )
    thursday_off = models.TimeField(
        verbose_name=_("thursday off"), null=True, blank=True, default=default_close
    )
    thursday_open = models.BooleanField(verbose_name=_("thursday open"), default=True)
    friday_on = models.TimeField(
        verbose_name=_("friday on"), null=True, blank=True, default=default_open
    )
    friday_off = models.TimeField(
        verbose_name=_("friday off"), null=True, blank=True, default=default_close
    )
    friday_open = models.BooleanField(verbose_name=_("friday open"), default=True)
    saturday_on = models.TimeField(
        verbose_name=_("saturday on"), null=True, blank=True, default=default_open
    )
    saturday_off = models.TimeField(
        verbose_name=_("saturday off"), null=True, blank=True, default=default_close
    )
    saturday_open = models.BooleanField(verbose_name=_("saturday open"), default=False)
    sunday_on = models.TimeField(
        verbose_name=_("sunday on"), null=True, blank=True, default=default_open
    )
    sunday_off = models.TimeField(
        verbose_name=_("sunday off"), null=True, blank=True, default=default_close
    )
    sunday_open = models.BooleanField(verbose_name=_("sunday open"), default=False)
    site = models.ForeignKey(
        Site, related_name="wake_week_plans", on_delete=models.CASCADE
    )
    wake_change_events = models.ManyToManyField(
        WakeChangeEvent,
        related_name="wake_week_plans",
        verbose_name=_("wake change events"),
    )

    def get_absolute_url(self):
        return reverse("wake_plan", args=(self.site.uid, self.id))

    def get_script_arguments(self):
        args = []
        if self.monday_open:
            args.append(self.get_script_argument(self.monday_on))
            args.append(self.get_script_argument(self.monday_off))
        else:
            args.extend(["None", "None"])
        if self.tuesday_open:
            args.append(self.get_script_argument(self.tuesday_on))
            args.append(self.get_script_argument(self.tuesday_off))
        else:
            args.extend(["None", "None"])
        if self.wednesday_open:
            args.append(self.get_script_argument(self.wednesday_on))
            args.append(self.get_script_argument(self.wednesday_off))
        else:
            args.extend(["None", "None"])
        if self.thursday_open:
            args.append(self.get_script_argument(self.thursday_on))
            args.append(self.get_script_argument(self.thursday_off))
        else:
            args.extend(["None", "None"])
        if self.friday_open:
            args.append(self.get_script_argument(self.friday_on))
            args.append(self.get_script_argument(self.friday_off))
        else:
            args.extend(["None", "None"])
        if self.saturday_open:
            args.append(self.get_script_argument(self.saturday_on))
            args.append(self.get_script_argument(self.saturday_off))
        else:
            args.extend(["None", "None"])
        if self.sunday_open:
            args.append(self.get_script_argument(self.sunday_on))
            args.append(self.get_script_argument(self.sunday_off))
        else:
            args.extend(["None", "None"])
        custom_string = ""
        today = datetime.date.today()
        for event in self.wake_change_events.all():
            if event.type == "CLOSED" and event.date_end >= today:
                custom_string += (
                    ";".join(
                        [
                            event.date_start.strftime("%d-%m-%Y"),
                            event.date_end.strftime("%d-%m-%Y"),
                            "None",
                            "None",
                        ]
                    )
                    + "|"
                )
            elif event.type == "ALTERED_HOURS" and event.date_end >= today:
                custom_string += (
                    ";".join(
                        [
                            event.date_start.strftime("%d-%m-%Y"),
                            event.date_end.strftime("%d-%m-%Y"),
                            self.get_script_argument(event.time_start),
                            self.get_script_argument(event.time_end),
                        ]
                    )
                    + "|"
                )
        args.append(custom_string[:-1])
        args.append(self.sleep_state)

        return args

    def get_script_argument(self, on_or_off_time):
        if on_or_off_time is None:
            return "None"
        else:
            return f"{on_or_off_time.hour}:{on_or_off_time.minute}"

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


class PCGroup(models.Model):
    """Groups of PCs. Each PC may be in zero or many groups."""

    name = models.CharField(verbose_name=_("name"), max_length=255)
    description = models.TextField(
        verbose_name=_("description"), max_length=1024, blank=True
    )
    site = models.ForeignKey(Site, related_name="groups", on_delete=models.CASCADE)
    configuration = models.ForeignKey(Configuration, on_delete=models.PROTECT)
    wake_week_plan = models.ForeignKey(
        WakeWeekPlan, related_name="groups", on_delete=models.SET_NULL, null=True
    )

    supervisors = models.ManyToManyField(
        User,
        related_name="pc_groups",
        verbose_name=_("supervisors"),
        blank=True,
    )

    def __str__(self):
        return self.name

    @property
    def url(self):
        return self.id

    def save(self, *args, **kwargs):
        """Customize behaviour when saving a group object."""
        # Before actual save
        is_new = self.id is None
        if is_new and self.name:
            related_name = "Group: " + self.name
            self.configuration, new = Configuration.objects.get_or_create(
                name=related_name
            )
        # Perform save
        super(PCGroup, self).save(*args, **kwargs)

        # After save
        pass

    @transaction.atomic
    def update_associated_script_positions(self):
        groups_policy_scripts = [asc for asc in self.policy.all().order_by("position")]
        for count, asc in enumerate(groups_policy_scripts):
            asc.position = count
            asc.save()

    def update_policy_from_request(self, request, submit_name):
        req_params = request.POST
        req_files = request.FILES

        existing_set = set(asc.pk for asc in self.policy.all())
        old_params = set()
        updated_policy_scripts = set()

        for pk in existing_set:
            asc = AssociatedScript.objects.get(pk=pk)
            old_params.update(asc.parameters.all())
            asc.delete()

        for i, pk in enumerate(req_params.getlist(submit_name, [])):
            script_param = "%s_%s" % (submit_name, pk)

            script_pk = int(req_params.get(script_param, None))
            script = Script.objects.get(pk=script_pk)
            asc = AssociatedScript(group=self, script=script, position=i)
            if not pk.startswith("new_"):
                asc.pk = pk
            asc.save()

            for old_param in old_params:
                if old_param.associated_script_id == asc.pk:
                    old_param.associated_script = asc
                    old_param.save()

            for inp in script.ordered_inputs:
                try:
                    par = AssociatedScriptParameter.objects.get(
                        associated_script=asc, input=inp
                    )
                except AssociatedScriptParameter.DoesNotExist:
                    par = AssociatedScriptParameter(associated_script=asc, input=inp)
                param_name = "{0}_param_{1}".format(script_param, inp.position)
                if inp.value_type == Input.FILE:
                    if param_name not in req_files or not req_files[param_name]:
                        if par.pk is not None:
                            # Don't blank existing values
                            continue
                        elif inp.mandatory:
                            raise MandatoryParameterMissingError(inp)
                        else:
                            pass
                    else:
                        if (
                            par.pk is not None
                            and par.file_value != req_files[param_name]
                        ):
                            updated_policy_scripts.add(par.associated_script)
                        par.file_value = req_files[param_name]
                else:
                    if param_name not in req_params or (
                        not req_params[param_name] and inp.value_type == Input.PASSWORD
                    ):
                        if par.pk is not None:
                            # Don't blank existing values
                            continue
                        elif inp.mandatory:
                            raise MandatoryParameterMissingError(inp)
                        else:
                            pass
                    elif not req_params[param_name] and inp.mandatory:
                        raise MandatoryParameterMissingError(inp)
                    else:
                        if (
                            par.pk is not None
                            and par.string_value != req_params[param_name]
                        ):
                            updated_policy_scripts.add(par.associated_script)
                        par.string_value = req_params[param_name]
                par.save()
        return updated_policy_scripts

    @property
    def ordered_policy(self):
        return self.policy.all().order_by("position")

    def get_absolute_url(self):
        return reverse("group", args=(self.site.uid, self.id))

    class Meta:
        ordering = ["name"]


class PC(models.Model):
    """This class represents one PC, i.e. one client of the admin system."""

    mac = models.CharField(verbose_name=_("MAC"), max_length=255, blank=True)
    name = models.CharField(verbose_name=_("name"), max_length=255)
    uid = models.CharField(
        verbose_name=_("UID"), max_length=255, db_index=True, unique=True
    )
    description = models.CharField(
        verbose_name=_("description"), max_length=1024, blank=True
    )
    configuration = models.ForeignKey(Configuration, on_delete=models.PROTECT)
    pc_groups = models.ManyToManyField(PCGroup, related_name="pcs", blank=True)
    site = models.ForeignKey(Site, related_name="pcs", on_delete=models.CASCADE)
    is_activated = models.BooleanField(verbose_name=_("activated"), default=False)
    created = models.DateTimeField(
        verbose_name=_("created"), auto_now_add=True, null=True
    )
    last_seen = models.DateTimeField(verbose_name=_("last seen"), null=True, blank=True)
    location = models.CharField(
        verbose_name=_("location"), max_length=1024, blank=True, default=""
    )

    @property
    def online(self):
        """A PC being online is defined as last seen less than 5 minutes ago."""
        if not self.last_seen:
            return False
        now = timezone.now()
        return self.last_seen >= now - relativedelta(minutes=5)

    class Status:
        """This class represents the status of af PC. We may want to do
        something similar for jobs."""

        def __init__(self, state, priority):
            self.state = state
            self.priority = priority

    @property
    def status(self):
        if not self.is_activated:
            return self.Status(NEW, INFO)
        else:
            # Get a list of all jobs associated with this PC and see if any of
            # them failed.
            failed_jobs = self.jobs.filter(status=Job.FAILED)
            if len(failed_jobs) > 0:
                # Only UNHANDLED failed jobs, please.
                return self.Status(FAIL, IMPORTANT)
            else:
                return self.Status(OK, None)

    def get_list_of_configurations(self):
        configs = [self.site.configuration]
        configs.extend([g.configuration for g in self.pc_groups.all()])
        configs.append(self.configuration)
        return configs

    def get_config_value(self, key, default=None):
        value = default
        configs = self.get_list_of_configurations()
        for conf in configs:
            try:
                entry = conf.entries.get(key=key)
                value = entry.value
            except ConfigurationEntry.DoesNotExist:
                pass
        return value

    def get_full_config(self):
        result = {}
        configs = self.get_list_of_configurations()
        for conf in configs:
            for entry in conf.entries.all():
                result[entry.key] = entry.value
        if "mac" not in result.keys():
            result["mac"] = self.mac
        result["uid"] = self.uid
        return result

    def get_merged_config_list(self, key, default=None):
        result = default[:] if default is not None else []

        configs = [self.site.configuration]
        configs.extend([g.configuration for g in self.pc_groups.all()])
        configs.append(self.configuration)

        for conf in configs:
            try:
                entry = conf.entries.get(key=key)
                for v in entry.value.split(","):
                    v = v.strip()
                    if v != "" and v not in result:
                        result.append(v)
            except ConfigurationEntry.DoesNotExist:
                pass

        return result

    def get_absolute_url(self):
        return reverse("computer", args=(self.site.uid, self.uid))

    def os2_product(self):
        """Return whether a PC is running e.g. os2borgerpc or os2borgerpc kiosk."""
        return self.get_config_value("os2_product")

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


class ScriptTag(models.Model):
    """A tag model for scripts."""

    name = models.CharField(verbose_name=_("name"), max_length=255)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Script(AuditModelMixin):
    """A script to be performed on a registered client computer."""

    name = models.CharField(verbose_name=_("name"), max_length=255)
    # To have a consistent, unique reference to a script locally and across servers
    uid = models.CharField(
        verbose_name=_("UID"), max_length=255, unique=True, blank=True, null=True
    )
    description = models.TextField(verbose_name=_("description"), max_length=4096)
    site = models.ForeignKey(
        Site, related_name="scripts", null=True, blank=True, on_delete=models.CASCADE
    )
    # The executable_code field should contain a single executable (e.g. a Bash
    # script OR a single extractable .zip or .tar.gz file with all necessary
    # data.
    executable_code = models.FileField(
        verbose_name=_("executable code"), upload_to="script_uploads"
    )
    is_security_script = models.BooleanField(
        verbose_name=_("security script"), default=False, null=False
    )

    is_hidden = models.BooleanField(
        verbose_name=_("hidden script"), default=False, null=False
    )

    maintained_by_magenta = models.BooleanField(
        verbose_name=_("maintained by Magenta"),
        default=False,
        null=False,
    )
    tags = models.ManyToManyField(ScriptTag, related_name="scripts", blank=True)

    @property
    def is_global(self):
        return self.site is None

    def __str__(self):
        return self.name

    def run_on(self, site, pc_list, *args, user):
        batch = Batch(site=site, script=self, name="")
        batch.save()

        parameter_values = "["

        # Add parameters
        for i, inp in enumerate(self.ordered_inputs):
            if i < len(args):
                value = args[i]
                if inp.value_type == Input.PASSWORD:
                    parameter_values += "*****, "
                else:
                    parameter_values += str(value) + ", "
                if inp.value_type == Input.FILE:
                    p = BatchParameter(input=inp, batch=batch, file_value=value)
                else:
                    p = BatchParameter(input=inp, batch=batch, string_value=value)
                p.save()

        if len(parameter_values) > 1:
            parameter_values = parameter_values[:-2]
        parameter_values += "]"

        log_output = f"New job with arguments {parameter_values}"

        for pc in pc_list:
            job = Job(batch=batch, pc=pc, user=user, log_output=log_output)
            job.save()

        return batch

    @property
    def ordered_inputs(self):
        return self.inputs.all().order_by("position")

    def get_absolute_url(self, **kwargs):
        if "slug" in kwargs:
            slug = kwargs["slug"]
        else:
            slug = self.site.uid
        if self.is_security_script:
            return reverse("security_script", args=(slug, self.pk))
        else:
            return reverse("script", args=(slug, self.pk))

    class Meta:
        ordering = ["name"]


class Batch(models.Model):
    """A batch of jobs to be performed on a number of computers."""

    class Meta:
        verbose_name_plural = "Batches"
        ordering = ["-id"]

    # TODO: The name should probably be generated automatically from ID and
    # script and date, etc.
    name = models.CharField(verbose_name=_("name"), max_length=255)
    script = models.ForeignKey(Script, on_delete=models.CASCADE)
    site = models.ForeignKey(Site, related_name="batches", on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.name} - {self.script} - {self.site}"


class AssociatedScript(models.Model):
    """A script associated with a group. Adding a script to a group causes it
    to be run on all computers in the group; adding a computer to a group with
    scripts will cause all of those scripts to be run on the new member."""

    group = models.ForeignKey(PCGroup, related_name="policy", on_delete=models.CASCADE)
    script = models.ForeignKey(
        Script, related_name="associations", on_delete=models.CASCADE
    )
    position = models.IntegerField(verbose_name=_("position"))

    def make_batch(self):
        return Batch(
            site=self.group.site,
            script=self.script,
            name=f"{self.group.name}",
        )

    def make_parameters(self, batch):
        params = []
        for i in self.script.ordered_inputs.all():
            try:
                asp = self.parameters.get(input=i)
                params.append(asp.make_batch_parameter(batch))
            except AssociatedScriptParameter.DoesNotExist:
                # XXX
                raise
        return params

    @property
    def ordered_parameters(self):
        return self.parameters.all().order_by("input__position")

    def run_on(self, user, pcs):
        """\
Runs this script on several PCs, returning a batch representing this task."""
        batch = self.make_batch()
        batch.save()
        params = self.make_parameters(batch)

        parameter_values = "["

        for p in params:
            p.save()
            if p.file_value:
                parameter_values += str(p.file_value) + ", "
            elif p.input.value_type == Input.PASSWORD:
                parameter_values += "*****, "
            else:
                parameter_values += str(p.string_value) + ", "

        if len(parameter_values) > 1:
            parameter_values = parameter_values[:-2]
        parameter_values += "]"

        log_output = f"New job with arguments {parameter_values}"

        for pc in pcs:
            job = Job(batch=batch, pc=pc, user=user, log_output=log_output)
            job.save()

        return batch

    def __str__(self):
        return "{0}, {1}: {2}".format(self.group, self.position, self.script)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["position", "group"], name="unique_group_position"
            ),
        ]


class Job(models.Model):
    """A Job or task to be performed on a single computer."""

    # Job status choices
    NEW = "NEW"
    SUBMITTED = "SUBMITTED"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"
    RESOLVED = "RESOLVED"

    STATUS_TRANSLATIONS = {
        NEW: _("jobstatus:New"),
        SUBMITTED: _("jobstatus:Submitted"),
        RUNNING: _("jobstatus:Running"),
        FAILED: _("jobstatus:Failed"),
        DONE: _("jobstatus:Done"),
        RESOLVED: _("jobstatus:Resolved"),
    }

    STATUS_CHOICES = (
        (NEW, STATUS_TRANSLATIONS[NEW]),
        (SUBMITTED, STATUS_TRANSLATIONS[SUBMITTED]),
        (RUNNING, STATUS_TRANSLATIONS[RUNNING]),
        (FAILED, STATUS_TRANSLATIONS[FAILED]),
        (DONE, STATUS_TRANSLATIONS[DONE]),
        (RESOLVED, STATUS_TRANSLATIONS[RESOLVED]),
    )

    # Is it ideal to hardcode CSS class names in here? Better in template tag?
    STATUS_TO_LABEL = {
        NEW: "bg-secondary",
        SUBMITTED: "bg-info",
        RUNNING: "bg-warning",
        DONE: "bg-success",
        FAILED: "bg-danger",
        RESOLVED: "bg-primary",
    }

    # Fields
    # Use built-in ID field for ID.
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=NEW)
    log_output = models.TextField(
        verbose_name=_("log output"), max_length=128000, blank=True
    )
    created = models.DateTimeField(
        verbose_name=_("created"), auto_now_add=True, null=True
    )
    started = models.DateTimeField(verbose_name=_("started"), null=True)
    finished = models.DateTimeField(verbose_name=_("finished"), null=True)
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    batch = models.ForeignKey(Batch, related_name="jobs", on_delete=models.CASCADE)
    pc = models.ForeignKey(PC, related_name="jobs", on_delete=models.CASCADE)

    def __str__(self):
        return "_".join(map(str, [self.batch, self.id]))

    @property
    def has_info(self):
        return self.status == Job.FAILED or len(self.log_output) > 1

    @property
    def status_label(self):
        if self.status is None:
            return ""
        else:
            return Job.STATUS_TO_LABEL[self.status]

    @property
    def status_translated(self):
        if self.status is None:
            return ""
        else:
            return Job.STATUS_TRANSLATIONS[self.status]

    @property
    def failed(self):
        return self.status == Job.FAILED

    @property
    def as_instruction(self):
        parameters = []

        for param in self.batch.parameters.order_by("input__position"):
            parameters.append(
                {"type": param.input.value_type, "value": param.transfer_value}
            )

        return {
            "id": self.pk,
            "name": self.batch.script.name,
            "status": self.status,
            "parameters": parameters,
            "executable_code": self.batch.script.executable_code.read().decode("utf8"),
        }

    def resolve(self):
        if self.failed:
            self.status = Job.RESOLVED
            self.save()
        else:
            raise Exception(
                _("Cannot change status from {0} to {1}").format(
                    self.status, Job.RESOLVED
                )
            )

    def restart(self, user=user):
        if not self.failed:
            raise Exception(_("Can only restart jobs with status %s") % (Job.FAILED))
        # Create a new batch
        script = self.batch.script
        new_batch = Batch(site=self.batch.site, script=script, name="")
        new_batch.save()
        for p in self.batch.parameters.all():
            new_p = BatchParameter(
                input=p.input,
                batch=new_batch,
                file_value=p.file_value,
                string_value=p.string_value,
            )
            new_p.save()

        new_job = Job(batch=new_batch, pc=self.pc, user=user)
        new_job.save()
        self.resolve()

        return new_job


class Input(models.Model):
    """Input for a script"""

    # Value types
    STRING = "STRING"
    INT = "INT"
    DATE = "DATE"
    FILE = "FILE"
    BOOLEAN = "BOOLEAN"
    TIME = "TIME"
    PASSWORD = "PASSWORD"

    VALUE_CHOICES = (
        (STRING, _("String")),
        (INT, _("Integer")),
        (DATE, _("Date")),
        (FILE, _("File")),
        (BOOLEAN, _("Boolean")),
        (TIME, _("Time")),
        (PASSWORD, _("Password")),
    )

    name = models.CharField(verbose_name=_("name"), max_length=255)
    value_type = models.CharField(
        verbose_name=_("value type"), choices=VALUE_CHOICES, max_length=10
    )
    default_value = models.CharField(
        verbose_name=_("default value"), max_length=255, blank=True, null=True
    )
    position = models.IntegerField(verbose_name=_("position"))
    mandatory = models.BooleanField(verbose_name=_("mandatory"), default=True)
    script = models.ForeignKey(Script, related_name="inputs", on_delete=models.CASCADE)

    def __str__(self):
        return self.script.name + "/" + self.name

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["position", "script"], name="unique_script_position"
            ),
        ]


def upload_file_name(instance, filename):
    size = 32
    random_dirname = "".join(
        random.choice(string.ascii_lowercase + string.digits) for x in range(size)
    )
    return "/".join(["parameter_uploads", random_dirname, filename])


class Parameter(models.Model):
    """A concrete value for the Input of a Script."""

    string_value = models.CharField(max_length=4096, blank=True)
    file_value = models.FileField(upload_to=upload_file_name, null=True, blank=True)
    # which input does this belong to?
    input = models.ForeignKey(Input, on_delete=models.CASCADE)

    @property
    def transfer_value(self):
        input_type = self.input.value_type
        if input_type == Input.FILE:
            return self.file_value.url if self.file_value else ""
        else:
            return self.string_value

    class Meta:
        abstract = True


class BatchParameter(Parameter):
    # Which batch is this parameter associated with?
    batch = models.ForeignKey(
        Batch, related_name="parameters", on_delete=models.CASCADE
    )

    def __str__(self):
        return "{0}: {1}".format(self.input, self.transfer_value)


class AssociatedScriptParameter(Parameter):
    associated_script = models.ForeignKey(
        AssociatedScript, related_name="parameters", on_delete=models.CASCADE
    )

    def make_batch_parameter(self, batch):
        if self.input.value_type == Input.FILE:
            return BatchParameter(
                batch=batch, input=self.input, file_value=self.file_value
            )
        else:
            return BatchParameter(
                batch=batch, input=self.input, string_value=self.string_value
            )

    def __str__(self):
        return "{0} - {1}: {2}".format(
            self.associated_script, self.input, self.transfer_value
        )


class EventRuleBase(models.Model):
    """Contains everything shared between SecurityProblem and EventRuleServer."""

    name = models.CharField(verbose_name=_("name"), max_length=255)
    description = models.TextField(verbose_name=_("description"), blank=True)
    level = models.CharField(
        verbose_name=_("level"),
        max_length=10,
        choices=EventLevels.LEVEL_CHOICES,
        default=EventLevels.HIGH,
    )
    site = models.ForeignKey(Site, related_name="%(class)s", on_delete=models.CASCADE)
    alert_groups = models.ManyToManyField(
        PCGroup,
        related_name="%(class)s",
        verbose_name=_("alert groups"),
        blank=True,
    )
    alert_users = models.ManyToManyField(
        User,
        related_name="%(class)s",
        verbose_name=_("alert users"),
        blank=True,
    )

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]
        abstract = True


# Idea for future name change: EventRuleClient?
class SecurityProblem(EventRuleBase):
    """A security problem and the method (script) to handle it."""

    security_script = models.ForeignKey(
        Script,
        verbose_name=_("security script"),
        related_name="security_problems",
        on_delete=models.CASCADE,
    )

    def get_absolute_url(self):
        return reverse("event_rule_security_problem", args=(self.site.uid, self.id))


class EventRuleServer(EventRuleBase):
    """A model representing a different type of SecurityProblem. A regular SecurityProblem is a script sent to the
    computer which does some work and then conditionally reports alerts to the adminsite.
    An EventRuleServer is instead the adminsite doing some work and conditionally creating an alert.
    Example task: Check whether a computer hasn't been offline more than X amount of time.
    """

    monitor_period_start = models.TimeField(verbose_name=_("monitor period start"))
    monitor_period_end = models.TimeField(verbose_name=_("monitor period end"))
    # If implementing more EventRuleServer's this field would likely be made optional:
    maximum_offline_period = models.PositiveSmallIntegerField(
        verbose_name=_("maximum offline period allowed, in minutes"),
        default=15,
        validators=[MinValueValidator(15)],
        help_text=_("How long a PC may be offline before an event is created"),
    )

    def get_absolute_url(self):
        return reverse("event_rule_server", args=(self.site.uid, self.id))


class SecurityEvent(models.Model):

    """A security event is an instance of a security problem."""

    # Event status choices

    objects = SecurityEventQuerySet.as_manager()

    NEW = "NEW"
    ASSIGNED = "ASSIGNED"
    RESOLVED = "RESOLVED"

    STATUS_TRANSLATIONS = {
        NEW: _("eventstatus:New"),
        ASSIGNED: _("eventstatus:Assigned"),
        RESOLVED: _("eventstatus:Resolved"),
    }

    STATUS_CHOICES = (
        (NEW, STATUS_TRANSLATIONS[NEW]),
        (ASSIGNED, STATUS_TRANSLATIONS[ASSIGNED]),
        (RESOLVED, STATUS_TRANSLATIONS[RESOLVED]),
    )

    STATUS_TO_LABEL = {
        NEW: "bg-primary",
        ASSIGNED: "bg-secondary",
        RESOLVED: "bg-success",
    }
    problem = models.ForeignKey(
        SecurityProblem, null=True, blank=True, on_delete=models.CASCADE
    )
    event_rule_server = models.ForeignKey(
        EventRuleServer, null=True, blank=True, on_delete=models.CASCADE
    )
    # The time the problem was reported in the log file
    occurred_time = models.DateTimeField(verbose_name=_("occurred"))
    # The time the problem was submitted to the system
    reported_time = models.DateTimeField(verbose_name=_("reported"))
    pc = models.ForeignKey(PC, on_delete=models.CASCADE, related_name="security_events")
    summary = models.CharField(max_length=4096, blank=False)
    complete_log = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=NEW)
    assigned_user = models.ForeignKey(
        User,
        verbose_name=_("assigned user"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    note = models.TextField(blank=True)

    @property
    def namestr(self):
        return str(self)

    def __str__(self):
        if self.problem:
            return "{0}: {1}".format(self.problem.name, self.id)
        else:
            return "{0}: {1}".format(self.event_rule_server.name, self.id)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=Q(problem__isnull=False, event_rule_server=None)
                | Q(problem=None, event_rule_server__isnull=False),
                name="problem_or_rule_set",
            ),
        ]


class ImageVersion(models.Model):
    BORGERPC = "BORGERPC"
    BORGERPC_KIOSK = "BORGERPC_KIOSK"
    MEDBORGARPC = "MEDBORGARPC"

    platform_choices = (
        (BORGERPC, "OS2borgerPC"),
        (BORGERPC_KIOSK, "OS2borgerPC Kiosk"),
        (MEDBORGARPC, "Sambruk MedborgarPC"),
    )

    platform = models.CharField(max_length=128, choices=platform_choices)
    image_version = models.CharField(unique=True, max_length=7)
    release_date = models.DateField()
    os = models.CharField(verbose_name="OS", max_length=30)
    release_notes = models.TextField(max_length=1500)
    image_upload = models.FileField(upload_to="images", default="#")

    def __str__(self):
        return "{0} {1}".format(
            self.get_platform_display(),
            self.image_version,
        )

    class Meta:
        ordering = ["platform", "-image_version"]


# Last_successful_login is only updated whenever the citizen user:
# 1. Successfully authenticates with their backend (exists in their db, not locked out)
# 2. Successfully logs into a borgerPC because they either still have time left or it's
# after the quarantine period
class Citizen(models.Model):
    citizen_id = models.CharField(unique=True, max_length=128)
    last_successful_login = models.DateTimeField()
    site = models.ForeignKey(Site, on_delete=models.CASCADE)
    logged_in = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.site} - {self.citizen_id}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["citizen_id", "site"], name="unique_citizen_per_site"
            ),
        ]
