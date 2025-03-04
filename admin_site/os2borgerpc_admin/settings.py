# Django settings for OS2borgerPC admin project.

import os
import logging
import django

from google.oauth2 import service_account
from datetime import datetime

logger = logging.getLogger(__name__)

install_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Our customized user profile.
AUTH_PROFILE_MODULE = "account.UserProfile"

DEBUG = os.getenv("DEBUG", 'false').lower() == 'true'

ADMINS = (
    [
        (os.environ.get("ADMIN_USERNAME"), os.environ["ADMIN_EMAIL"]),
    ]
    if os.environ.get("ADMIN_EMAIL")
    else None
)

PC_IMAGE_RELEASES_URL = os.environ.get("PC_IMAGE_RELEASES_URL")
KIOSK_IMAGE_RELEASES_URL = os.environ.get("KIOSK_IMAGE_RELEASES_URL")

MANAGERS = ADMINS

# Template settings
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            os.path.join(install_dir, "templates/"),
            django.__path__[0] + "/forms/templates",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                'os2borgerpc_admin.context_processors.iso_urls',
            ],
            "builtins": [
                "system.templatetags.custom_tags",
            ],
        },
    },
]


SOURCE_DIR = os.path.abspath(os.path.join(install_dir, ".."))

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ['DB_NAME'],
        "USER": os.environ['DB_USER'],
        "PASSWORD": os.environ['DB_PASSWORD'],
        "HOST": os.environ['DB_HOST'],
        "PORT": os.getenv("DB_PORT", ""),
        "OPTIONS": {
            "connect_timeout": 2,  # Minimum in 2
        },
    }
}

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/3.1/ref/settings/#allowed-hosts
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "").split(",")

# Django > 4.0 introduced changes related to CSRF. Note that the protocol has to be specified too.
# https://docs.djangoproject.com/en/4.2/releases/4.0/#csrf
# https://docs.djangoproject.com/en/4.2/ref/settings/#csrf-trusted-origins
if os.getenv("CSRF_TRUSTED_ORIGINS", ""):
    CSRF_TRUSTED_ORIGINS = os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",")
else:
    CSRF_TRUSTED_ORIGINS = []

# Proxy setup
if os.environ.get("USE_X_FORWARDED_HOST"):
    USE_X_FORWARDED_HOST = True
if os.environ.get("SECURE_PROXY_SSL_HEADER"):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")  

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
# Timezone/Language
TIME_ZONE = os.environ["TIME_ZONE"]

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = os.environ["LANGUAGE_CODE"]

LOCALE_PATHS = [os.path.join(install_dir, "locale")]

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = False

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/var/www/example.com/media/"
MEDIA_ROOT = "/media"

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://example.com/media/", "http://media.example.com/"
MEDIA_URL = "/media/"

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/var/www/example.com/static/"
STATIC_ROOT = "/static"

# URL prefix for static files.
# Example: "http://example.com/static/", "http://static.example.com/"
STATIC_URL = "/static/"

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(install_dir, "static"),
    "/frontend",
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
)


# Storage setup
if os.environ.get("GS_BUCKET_NAME"):
    # The Google Cloud Storage bucket name. For `django-storages[google]`
    # https://django-storages.readthedocs.io/en/latest/backends/gcloud.html
    # If it is set, we save all files to Google Cloud.
    DEFAULT_FILE_STORAGE = "storages.backends.gcloud.GoogleCloudStorage"
    GS_BUCKET_NAME = os.environ.get("GS_BUCKET_NAME")
    GS_CREDENTIALS = service_account.Credentials.from_service_account_file(
        os.environ.get("GS_CREDENTIALS_FILE")
    )
    GS_QUERYSTRING_AUTH = False
    GS_FILE_OVERWRITE = False
    GS_CUSTOM_ENDPOINT = os.environ.get("GS_CUSTOM_ENDPOINT", None)

# Make this unique, and don't share it with anybody.
SECRET_KEY = os.environ["SECRET_KEY"]

MIDDLEWARE = (
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_otp.middleware.OTPMiddleware",
    "os2borgerpc_admin.middlewares.user_locale_middleware",
    "django.contrib.messages.middleware.MessageMiddleware",
) + (("os2borgerpc_admin.middlewares.HttpsOnlyMiddleware",) if os.getenv('HTTPS_GUARANTEED') == 'true' else ())

# Email settings

DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL")
EMAIL_HOST = os.environ.get("EMAIL_HOST")
EMAIL_PORT = os.environ.get("EMAIL_PORT")
SERVER_EMAIL = os.environ.get("SERVER_EMAIL")
EMAIL_BACKEND = "os.environ.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST_USER = os.environ.get("EMAIL_USER")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_PASSWORD")

ROOT_URLCONF = "os2borgerpc_admin.urls"

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = "os2borgerc_admin.wsgi.application"

# Don't forget to use absolute paths, not relative paths.
DOCUMENTATION_DIR = os.path.join(install_dir, "templates")


LOCAL_APPS = (
    "system",
    "account",
    "changelog",
)

THIRD_PARTY_APPS = (
    "django_xmlrpc",
    "django_extensions",
    "crispy_forms",
    "crispy_bootstrap5",
    "markdownx",
    "django_otp",
    "django_otp.plugins.otp_static",
    "django_otp.plugins.otp_totp",
    "two_factor",
)

DJANGO_APPS = (
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Uncomment the next line to enable the admin:
    "django.contrib.admin",
    # Uncomment the next line to enable admin documentation:
    "django.contrib.admindocs",
    "django.forms",
)

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

XMLRPC_METHODS = (
    ("system.rpc.register_new_computer", "register_new_computer"),
    ("system.rpc.register_new_computer_v2", "register_new_computer_v2"),
    ("system.rpc.send_status_info", "send_status_info"),
    ("system.rpc.send_status_info_v2", "send_status_info_v2"),
    ("system.rpc.get_instructions", "get_instructions"),
    ("system.rpc.push_config_keys", "push_config_keys"),
    ("system.rpc.push_security_events", "push_security_events"),
    ("system.rpc.citizen_login", "citizen_login"),
    ("system.rpc.citizen_logout", "citizen_logout"),
    ("system.rpc.sms_login", "sms_login"),
    ("system.rpc.sms_login_finalize", "sms_login_finalize"),
    ("system.rpc.sms_logout", "sms_logout"),
    ("system.rpc.general_citizen_login", "general_citizen_login"),
    ("system.rpc.general_citizen_logout", "general_citizen_logout"),
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "console": {
            "format": "{levelname} {asctime} {message}",
            "style": "{",
        }
    },
    "filters": {"require_debug_false": {"()": "django.utils.log.RequireDebugFalse"}},
    "handlers": {
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler",
        },
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "console",
        },
    },
    "root": {
        "handlers": ["console", "mail_admins"],
        "level": os.getenv("LOG_LEVEL", "ERROR"),
    },
}

INITIALIZE_DATABASE = os.getenv("INITIALIZE_DATABASE", 'false').lower() == 'true'

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"

CRISPY_TEMPLATE_PACK = "bootstrap5"

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# Handler for citizen login.
CITIZEN_LOGIN_API_VALIDATOR = os.environ.get(
    "CITIZEN_LOGIN_API_VALIDATOR", "system.utils.cicero_validate"
)

# Cicero specific stuff.
CICERO_URL = os.environ.get("CICERO_URL")

# All Python Markdown's officially supported extensions can be added here without
# any extra setup.
# Third-party extensions can also be imported and used, asuming they (and their
# dependencies) are installed.
MARKDOWNX_MARKDOWN_EXTENSIONS = [
    "markdown.extensions.extra",
]

MARKDOWNX_IMAGE_MAX_SIZE = {"size": (800, 800), "quality": 90}

# This specifies where uploaded media (images) are stored
MARKDOWNX_MEDIA_PATH = datetime.now().strftime("changelog-images/%Y/%m/%d")

FORM_RENDERER = "django.forms.renderers.DjangoDivFormRenderer"

USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
