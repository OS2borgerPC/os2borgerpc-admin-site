from django import forms
from django.forms import ValidationError
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _

from system.models import (
    ChangelogComment,
    ConfigurationEntry,
    Input,
    PC,
    PCGroup,
    WakeWeekPlan,
    Script,
    SecurityEvent,
    SecurityProblem,
    Site,
)
from account.models import SiteMembership


# Adds the passed-in CSS classes to CharField (type=text + textarea)
# and the multitude of Fields that default to a <select> widget)
def add_classes_to_form(someform, classes_to_add):
    for field_name, field in someform.fields.items():
        matches_select_widget = [
            forms.ChoiceField,
            forms.TypedChoiceField,
            forms.MultipleChoiceField,
            forms.TypedMultipleChoiceField,
            forms.ModelChoiceField,
            forms.ModelMultipleChoiceField,
        ]
        if type(field) in matches_select_widget + [forms.CharField]:
            # Append if classes have already been added
            if "class" not in field.widget.attrs:
                field.widget.attrs["class"] = ""
            field.widget.attrs["class"] += " " + classes_to_add


class SiteForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(SiteForm, self).__init__(*args, **kwargs)
        instance = getattr(self, "instance", None)
        if instance and instance.pk:
            self.fields["uid"].widget.attrs["readonly"] = True

    class Meta:
        model = Site
        exclude = ["configuration", "paid_for_access_until"]
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

        forms.ModelForm.__init__(self, *args, **kwargs)

    def clean(self):
        cleaned_data = self.cleaned_data

        cleaned_data_id = cleaned_data.get("id")
        id_exists = self.Meta.model.objects.filter(id=cleaned_data_id).exists()

        # self.instance.pk will be set if it's an update form
        if not self.instance.pk and id_exists:
            raise ValidationError(_("A group with this ID already exists."))
        return cleaned_data

    def save(self, commit=True):
        instance = forms.ModelForm.save(self, False)

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
        fields = "__all__"


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
            user_profile = kwargs["instance"].bibos_profile
            site = kwargs.pop("site")
            site_membership = user_profile.sitemembership_set.get(site=site)
            initial["usertype"] = site_membership.site_user_type
        else:
            initial["usertype"] = SiteMembership.SITE_USER
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

        username = cleaned_data.get("username")
        user_exists = self.Meta.model.objects.filter(username=username).exists()

        if not self.instance.pk and user_exists:
            raise ValidationError(_("A user with this username already exists."))
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
            }
            if inp.value_type == Input.FILE:
                self.fields[name] = forms.FileField(**field_data)
            elif inp.value_type == Input.DATE:
                field_data["widget"] = forms.DateInput(attrs={"type": "date"})
                self.fields[name] = forms.DateField(**field_data)
            elif inp.value_type == Input.BOOLEAN:
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
            else:
                self.fields[name] = forms.CharField(**field_data)


class PCForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(PCForm, self).__init__(*args, **kwargs)
        instance = getattr(self, "instance", None)
        if instance and instance.pk:
            self.fields["uid"].disabled = True

    class Meta:
        model = PC
        exclude = (
            "configuration",
            "site",
            "is_update_required",
            "created",
            "last_seen",
        )


class SecurityProblemForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(SecurityProblemForm, self).__init__(*args, **kwargs)

    class Meta:
        model = SecurityProblem
        fields = "__all__"


class ChangelogCommentForm(forms.ModelForm):
    class Meta:
        model = ChangelogComment
        fields = ["content"]


class SecurityEventForm(forms.ModelForm):
    class Meta:
        model = SecurityEvent
        fields = ("status", "assigned_user", "note")


class WakePlanForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        # Setup for the group picklist, so we have access to the groups for the form
        if "instance" in kwargs and kwargs["instance"] is not None:
            initial = kwargs.setdefault("initial", {})
            initial["groups"] = [group.pk for group in kwargs["instance"].groups.all()]

        forms.ModelForm.__init__(self, *args, **kwargs)

    groups = forms.ModelMultipleChoiceField(
        queryset=PCGroup.objects.all(), required=False
    )

    class Meta:
        model = WakeWeekPlan
        exclude = ("site", )
