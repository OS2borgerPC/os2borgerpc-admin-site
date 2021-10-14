from django.conf.urls import url
from django.views.generic import RedirectView

from .views import SiteList
from .views import AdminIndex, PCsView, GroupsView, UsersView, JobsView
from .views import GroupCreate, GroupUpdate, GroupDelete, JobSearch, UserDelete
from .views import SiteDetailView, UserCreate, UserUpdate, SiteConfiguration
from .views import ScriptList, ScriptUpdate, ScriptCreate, ScriptDelete
from .views import ScriptRun, PCUpdate, JobRestarter
from .views import ConfigurationEntryCreate, ConfigurationEntryUpdate
from .views import ConfigurationEntryDelete, JobInfo, DocView
from .views import PCDelete, JSONSiteSummary
from .views import ImageVersionsView
# SecurityProblem and SecurityEvent related views
from .views import SecurityProblemsView, SecurityProblemCreate
from .views import SecurityProblemUpdate, SecurityProblemDelete
from .views import SecurityEventsView, SecurityEventUpdate
from .views import SecurityEventSearch


urlpatterns = [
    # Security events UI
    url(r'^site/(?P<site_uid>[^/]+)/security_events/(?P<pk>\d+)/$',
        SecurityEventUpdate.as_view(),
        name='security_event_update'),
    url(r'^site/(?P<site_uid>[^/]+)/security_events/search/$',
        SecurityEventSearch.as_view(),
        name='security_event_search'),
    url(r'^site/(?P<slug>[^/]+)/security_events/pc/(?P<pc_uid>[^/]+)/$',
        SecurityEventsView.as_view(),
        name='security_event_pc'),
    url(r'^site/(?P<slug>[^/]+)/security_events/$',
        SecurityEventsView.as_view(),
        name='security_events'),

    # Security problems UI
    url(r'^site/(?P<site_uid>[^/]+)/security_problems/new/$',
        SecurityProblemCreate.as_view(),
        name='security_problem_new'),
    url(r'^site/(?P<site_uid>[^/]+)/security_problems/(?P<uid>[^/]+)/delete/$',
        SecurityProblemDelete.as_view(),
        name='security_problem_delete'),
    url(r'^site/(?P<site_uid>[^/]+)/security_problems/(?P<uid>[^/]+)/$',
        SecurityProblemUpdate.as_view(),
        name='security_problem'),
    url(r'^site/(?P<slug>[^/]+)/security_problems/$',
        SecurityProblemsView.as_view(),
        name='security_problems'),

    # Security scripts
    url(r'^site/(?P<slug>[^/]+)/security_scripts/(?P<script_pk>\d+)/delete/',
        ScriptDelete.as_view(is_security=True),
        name='delete_security_script'),
    url(r'^site/(?P<slug>[^/]+)/security_scripts/(?P<script_pk>\d+)/',
        ScriptUpdate.as_view(is_security=True),
        name='security_script'),
    url(r'^site/(?P<slug>[^/]+)/security_scripts/new/',
        ScriptCreate.as_view(is_security=True),
        name='new_security_script'),
    url(r'^site/(?P<slug>[^/]+)/security_scripts/',
        ScriptList.as_view(is_security=True),
        name='security_scripts'),

    # Sites
    url(r'^$', AdminIndex.as_view(), name='index'),
    url(r'^sites/$', SiteList.as_view(), name='sites'),
    url(r'^site/(?P<slug>[^/]+)/$', SiteDetailView.as_view(),
        name='site'),

    # Configurations
    url(r'^site/(?P<slug>[^/]+)/configuration/$',
        SiteConfiguration.as_view(),
        name='configuration'),
    url(r'^site/(?P<site_uid>[^/]+)/configuration/new/$',
        ConfigurationEntryCreate.as_view(), name='new_configuration'),
    url(r'^site/(?P<site_uid>[^/]+)/configuration/edit/(?P<pk>\d+)/$',
        ConfigurationEntryUpdate.as_view(), name='edit_configuration'),
    url(r'^site/(?P<site_uid>[^/]+)/configuration/delete/(?P<pk>\d+)/$',
        ConfigurationEntryDelete.as_view(), name='delete_configuration'),

    # Computers
    url(r'^site/(?P<slug>[^/]+)/computers/$', PCsView.as_view(),
        name='computers'),
    url(r'^site/(?P<slug>[^/]+)/computers/json/$',
        JSONSiteSummary.as_view(), name='computers_json_site_summary'),
    url(r'^site/(?P<site_uid>[^/]+)/computers/(?P<pc_uid>[^/]+)/$',
        PCUpdate.as_view(), name='computer'),
    url(r'^site/(?P<site_uid>[^/]+)/computers/(?P<pc_uid>[^/]+)/delete/$',
        PCDelete.as_view(), name='computer_delete'),

    # Groups
    url(r'^site/(?P<slug>[^/]+)/groups/$', GroupsView.as_view(),
        name='groups'),
    url(r'^site/(?P<site_uid>[^/]+)/groups/new/$', GroupCreate.as_view(),
        name='new_group'),
    url(r'^site/(?P<site_uid>[^/]+)/groups/(?P<group_uid>[^/]+)/$',
        GroupUpdate.as_view(), name='group'),
    url(r'^site/(?P<site_uid>[^/]+)/groups/(?P<group_uid>[^/]+)/delete/$',
        GroupDelete.as_view(), name='group_delete'),

    # Jobs
    url(r'^site/(?P<site_uid>[^/]+)/jobs/search/',
        JobSearch.as_view(),
        name='jobsearch'),
    url(r'^site/(?P<site_uid>[^/]+)/jobs/(?P<pk>\d+)/restart/',
        JobRestarter.as_view(),
        name='restart_job'
        ),
    url(r'^site/(?P<site_uid>[^/]+)/jobs/(?P<pk>\d+)/info/',
        JobInfo.as_view(),
        name='job_info'
        ),
    url(r'^site/(?P<slug>[^/]+)/jobs/', JobsView.as_view(), name='jobs'),

    # Scripts
    url(r'^site/(?P<slug>[^/]+)/scripts/(?P<script_pk>\d+)/delete/',
        ScriptDelete.as_view(),
        name='delete_script'),
    url(r'^site/(?P<slug>[^/]+)/scripts/(?P<script_pk>\d+)/run/',
        ScriptRun.as_view(),
        name='run_script'),
    url(r'^site/(?P<slug>[^/]+)/scripts/(?P<script_pk>\d+)/',
        ScriptUpdate.as_view(),
        name='script'),
    url(r'^site/(?P<slug>[^/]+)/scripts/new/',
        ScriptCreate.as_view(),
        name='new_script'),
    url(r'^site/(?P<slug>[^/]+)/scripts/',
        ScriptList.as_view(),
        name='scripts'),

    # Users
    url(r'^site/(?P<slug>[^/]+)/users/$',
        UsersView.as_view(),
        name='users'),
    url(r'^site/(?P<site_uid>[^/]+)/new_user/$',
        UserCreate.as_view(),
        name='new_user'),
    url(r'^site/(?P<site_uid>[^/]+)/users/(?P<username>[_\w\@\.\+\-]+)/$',
        UserUpdate.as_view(),
        name='user'),
    url((r'^site/(?P<site_uid>[^/]+)/users/' +
         r'(?P<username>[_\w\@\.\+\-]+)/delete/$'),
        UserDelete.as_view(),
        name='delete_user'),

    # Documentation
    url(r'^documentation/$',
        RedirectView.as_view(
            url='/documentation/om_os2borgerpc_admin/'
        )),
    url(r'^documentation/os2borgerpc_installation_guide/',
        RedirectView.as_view(
          url='https://github.com/OS2borgerPC/image/raw/development/docs/'
          + 'OS2BorgerPC%2020.04%20Installationsguide.pdf'
        )),
    url(r'^documentation/os2displaypc_installation_guide',
        RedirectView.as_view(
            url='https://os2borgerpc-server-image.readthedocs.io/en/latest/dev.html'
        )),
    url(r'^documentation/creating_security_problems/',
        RedirectView.as_view(
          url='https://github.com/OS2borgerPC/admin-site/raw/development/admin_site' \
          + '/static/docs/OS2BorgerPC-sikkerhedsoverv%C3%A5gning.pdf'
        )),
    url(r'^documentation/tech/os2borgerpc-image',
        RedirectView.as_view(
            url='https://os2borgerpc-image.readthedocs.io'
        )),
    url(r'^documentation/tech/os2borgerpc-admin',
        RedirectView.as_view(
            url='https://os2borgerpc-admin.readthedocs.io'
        )),
    url(r'^documentation/tech/os2borgerpc-server-image',
        RedirectView.as_view(
            url='https://os2borgerpc-server-image.readthedocs.io'
        )),
    url(r'^documentation/tech/os2borgerpc-client',
        RedirectView.as_view(
            url='https://os2borgerpc-client.readthedocs.io'
        )),

    url(r'^documentation/(?P<name>[\d\w\/]+)/', DocView.as_view(), name='doc'),
    url(r'^documentation/', DocView.as_view(), name='doc_root'),

    # Image Versions
    url(
        r'^site/(?P<site_uid>[^/]+)/image-versions/$',
        ImageVersionsView.as_view(),
        name='image-versions'
    ),
    url(
        r'^site/(?P<site_uid>[^/]+)/image-versions/(?P<major_version>\d+)$',
        ImageVersionsView.as_view(),
        name='image-version-major'
    ),

]
