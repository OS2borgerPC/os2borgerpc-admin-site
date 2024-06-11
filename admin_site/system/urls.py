from django.urls import re_path
from django.views.generic import RedirectView

from django.views.i18n import JavaScriptCatalog

from system.views import (
    AdminIndex,
    APIKeyCreate,
    APIKeyDelete,
    APIKeyUpdate,
    ConfigurationEntryCreate,
    ConfigurationEntryUpdate,
    DocView,
    ImageVersionRedirect,
    ImageVersionView,
    JobInfo,
    JobRestarter,
    JobSearch,
    JobsView,
    PCDelete,
    PCGroupCreate,
    PCGroupDelete,
    PCGroupRedirect,
    PCGroupUpdate,
    PCUpdate,
    WakePlanCreate,
    WakePlanDuplicate,
    WakePlanDelete,
    WakePlanRedirect,
    WakePlanUpdate,
    WakeChangeEventCreate,
    WakeChangeEventDelete,
    WakeChangeEventRedirect,
    WakeChangeEventUpdate,
    PCsView,
    ScriptCreate,
    ScriptDelete,
    ScriptRedirect,
    ScriptRun,
    ScriptUpdate,
    GlobalScriptRedirect,
    SecurityEventSearch,
    SecurityEventsUpdate,
    SecurityEventsView,
    SecurityProblemCreate,
    SecurityProblemDelete,
    SecurityProblemUpdate,
    EventRuleRedirect,
    EventRuleServerCreate,
    EventRuleServerDelete,
    EventRuleServerUpdate,
    SiteDetailView,
    SiteList,
    SiteCreate,
    site_uid_available_check,
    SiteDelete,
    SiteSettings,
    TwoFactor,
    AdminTwoFactorSetup,
    AdminTwoFactorSetupComplete,
    AdminTwoFactorDisable,
    AdminTwoFactorBackupTokens,
    UserCreate,
    UserDelete,
    UserLink,
    UserRedirect,
    UserUpdate,
)


urlpatterns = [
    # TODO: Switch to using the django javascript translation system
    # For translations of strings in javascript files that are printed to the user
    re_path("jsi18n/", JavaScriptCatalog.as_view(), name="javascript-catalog"),
    # Security events UI
    re_path(
        r"^site/(?P<slug>[^/]+)/security_events/update/$",
        SecurityEventsUpdate.as_view(),
        name="security_events_update",
    ),
    re_path(
        r"^site/(?P<slug>[^/]+)/security_events/search/$",
        SecurityEventSearch.as_view(),
        name="security_event_search",
    ),
    re_path(
        r"^site/(?P<slug>[^/]+)/security_events/$",
        SecurityEventsView.as_view(),
        name="security_events",
    ),
    # Shared by Security Problems and Event Rule Servers
    re_path(
        r"^site/(?P<slug>[^/]+)/event_rules/$",
        EventRuleRedirect.as_view(),
        name="event_rules",
    ),
    # Security problems
    re_path(
        r"^site/(?P<slug>[^/]+)/security_problems/new/$",
        SecurityProblemCreate.as_view(),
        name="event_rule_security_problem_new",
    ),
    re_path(
        r"^site/(?P<slug>[^/]+)/security_problems/(?P<id>[^/]+)/delete/$",
        SecurityProblemDelete.as_view(),
        name="event_rule_security_problem_delete",
    ),
    re_path(
        r"^site/(?P<slug>[^/]+)/security_problems/(?P<id>[^/]+)/$",
        SecurityProblemUpdate.as_view(),
        name="event_rule_security_problem",
    ),
    # Event Rule Server
    re_path(
        r"^site/(?P<slug>[^/]+)/event_rules_server/new/$",
        EventRuleServerCreate.as_view(),
        name="event_rule_server_new",
    ),
    re_path(
        r"^site/(?P<slug>[^/]+)/event_rules_server/(?P<id>[^/]+)/delete/$",
        EventRuleServerDelete.as_view(),
        name="event_rule_server_delete",
    ),
    re_path(
        r"^site/(?P<slug>[^/]+)/event_rules_server/(?P<id>[^/]+)/$",
        EventRuleServerUpdate.as_view(),
        name="event_rule_server",
    ),
    # Security scripts
    re_path(
        r"^site/(?P<slug>[^/]+)/security_scripts/(?P<script_pk>\d+)/delete/",
        ScriptDelete.as_view(is_security=True),
        name="security_script_delete",
    ),
    re_path(
        r"^site/(?P<slug>[^/]+)/security_scripts/(?P<script_pk>\d+)/",
        ScriptUpdate.as_view(is_security=True),
        name="security_script",
    ),
    re_path(
        r"^site/(?P<slug>[^/]+)/security_scripts/new/",
        ScriptCreate.as_view(is_security=True),
        name="new_security_script",
    ),
    re_path(
        r"^site/(?P<slug>[^/]+)/security_scripts/",
        ScriptRedirect.as_view(),
        name="security_scripts",
    ),
    # Two-factor for OS2borgerPC machines
    re_path(
        r"^site/(?P<slug>[^/]+)/two-factor/$", TwoFactor.as_view(), name="two_factor"
    ),
    # Two-factor for admin-site
    re_path(
        r"^site/(?P<slug>[^/]+)/admin-two-factor/(?P<username>[_\w\@\.\+\-]+)/setup/$",
        AdminTwoFactorSetup.as_view(),
        name="admin_otp_setup",
    ),
    re_path(
        r"^site/(?P<slug>[^/]+)/admin-two-factor/(?P<username>[_\w\@\.\+\-]+)/setup-complete/$",
        AdminTwoFactorSetupComplete.as_view(),
        name="admin_otp_setup_complete",
    ),
    re_path(
        r"^site/(?P<slug>[^/]+)/admin-two-factor/(?P<username>[_\w\@\.\+\-]+)/disable/$",
        AdminTwoFactorDisable.as_view(),
        name="admin_otp_disable",
    ),
    re_path(
        r"^site/(?P<slug>[^/]+)/admin-two-factor/(?P<username>[_\w\@\.\+\-]+)/backup-tokens/$",
        AdminTwoFactorBackupTokens.as_view(),
        name="admin_otp_backup",
    ),
    # Sites
    re_path(r"^$", AdminIndex.as_view(), name="index"),
    re_path(r"^sites/$", SiteList.as_view(), name="sites"),
    re_path(
        r"^site/new/$",
        SiteCreate.as_view(),
        name="site_create",
    ),
    re_path(
        r"^site/(?P<slug>[^/]+)/delete/$",
        SiteDelete.as_view(),
        name="site_delete",
    ),
    re_path(r"^site/(?P<slug>[^/]+)/$", SiteDetailView.as_view(), name="site"),
    # Site Settings
    re_path(
        r"^site/(?P<slug>[^/]+)/settings/$", SiteSettings.as_view(), name="settings"
    ),
    re_path(
        r"^site/(?P<slug>[^/]+)/configuration/new/$",
        ConfigurationEntryCreate.as_view(),
        name="new_configuration",
    ),
    re_path(
        r"^site/(?P<slug>[^/]+)/configuration/edit/(?P<pk>\d+)/$",
        ConfigurationEntryUpdate.as_view(),
        name="edit_configuration",
    ),
    # Computers
    re_path(r"^site/(?P<slug>[^/]+)/computers/$", PCsView.as_view(), name="computers"),
    re_path(
        r"^site/(?P<slug>[^/]+)/computers/(?P<pc_uid>[^/]+)/$",
        PCUpdate.as_view(),
        name="computer",
    ),
    re_path(
        r"^site/(?P<slug>[^/]+)/computers/(?P<pc_uid>[^/]+)/delete/$",
        PCDelete.as_view(),
        name="computer_delete",
    ),
    # Groups
    re_path(
        r"^site/(?P<slug>[^/]+)/groups/$", PCGroupRedirect.as_view(), name="groups"
    ),
    re_path(
        r"^site/(?P<slug>[^/]+)/groups/new/$",
        PCGroupCreate.as_view(),
        name="new_group",
    ),
    re_path(
        r"^site/(?P<slug>[^/]+)/groups/(?P<group_id>[^/]+)/$",
        PCGroupUpdate.as_view(),
        name="group",
    ),
    re_path(
        r"^site/(?P<slug>[^/]+)/groups/(?P<group_id>[^/]+)/delete/$",
        PCGroupDelete.as_view(),
        name="group_delete",
    ),
    # Wake Plans
    re_path(
        r"^site/(?P<slug>[^/]+)/wake_plans/$",
        WakePlanRedirect.as_view(),
        name="wake_plans",
    ),
    # This URL needs to be above WakePlanUpdate, as otherwise that regex tries to parse the word "new" as an ID
    re_path(
        r"^site/(?P<slug>[^/]+)/wake_plan/new/$",
        WakePlanCreate.as_view(),
        name="wake_plan_new",
    ),
    re_path(
        r"^site/(?P<slug>[^/]+)/wake_plan/(?P<wake_week_plan_id>[^/]+)/$",
        WakePlanUpdate.as_view(),
        name="wake_plan",
    ),
    re_path(
        r"^site/(?P<slug>[^/]+)/wake_plan/(?P<wake_week_plan_id>[^/]+)/delete/$",
        WakePlanDelete.as_view(),
        name="wake_plan_delete",
    ),
    re_path(
        r"^site/(?P<slug>[^/]+)/wake_plan/(?P<wake_week_plan_id>[^/]+)/copy/$",
        WakePlanDuplicate.as_view(),
        name="wake_plan_duplicate",
    ),
    # Wake Change Events
    re_path(
        r"^site/(?P<slug>[^/]+)/wake_change_events/$",
        WakeChangeEventRedirect.as_view(),
        name="wake_change_events",
    ),
    # This URL needs to be above WakeChangeEventUpdate, as otherwise that regex tries to parse the word "new" as an ID
    re_path(
        r"^site/(?P<slug>[^/]+)/wake_change_event/new_altered_hours/$",
        WakeChangeEventCreate.as_view(),
        name="wake_change_event_new_altered_hours",
    ),
    re_path(
        r"^site/(?P<slug>[^/]+)/wake_change_event/new_closed/$",
        WakeChangeEventCreate.as_view(),
        name="wake_change_event_new_closed",
    ),
    re_path(
        r"^site/(?P<slug>[^/]+)/wake_change_event/(?P<wake_change_event_id>[^/]+)/$",
        WakeChangeEventUpdate.as_view(),
        name="wake_change_event",
    ),
    re_path(
        r"^site/(?P<slug>[^/]+)/wake_change_event/(?P<wake_change_event_id>[^/]+)/delete/$",
        WakeChangeEventDelete.as_view(),
        name="wake_change_event_delete",
    ),
    # Jobs
    re_path(
        r"^site/(?P<slug>[^/]+)/jobs/search/", JobSearch.as_view(), name="jobsearch"
    ),
    re_path(
        r"^site/(?P<slug>[^/]+)/jobs/(?P<pk>\d+)/restart/",
        JobRestarter.as_view(),
        name="restart_job",
    ),
    re_path(
        r"^site/(?P<slug>[^/]+)/jobs/(?P<pk>\d+)/info/",
        JobInfo.as_view(),
        name="job_info",
    ),
    re_path(r"^site/(?P<slug>[^/]+)/jobs/", JobsView.as_view(), name="jobs"),
    # Scripts
    re_path(
        r"^site/(?P<slug>[^/]+)/scripts/(?P<script_pk>\d+)/delete/",
        ScriptDelete.as_view(),
        name="script_delete",
    ),
    re_path(
        r"^site/(?P<slug>[^/]+)/scripts/(?P<script_pk>\d+)/run/",
        ScriptRun.as_view(),
        name="run_script",
    ),
    re_path(
        r"^site/(?P<slug>[^/]+)/scripts/(?P<script_pk>\d+)/",
        ScriptUpdate.as_view(),
        name="script",
    ),
    re_path(
        r"^site/(?P<slug>[^/]+)/scripts/new/", ScriptCreate.as_view(), name="new_script"
    ),
    re_path(
        r"^site/(?P<slug>[^/]+)/scripts/", ScriptRedirect.as_view(), name="scripts"
    ),
    re_path(
        r"^scripts/(?P<script_pk>\d+)/",
        GlobalScriptRedirect.as_view(),
        name="script_redirect_id",
    ),
    re_path(
        r"^scripts/uid/(?P<script_uid>[^/]+)/",
        GlobalScriptRedirect.as_view(),
        name="script_redirect_uid",
    ),
    # Users
    re_path(r"^site/(?P<slug>[^/]+)/users/$", UserRedirect.as_view(), name="users"),
    re_path(
        r"^site/(?P<slug>[^/]+)/users/new/$", UserCreate.as_view(), name="new_user"
    ),
    re_path(
        r"^site/(?P<slug>[^/]+)/users/link/$", UserLink.as_view(), name="link_users"
    ),
    re_path(
        r"^site/(?P<slug>[^/]+)/users/(?P<username>[_\w\@\.\+\-]+)/$",
        UserUpdate.as_view(),
        name="user",
    ),
    re_path(
        (r"^site/(?P<slug>[^/]+)/users/" + r"(?P<username>[_\w\@\.\+\-]+)/delete/$"),
        UserDelete.as_view(),
        name="user_delete",
    ),
    # Documentation
    re_path(
        r"^documentation/$",
        RedirectView.as_view(url="/documentation/om_os2borgerpc_admin/"),
    ),
    re_path(
        r"^documentation/os2borgerpc_installation_guide/",
        RedirectView.as_view(
            url="https://github.com/OS2borgerPC/os2borgerpc-image/raw/development/"
            + "docs/OS2BorgerPC Installationsguide.pdf"
        ),
    ),
    re_path(
        r"^documentation/os2borgerpc_kiosk_installation_guide",
        RedirectView.as_view(
            url="https://os2borgerpc-server-image.readthedocs.io/en/latest/install_setup.html"
        ),
    ),
    re_path(
        r"^documentation/wake_plan_user_guide/",
        RedirectView.as_view(
            url="https://github.com/OS2borgerPC/os2borgerpc-admin-site/raw/development/admin_site"
            + "/static/docs/Guide_til_brug_af_strømbesparingsfunktioner.pdf"
        ),
        name="wake_plan_user_guide",
    ),
    re_path(
        r"^documentation/tech/os2borgerpc-image",
        RedirectView.as_view(url="https://os2borgerpc-image.readthedocs.io"),
    ),
    re_path(
        r"^documentation/tech/os2borgerpc-admin",
        RedirectView.as_view(url="https://os2borgerpc-admin.readthedocs.io"),
    ),
    re_path(
        r"^documentation/tech/os2borgerpc-server-image",
        RedirectView.as_view(url="https://os2borgerpc-server-image.readthedocs.io"),
    ),
    re_path(
        r"^documentation/tech/os2borgerpc-client",
        RedirectView.as_view(url="https://os2borgerpc-client.readthedocs.io"),
    ),
    re_path(r"^documentation/(?P<name>[\d\w\/]+)/", DocView.as_view(), name="doc"),
    re_path(r"^documentation/", DocView.as_view(), name="doc_root"),
    # Image Versions
    re_path(
        r"^site/(?P<slug>[^/]+)/image-versions/$",
        ImageVersionRedirect.as_view(),
        name="images",
    ),
    re_path(
        r"^site/(?P<slug>[^/]+)/image-versions/(?P<product_id>[^/]+)$",
        ImageVersionView.as_view(),
        name="images-product",
    ),
    # This contains both a regular view and an HTMX view
    re_path(
        r"^site/(?P<slug>[^/]+)/api-keys/$",
        APIKeyUpdate.as_view(),
        name="api_keys",
    ),
]

# Define HTMX URL Patterns here, and add them to the urlpatterns list
# Basically these are views that only return partial HTML fragments rather than entire pages
htmx_urlpatterns = [
    re_path(
        r"^site/(?P<slug>[^/]+)/api-keys/new/$",
        APIKeyCreate.as_view(),
        name="api_key_new",
    ),
    re_path(
        r"^site/(?P<slug>[^/]+)/api-key/(?P<pk>\d+)/update/$",
        APIKeyUpdate.as_view(),
        name="api_key_update",
    ),
    re_path(
        r"^site/(?P<slug>[^/]+)/api-key/(?P<pk>\d+)/delete/$",
        APIKeyDelete.as_view(),
        name="api_key_delete",
    ),
    re_path(
        r"^site/new-validate$",
        site_uid_available_check,
        name="site_uid_available_check",
    ),
]

urlpatterns += htmx_urlpatterns
