"""Regression tests for the portal authorization / security fixes.

Covers the findings fixed on the security branch: privilege escalation (A1),
cross-site script run (A2), global-script write protection (CR3), the removed
ConfigurationEntry views (A3), the login requirement on the security-event
search (A4), the config wipe/edit protection (read_only), cross-site policy
scripts, and the markdown XSS sink.

The logic-level guards are tested by instantiating the view and calling the
guard directly - this exercises exactly the security check without depending on
the full form/template machinery.
"""

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.http import Http404, QueryDict
from django.test import TestCase, SimpleTestCase, RequestFactory
from django.urls import reverse, NoReverseMatch

from account.models import UserProfile, SiteMembership
from system.models import (
    APIKey,
    Configuration,
    ConfigurationEntry,
    Country,
    Customer,
    PC,
    PCGroup,
    Script,
    Site,
    WakeWeekPlan,
)
from system.views import (
    EventRuleServerCreate,
    PCGroupUpdate,
    ScriptRun,
    ScriptUpdate,
    UserUpdate,
    WakePlanDuplicate,
    WakePlanUpdate,
)
from system.templatetags.markdown_extras import markdown_format


def make_site(uid):
    country = Country.objects.create(name="country-" + uid)
    customer = Customer.objects.create(name="cust-" + uid, country=country, is_test=False)
    config = Configuration.objects.create(name="sitecfg-" + uid)
    return Site.objects.create(
        name="site-" + uid, uid=uid, configuration=config, customer=customer
    )


def make_user(username, site, usertype, is_superuser=False):
    user = User.objects.create_user(username=username, password="pw")
    if is_superuser:
        user.is_superuser = True
        user.save()
    profile = UserProfile.objects.create(user=user)
    SiteMembership.objects.create(
        site=site, user_profile=profile, site_user_type=usertype
    )
    return user


def make_pc(uid, site, is_activated=True):
    config = Configuration.objects.create(name="pccfg-" + uid)
    return PC.objects.create(
        name="pc-" + uid,
        uid=uid,
        mac=uid,
        configuration=config,
        site=site,
        is_activated=is_activated,
    )


def make_group(name, site):
    config = Configuration.objects.create(name="grpcfg-" + name)
    return PCGroup.objects.create(
        name=name, description="", site=site, configuration=config
    )


class _FakeBoundField:
    """Minimal stand-in for a bound form field: only .value() is used by
    verify_and_add_groups_and_exceptions."""

    def __init__(self, value):
        self._value = value

    def value(self):
        return self._value


class _FakeForm:
    def __init__(self, groups, events):
        self._fields = {
            "groups": _FakeBoundField(groups),
            "wake_change_events": _FakeBoundField(events),
        }

    def __getitem__(self, key):
        return self._fields[key]


def make_script(name, site):
    return Script.objects.create(
        name=name, description="d", site=site, is_security_script=False
    )


class ConfigProtectionTests(TestCase):
    def test_wipe_does_not_delete_read_only_entry(self):
        cfg = Configuration.objects.create(name="cfg")
        ConfigurationEntry.objects.create(
            owner_configuration=cfg, key="admin_url", value="https://p", read_only=True
        )
        ConfigurationEntry.objects.create(
            owner_configuration=cfg, key="normal", value="x", read_only=False
        )
        # A POST that omits all config fields (the "bricking" attempt).
        cfg.update_from_request(QueryDict(""), "pc_config")
        keys = set(cfg.entries.values_list("key", flat=True))
        self.assertIn("admin_url", keys)
        self.assertNotIn("normal", keys)

    def test_update_cannot_touch_another_configs_entry(self):
        cfg_a = Configuration.objects.create(name="a")
        cfg_b = Configuration.objects.create(name="b")
        entry_b = ConfigurationEntry.objects.create(
            owner_configuration=cfg_b, key="k", value="original", read_only=False
        )
        # Craft a POST for cfg_a that references cfg_b's entry pk.
        post = QueryDict(mutable=True)
        post.setlist("pc_config", [str(entry_b.pk)])
        post["pc_config_%s_key" % entry_b.pk] = "k"
        post["pc_config_%s_value" % entry_b.pk] = "hijacked"
        cfg_a.update_from_request(post, "pc_config")
        entry_b.refresh_from_db()
        self.assertEqual(entry_b.value, "original")


class MarkdownXSSTests(SimpleTestCase):
    def test_raw_html_is_escaped(self):
        out = str(markdown_format("<script>alert(1)</script>"))
        self.assertNotIn("<script>", out)
        self.assertIn("&lt;script&gt;", out)

    def test_markdown_formatting_preserved(self):
        out = str(markdown_format("**bold**"))
        self.assertIn("<strong>bold</strong>", out)


class UserEscalationTests(TestCase):
    def _view_for(self, user, selected_user):
        view = UserUpdate()
        req = RequestFactory().post("/")
        req.user = user
        view.request = req
        view.selected_user = selected_user
        return view

    def test_site_user_cannot_grant_higher_type(self):
        site = make_site("s1")
        site_user = make_user("u1", site, SiteMembership.SITE_USER)
        view = self._view_for(site_user, site_user)
        with self.assertRaises(PermissionDenied):
            view.deny_if_usertype_elevated(site, SiteMembership.CUSTOMER_ADMIN)

    def test_site_user_may_keep_own_type(self):
        site = make_site("s2")
        site_user = make_user("u2", site, SiteMembership.SITE_USER)
        view = self._view_for(site_user, site_user)
        # Should not raise.
        view.deny_if_usertype_elevated(site, SiteMembership.SITE_USER)

    def test_superuser_may_grant_anything(self):
        site = make_site("s3")
        su = make_user("root", site, SiteMembership.SITE_USER, is_superuser=True)
        view = self._view_for(su, su)
        view.deny_if_usertype_elevated(site, SiteMembership.CUSTOMER_ADMIN)


class ScriptRunScopingTests(TestCase):
    def test_pcs_from_another_site_are_filtered_out(self):
        site_a = make_site("a")
        site_b = make_site("b")
        pc_a = make_pc("pca", site_a)
        pc_b = make_pc("pcb", site_b)

        view = ScriptRun()
        view.object = site_a  # SiteView.object is the site being acted on

        view.request = RequestFactory().post("/", {"pcs": [str(pc_b.pk)]})
        selected, num = view.fetch_pcs_from_request()
        self.assertEqual(selected, [])  # pc_b belongs to another site

        view.request = RequestFactory().post("/", {"pcs": [str(pc_a.pk)]})
        selected, num = view.fetch_pcs_from_request()
        self.assertEqual(selected, [pc_a.pk])


class GlobalScriptWriteTests(TestCase):
    def test_site_user_cannot_edit_global_script(self):
        site = make_site("g1")
        site_user = make_user("gu", site, SiteMembership.SITE_ADMIN)
        global_script = make_script("global", None)  # site=None => global

        view = ScriptUpdate()
        view.script = global_script
        req = RequestFactory().post("/")
        req.user = site_user
        view.request = req
        # The guard raises before the form is used, so form=None is fine.
        with self.assertRaises(PermissionDenied):
            view.form_valid(form=None)


class PolicyScriptScopingTests(TestCase):
    def _post_for_script(self, script):
        post = QueryDict(mutable=True)
        post.setlist("group_policies", ["new_0"])
        post["group_policies_new_0"] = str(script.pk)
        req = RequestFactory().post("/")
        req.POST = post
        return req

    def test_foreign_site_script_not_associated(self):
        site_a = make_site("pa")
        site_b = make_site("pb")
        group_cfg = Configuration.objects.create(name="gcfg")
        group = PCGroup.objects.create(
            name="grp", description="", site=site_a, configuration=group_cfg
        )
        foreign_script = make_script("foreign", site_b)
        group.update_policy_from_request(
            self._post_for_script(foreign_script), "group_policies"
        )
        self.assertEqual(group.policy.count(), 0)

    def test_global_script_is_associated(self):
        site_a = make_site("pc1")
        group_cfg = Configuration.objects.create(name="gcfg2")
        group = PCGroup.objects.create(
            name="grp2", description="", site=site_a, configuration=group_cfg
        )
        global_script = make_script("glob", None)
        group.update_policy_from_request(
            self._post_for_script(global_script), "group_policies"
        )
        self.assertEqual(group.policy.count(), 1)


class RemovedAndProtectedUrlTests(TestCase):
    def test_configuration_edit_urls_removed(self):
        with self.assertRaises(NoReverseMatch):
            reverse("edit_configuration", args=["default", 1])
        with self.assertRaises(NoReverseMatch):
            reverse("new_configuration", args=["default"])

    def test_security_event_search_requires_login(self):
        site = make_site("sec")
        url = reverse("security_event_search", args=[site.uid])
        response = self.client.get(url)
        # Anonymous access must not succeed (redirect to login or forbidden).
        self.assertIn(response.status_code, (302, 403))


class PCGroupUpdateScopingTests(TestCase):
    def test_pcs_and_supervisors_scoped_to_site(self):
        site_a = make_site("gsa")
        site_b = make_site("gsb")
        pc_a = make_pc("gspa", site_a)
        pc_b = make_pc("gspb", site_b)
        user_a = make_user("gsua", site_a, SiteMembership.SITE_ADMIN)
        user_b = make_user("gsub", site_b, SiteMembership.SITE_ADMIN)
        group = make_group("gsgrp", site_a)

        view = PCGroupUpdate()
        view.kwargs = {"slug": site_a.uid, "group_id": group.id}
        view.object = group
        view.request = RequestFactory().get("/")
        form = view.get_form()

        self.assertIn(pc_a, form.fields["pcs"].queryset)
        self.assertNotIn(pc_b, form.fields["pcs"].queryset)
        self.assertIn(user_a, form.fields["supervisors"].queryset)
        self.assertNotIn(user_b, form.fields["supervisors"].queryset)


class EventRuleScopingTests(TestCase):
    def test_alert_groups_scoped_to_site(self):
        site_a = make_site("era")
        site_b = make_site("erb")
        group_a = make_group("erga", site_a)
        group_b = make_group("ergb", site_b)

        view = EventRuleServerCreate()
        view.kwargs = {"slug": site_a.uid}
        view.object = None
        view.request = RequestFactory().get("/")
        form = view.get_form()

        self.assertIn(group_a, form.fields["alert_groups"].queryset)
        self.assertNotIn(group_b, form.fields["alert_groups"].queryset)


class WakePlanScopingTests(TestCase):
    def test_cannot_duplicate_another_sites_plan(self):
        site_a = make_site("wda")
        site_b = make_site("wdb")
        plan_b = WakeWeekPlan.objects.create(name="planb", site=site_b)

        view = WakePlanDuplicate()
        view.request = RequestFactory().get("/")
        with self.assertRaises(Http404):
            view.get_redirect_url(slug=site_a.uid, wake_week_plan_id=plan_b.id)

    def test_verify_and_add_filters_foreign_group(self):
        site_a = make_site("wva")
        site_b = make_site("wvb")
        plan_a = WakeWeekPlan.objects.create(name="plana", site=site_a)
        foreign_group = make_group("wvfg", site_b)

        view = WakePlanUpdate()
        view.object = plan_a
        view.kwargs = {"slug": site_a.uid}
        view.request = RequestFactory().post("/")
        view.verify_and_add_groups_and_exceptions(
            _FakeForm(groups=[foreign_group.pk], events=[])
        )

        foreign_group.refresh_from_db()
        self.assertIsNone(foreign_group.wake_week_plan)
        self.assertEqual(plan_a.wake_change_events.count(), 0)


class APIKeyDeleteScopingTests(TestCase):
    def test_cannot_delete_another_sites_api_key(self):
        site_a = make_site("aka")
        site_b = make_site("akb")
        admin_a = make_user("aka_admin", site_a, SiteMembership.CUSTOMER_ADMIN)
        key_b = APIKey.objects.create(key="secret-b", site=site_b)

        self.client.force_login(admin_a)
        self.client.delete(reverse("api_key_delete", args=[site_a.uid, key_b.id]))

        self.assertTrue(APIKey.objects.filter(id=key_b.id).exists())

    def test_can_delete_own_sites_api_key(self):
        site_a = make_site("akc")
        admin_a = make_user("akc_admin", site_a, SiteMembership.CUSTOMER_ADMIN)
        key_a = APIKey.objects.create(key="secret-a", site=site_a)

        self.client.force_login(admin_a)
        self.client.delete(reverse("api_key_delete", args=[site_a.uid, key_a.id]))

        self.assertFalse(APIKey.objects.filter(id=key_a.id).exists())
