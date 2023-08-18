from django_xmlrpc.views import handle_xmlrpc

from django.urls import include, re_path
from django.conf.urls.static import static
from django.conf import settings


# Uncomment the next two lines to enable the admin:
from django.contrib import admin
from django.contrib.auth import views as auth_views
from two_factor import views as otp_views

from markdownx import urls as markdownx
from two_factor.urls import urlpatterns as tf_urls

admin.autodiscover()

urlpatterns = [
    re_path("accounts/login/", otp_views.LoginView.as_view()),
    re_path(r"^xmlrpc/$", handle_xmlrpc, name="xmlrpc"),
    re_path(r"^admin-xml/$", handle_xmlrpc),
    re_path(
        "accounts/logout/", auth_views.LogoutView.as_view(template_name="logout.html")
    ),
    # Include each of our apps' URLs
    re_path(r"^", include("system.urls")),
    # Include changelog URLs
    re_path(r"^changelog/", include("changelog.urls")),
    # Include external apps' URLs
    re_path("markdownx/", include(markdownx)),
    re_path("", include(tf_urls)),
    # Uncomment the admin/doc line below to enable admin documentation:
    re_path("admin/doc/", include("django.contrib.admindocs.urls")),
    # Uncomment the next line to enable the admin:
    re_path(r"^admin/", admin.site.urls),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
