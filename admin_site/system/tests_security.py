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
    AssociatedScript,
    Batch,
    Configuration,
    ConfigurationEntry,
    Country,
    Customer,
    Input,
    Job,
    PC,
    PCGroup,
    Script,
    SecurityProblem,
    Site,
    WakeWeekPlan,
)
from system.views import (
    EventRuleServerCreate,
    JobRestarter,
    PCGroupUpdate,
    ScriptRun,
    ScriptUpdate,
    SecurityProblemCreate,
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


def make_script(name, site, is_security=False, is_hidden=False):
    return Script.objects.create(
        name=name,
        description="d",
        site=site,
        is_security_script=is_security,
        is_hidden=is_hidden,
    )


def make_job(site, pc):
    script = make_script("job-script-" + site.uid, site)
    batch = Batch.objects.create(name="b-" + site.uid, script=script, site=site)
    return Job.objects.create(batch=batch, pc=pc, status=Job.DONE)


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


class APIKeyViewTests(TestCase):
    def test_delete_on_apikeyupdate_cannot_delete_a_site(self):
        site_a = make_site("apa")
        site_b = make_site("apb")
        admin_a = make_user("apa_admin", site_a, SiteMembership.CUSTOMER_ADMIN)

        self.client.force_login(admin_a)
        # The <pk> is site_b's id; before the fix this DELETE deleted that Site.
        self.client.delete(
            reverse("api_key_update", args=[site_a.uid, site_b.id])
        )
        self.assertTrue(Site.objects.filter(id=site_b.id).exists())

    def test_description_update_scoped_to_site(self):
        site_a = make_site("apc")
        site_b = make_site("apd")
        admin_a = make_user("apc_admin", site_a, SiteMembership.CUSTOMER_ADMIN)
        key_b = APIKey.objects.create(key="kb", site=site_b, description="orig")

        self.client.force_login(admin_a)
        self.client.post(
            reverse("api_key_update", args=[site_a.uid, key_b.id]),
            {"description": "hijacked"},
        )
        key_b.refresh_from_db()
        self.assertEqual(key_b.description, "orig")

    def test_create_cannot_target_another_site(self):
        site_a = make_site("ape")
        site_b = make_site("apf")
        admin_a = make_user("ape_admin", site_a, SiteMembership.CUSTOMER_ADMIN)

        self.client.force_login(admin_a)
        self.client.post(
            reverse("api_key_new", args=[site_a.uid]),
            {"site": site_b.id, "key": "attacker-chosen", "description": "x"},
        )
        # No key on site_b, and the attacker-chosen key value was not honored.
        self.assertFalse(APIKey.objects.filter(site=site_b).exists())
        self.assertFalse(APIKey.objects.filter(key="attacker-chosen").exists())


class SecurityProblemSiteSpoofTests(TestCase):
    def test_site_is_forced_to_slug_site(self):
        site_a = make_site("spa")
        site_b = make_site("spb")
        admin_a = make_user("spa_admin", site_a, SiteMembership.SITE_ADMIN)
        script = make_script("secscript", None, is_security=True)  # global

        view = SecurityProblemCreate()
        view.kwargs = {"slug": site_a.uid}
        req = RequestFactory().post("/")
        req.user = admin_a
        view.request = req
        view.object = None

        form_class = view.get_form_class()
        form = form_class(
            data={
                "name": "rule",
                "level": "High",
                "site": site_b.id,  # spoofed target
                "security_script": script.id,
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        view.form_valid(form)

        created = SecurityProblem.objects.get(name="rule")
        self.assertEqual(created.site_id, site_a.id)  # forced back to own site


class UserDeleteAuthTests(TestCase):
    def test_delete_denied_for_site_user(self):
        site = make_site("uda")
        low = make_user("uda_low", site, SiteMembership.SITE_USER)
        victim = make_user("uda_victim", site, SiteMembership.SITE_USER)

        self.client.force_login(low)
        self.client.delete(reverse("user_delete", args=[site.uid, victim.username]))
        self.assertTrue(User.objects.filter(username=victim.username).exists())

    def test_delete_of_superuser_denied_for_site_admin(self):
        site = make_site("udb")
        admin = make_user("udb_admin", site, SiteMembership.SITE_ADMIN)
        su = make_user("udb_su", site, SiteMembership.SITE_USER, is_superuser=True)

        self.client.force_login(admin)
        self.client.delete(reverse("user_delete", args=[site.uid, su.username]))
        self.assertTrue(User.objects.filter(username=su.username).exists())


class UserUpdateSuperuserTargetTests(TestCase):
    def _get_object_as(self, requester, target, site):
        view = UserUpdate()
        view.kwargs = {"slug": site.uid, "username": target.username}
        req = RequestFactory().post("/")
        req.user = requester
        view.request = req
        return view.get_object()

    def test_site_admin_cannot_load_superuser_target(self):
        site = make_site("sua")
        admin = make_user("sua_admin", site, SiteMembership.SITE_ADMIN)
        su = make_user("sua_su", site, SiteMembership.SITE_USER, is_superuser=True)
        with self.assertRaises(PermissionDenied):
            self._get_object_as(admin, su, site)

    def test_site_admin_can_load_ordinary_target(self):
        site = make_site("sub")
        admin = make_user("sub_admin", site, SiteMembership.SITE_ADMIN)
        ordinary = make_user("sub_user", site, SiteMembership.SITE_USER)
        # Should not raise.
        self.assertEqual(self._get_object_as(admin, ordinary, site), ordinary)

    def test_user_can_load_self(self):
        site = make_site("suc")
        low = make_user("suc_low", site, SiteMembership.SITE_USER)
        self.assertEqual(self._get_object_as(low, low, site), low)


class SaveScriptInputsTests(TestCase):
    def test_foreign_input_pk_not_hijacked(self):
        site = make_site("ssi")
        su = make_user("ssi_su", site, SiteMembership.SITE_USER, is_superuser=True)
        my_script = make_script("mine", site)
        global_script = make_script("glob", None)
        victim_input = Input.objects.create(
            name="victim", script=global_script, position=0, value_type=Input.STRING
        )

        view = ScriptUpdate()
        view.script = my_script
        req = RequestFactory().post("/")
        req.user = su
        view.request = req
        # Submit the GLOBAL script's Input pk while editing my own script.
        view.script_inputs = [
            {
                "pk": str(victim_input.pk),
                "name": "stolen",
                "value_type": Input.STRING,
                "position": 0,
                "default_value": "",
                "mandatory": False,
            }
        ]
        view.save_script_inputs()

        victim_input.refresh_from_db()
        # The victim Input still belongs to the global script, untouched.
        self.assertEqual(victim_input.script_id, global_script.id)
        self.assertEqual(victim_input.name, "victim")


class PolicyAscPkTests(TestCase):
    def test_foreign_associated_script_pk_not_moved(self):
        site = make_site("pap")
        my_cfg = Configuration.objects.create(name="mg")
        other_cfg = Configuration.objects.create(name="og")
        my_group = PCGroup.objects.create(
            name="mine", description="", site=site, configuration=my_cfg
        )
        other_group = PCGroup.objects.create(
            name="other", description="", site=site, configuration=other_cfg
        )
        script = make_script("s", site)
        # An AssociatedScript owned by another group.
        foreign_asc = AssociatedScript.objects.create(
            group=other_group, script=script, position=0
        )

        # Craft a POST for my_group reusing the foreign asc pk.
        post = QueryDict(mutable=True)
        post.setlist("group_policies", [str(foreign_asc.pk)])
        post["group_policies_%s" % foreign_asc.pk] = str(script.pk)

        class _Req:
            POST = post
            FILES = {}

        my_group.update_policy_from_request(_Req(), "group_policies")

        foreign_asc.refresh_from_db()
        # Still owned by the other group - not moved into mine.
        self.assertEqual(foreign_asc.group_id, other_group.id)


class JobRestarterScopeTests(TestCase):
    def test_foreign_job_not_found(self):
        site_a = make_site("jra")
        site_b = make_site("jrb")
        pc_b = make_pc("jrbpc", site_b)
        job_b = make_job(site_b, pc_b)

        view = JobRestarter()
        view.kwargs = {"slug": site_a.uid, "pk": job_b.pk}
        view.request = RequestFactory().get("/")
        with self.assertRaises(Http404):
            view.get_object()


class ScriptRunFetchScopeTests(TestCase):
    def _fetch_script_pk(self, view, slug, script_pk):
        view.kwargs = {"slug": slug, "script_pk": script_pk}
        req = RequestFactory().post("/", {"action": "choose_pcs_and_groups"})
        view.request = req
        view.object = Site.objects.get(uid=slug)
        return view.get_context_data()

    def test_foreign_site_script_not_fetchable(self):
        site_a = make_site("sra")
        site_b = make_site("srb")
        foreign = make_script("secret", site_b, is_hidden=True)

        view = ScriptRun()
        with self.assertRaises(Http404):
            self._fetch_script_pk(view, site_a.uid, foreign.pk)

    def test_global_script_is_fetchable(self):
        site_a = make_site("src")
        glob = make_script("glob", None)

        view = ScriptRun()
        ctx = self._fetch_script_pk(view, site_a.uid, glob.pk)
        self.assertEqual(ctx["script"].id, glob.id)
