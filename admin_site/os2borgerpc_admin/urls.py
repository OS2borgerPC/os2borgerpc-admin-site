from django_xmlrpc.views import handle_xmlrpc

from django.conf.urls import include, url
from django.conf.urls.static import static
from django.conf import settings


# Uncomment the next two lines to enable the admin:
from django.contrib import admin
from django.contrib.auth import views as auth_views
admin.autodiscover()

urlpatterns = [
    # Examples:
    url(
        'accounts/login/',
        auth_views.LoginView.as_view(template_name='login.html')
    ),
    url(r'^xmlrpc/$', handle_xmlrpc, name='xmlrpc'),
    url(
        'accounts/logout/',
        auth_views.LogoutView.as_view(template_name='logout.html')
    ),
    url(r'^', include('system.urls')),
    url(r'^admin-xml/$', handle_xmlrpc),
    # Uncomment the admin/doc line below to enable admin documentation:
    url('admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', admin.site.urls),
]

# Static files are served by WhiteNoise in both development and production.

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
