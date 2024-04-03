from django import forms
from django.forms import ValidationError
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

from system.models import (
    ConfigurationEntry,
    Input,
    PC,
    PCGroup,
    WakeChangeEvent,
    WakeWeekPlan,
    Script,
    SecurityEvent,
    EventRuleServer,
    Site,
)
from account.models import SiteMembership, UserProfile

time_format = forms.TimeInput(
    attrs={"type": "time", "max": "23:59", "class": "form-control"}, format="%H:%M"
)
date_format = forms.DateInput(
    attrs={"type": "date", "class": "form-control"}, format="%Y-%m-%d"
)


class SiteForm(forms.ModelForm):
    citizen_login_api_password = forms.CharField(
        label=_("Password for login API (e.g. Cicero)"),
        widget=forms.PasswordInput(attrs={"class": "passwordinput"}),
        required=False,
        help_text=_(
            "Necessary for customers who wish to authenticate BorgerPC logins through an API (e.g. Cicero)"
        ),
    )
    booking_api_key = forms.CharField(
        label=_("API key for Easy!Appointments"),
        widget=forms.PasswordInput(attrs={"class": "passwordinput"}),
        required=False,
        help_text=_(
            "Necessary for customers who wish to require booking through Easy!Appointments"
        ),
    )
    citizen_login_api_key = forms.CharField(
        label=_("API key for login API (e.g. Quria)"),
        widget=forms.PasswordInput(attrs={"class": "passwordinput"}),
        required=False,
        help_text=_(
            "Necessary for customers who wish to authenticate BorgerPC logins through an API "
            "that requires an API key (e.g. Quria)"
        ),
    )

    def __init__(self, *args, **kwargs):
        super(SiteForm, self).__init__(*args, **kwargs)
        instance = getattr(self, "instance", None)
        if instance and instance.pk:
            self.fields["uid"].widget.attrs["readonly"] = True

    class Meta:
        model = Site
        exclude = ["configuration", "paid_for_access_until", "country", "is_testsite"]
        widgets = {
            "paid_for_access_until": forms.widgets.DateInput(attrs={"type": "date"}),
        }


class PCGroupForm(forms.ModelForm):
    # Need to set up this side of the many-to-many relation between groups
    # and PCs manually.
    pcs = forms.ModelMultipleChoiceField(queryset=PC.objects.all(), required=False)

    def __init__(self, *args, **kwargs):
        if "instance" in kwargs and kwargs["instance"] is not None:
            initial = kwargs.setdefault("initial", {})
            initial["pcs"] = [pc.pk for pc in kwargs["instance"].pcs.all()]

        super().__init__(*args, **kwargs)

    def clean(self):
        return self.cleaned_data

    def save(self, commit=True):
        instance = super().save(False)

        old_save_m2m = self.save_m2m

        def save_m2m():
            old_save_m2m()
            instance.pcs.clear()
            for pc in self.cleaned_data["pcs"]:
                instance.pcs.add(pc)

        self.save_m2m = save_m2m

        # Do we need to save all changes now?
        if commit:
            instance.save()
            self.save_m2m()

        return instance

    class Meta:
        model = PCGroup
        exclude = ["site", "configuration", "wake_week_plan"]


class ScriptForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(ScriptForm, self).__init__(*args, **kwargs)
        instance = getattr(self, "instance", None)
        if instance and instance.pk:
            self.fields["site"].disabled = True
        else:
            self.fields["maintained_by_magenta"].widget = forms.HiddenInput()

        self.fields["tags"].disabled = True
        self.fields["maintained_by_magenta"].widget.attrs["disabled"] = True

    class Meta:
        model = Script
        exclude = ["feature_permission", "product"]


class ConfigurationEntryForm(forms.ModelForm):
    class Meta:
        model = ConfigurationEntry
        exclude = ["owner_configuration"]


class UserForm(forms.ModelForm):
    usertype = forms.ChoiceField(
        required=True,
        choices=SiteMembership.type_choices,
        label=_("Usertype"),
    )

    language = forms.ChoiceField(
        required=True,
        choices=UserProfile.language_choices,
        label=_("Language"),
    )

    new_password = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(attrs={"class": "passwordinput"}),
        required=False,
    )

    password_confirm = forms.CharField(
        label=_("Password (again)"),
        widget=forms.PasswordInput(attrs={"class": "passwordinput"}),
        required=False,
    )

    class Meta:
        model = User
        exclude = (
            "groups",
            "user_permissions",
            "first_name",
            "last_name",
            "is_staff",
            "is_active",
            "is_superuser",
            "date_joined",
            "last_login",
            "password",
        )

    def __init__(self, *args, **kwargs):
        initial = kwargs.setdefault("initial", {})
        if "instance" in kwargs and kwargs["instance"] is not None:
            user_profile = kwargs["instance"].user_profile
            site = kwargs.pop("site")
            site_membership = user_profile.sitemembership_set.get(site=site)
            initial["usertype"] = site_membership.site_user_type
            initial["language"] = user_profile.language
        else:
            initial["usertype"] = SiteMembership.SITE_USER
            language = kwargs.pop("language", None)
            if language is not None:
                initial["language"] = language
        self.initial_type = initial["usertype"]
        super(UserForm, self).__init__(*args, **kwargs)

    def set_usertype_single_choice(self, choice_type):
        self.fields["usertype"].choices = [
            (c, l) for c, l in SiteMembership.type_choices if c == choice_type
        ]
        self.fields["usertype"].widget.attrs["readonly"] = True

    # Sets the choices in the usertype widget depending on the usertype
    # of the user currently filling out the form
    def setup_usertype_choices(self, loginuser_type, is_superuser):
        if is_superuser or loginuser_type == SiteMembership.SITE_ADMIN:
            # superusers and site admins can both
            # choose site admin or site user.
            self.fields["usertype"].choices = SiteMembership.type_choices
        else:
            # Set to read-only single choice
            self.set_usertype_single_choice(self.initial_type)

    def clean(self):
        cleaned_data = self.cleaned_data
        pw1 = cleaned_data.get("new_password")
        pw2 = cleaned_data.get("password_confirm")
        if pw1 != pw2:
            raise forms.ValidationError(_("Passwords must be identical."))

        form_username = cleaned_data.get("username")
        user_exists = self.Meta.model.objects.filter(username=form_username).exists()

        if not self.instance.username == form_username and user_exists:
            raise ValidationError(
                _('A user named "%s" already exists.') % form_username
            )
        return cleaned_data

    def save(self, commit=True):
        user = super(UserForm, self).save(commit=False)
        if self.cleaned_data["new_password"]:
            user.set_password(self.cleaned_data["new_password"])
        if commit:
            user.save()
        return user


class ParameterForm(forms.Form):
    def __init__(self, *args, **kwargs):
        script = kwargs.pop("script")
        super(ParameterForm, self).__init__(*args, **kwargs)

        for i, inp in enumerate(script.ordered_inputs):
            name = "parameter_%s" % i
            field_data = {
                "label": inp.name,
                "required": True if inp.mandatory else False,
                "initial": inp.default_value,
            }
            if inp.value_type == Input.FILE:
                self.fields[name] = forms.FileField(**field_data)
            elif inp.value_type == Input.DATE:
                field_data["widget"] = forms.DateInput(attrs={"type": "date"})
                self.fields[name] = forms.DateField(**field_data)
            elif inp.value_type == Input.BOOLEAN:
                field_data["initial"] = "True"
                self.fields[name] = forms.BooleanField(
                    **field_data, widget=forms.CheckboxInput()
                )
            elif inp.value_type == Input.INT:
                self.fields[name] = forms.IntegerField(**field_data)
            elif inp.value_type == Input.TIME:
                field_data["widget"] = forms.TimeInput(attrs={"type": "time"})
                self.fields[name] = forms.CharField(**field_data)
            elif inp.value_type == Input.PASSWORD:
                self.fields[name] = forms.CharField(
                    **field_data,
                    widget=forms.PasswordInput(
                        attrs={
                            "readonly": "",
                            "onfocus": "this.removeAttribute('readonly')",
                            "class": "password-input",
                        }
                    )
                )
            elif inp.value_type == Input.CHOICE:
                default_value_no_spaces = inp.default_value.replace(" ", "")
                CHOICES = [
                    (option, option) for option in default_value_no_spaces.split(",")
                ]
                self.fields[name] = forms.ChoiceField(**field_data, choices=CHOICES)
            else:
                self.fields[name] = forms.CharField(**field_data)


class PCForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(PCForm, self).__init__(*args, **kwargs)
        instance = getattr(self, "instance", None)
        if instance and instance.pk:
            self.fields["uid"].disabled = True
            self.fields["mac"].disabled = True

    class Meta:
        model = PC
        exclude = (
            "configuration",
            "site",
            "created",
            "last_seen",
        )


class SecurityEventForm(forms.ModelForm):
    class Meta:
        model = SecurityEvent
        fields = ("status", "assigned_user", "note")


class EventRuleServerForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(EventRuleServerForm, self).__init__(*args, **kwargs)

    class Meta:
        model = EventRuleServer
        fields = "__all__"
        widgets = {
            "monitor_period_start": time_format,
            "monitor_period_end": time_format,
        }


# Used on the Create and Update views
class WakePlanForm(forms.ModelForm):
    # Picklist related
    groups = forms.ModelMultipleChoiceField(
        queryset=PCGroup.objects.all(), required=False
    )
    wake_change_events = forms.ModelMultipleChoiceField(
        queryset=WakeChangeEvent.objects.all(), required=False
    )

    def __init__(self, *args, **kwargs):
        # Setup for the picklists, so we have access to the groups and wake_change_events for the form
        if "instance" in kwargs and kwargs["instance"] is not None:
            initial = kwargs.setdefault("initial", {})
            initial["groups"] = [group.pk for group in kwargs["instance"].groups.all()]
            initial["wake_change_events"] = [
                event.pk for event in kwargs["instance"].wake_change_events.all()
            ]

        super().__init__(*args, **kwargs)

    class Meta:
        model = WakeWeekPlan
        exclude = (
            "site",
            "wake_change_events",
        )

        switch_input = forms.CheckboxInput(
            attrs={"class": "form-check-input fs-5", "role": "switch"}
        )

        widgets = {
            "monday_on": time_format,
            "monday_off": time_format,
            "tuesday_on": time_format,
            "tuesday_off": time_format,
            "wednesday_on": time_format,
            "wednesday_off": time_format,
            "thursday_on": time_format,
            "thursday_off": time_format,
            "friday_on": time_format,
            "friday_off": time_format,
            "saturday_on": time_format,
            "saturday_off": time_format,
            "sunday_on": time_format,
            "sunday_off": time_format,
            "sleep_state": forms.Select(attrs={"class": "form-control"}),
            "enabled": switch_input,
        }


# This should be deleteable later on:
class WakeChangeEventForm(forms.ModelForm):
    class Meta:
        model = WakeChangeEvent
        exclude = ("site",)
        widgets = {
            "name": forms.TextInput(attrs={"id": "wake-change-event-name"}),
            "date_start": date_format,
            "time_start": time_format,
            "date_end": date_format,
            "time_end": time_format,
        }
