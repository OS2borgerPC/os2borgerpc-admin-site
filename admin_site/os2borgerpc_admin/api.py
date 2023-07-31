from ninja import NinjaAPI
from ninja.security import HttpBearer
from django.contrib.admin.views.decorators import user_passes_test

from system.models import APIKey
from system.api import router as system_router

# from changelog.api import router as changelog_router


# Require authentication to access all parts of the API (except docs, which is handled below)
# "key" must then be passed as part of a HTTP header
# The header format is: "Authorizization: Bearer <SOME_API_KEY_HERE>"
# Example curl call:
# curl --header 'Authorization: Bearer <SOME_API_KEY_HERE>' http://os2borgerpc-admin.magenta.dk/api/system/pcs
class GlobalAuth(HttpBearer):
    def authenticate(self, request, key):
        valid_key_check = APIKey.objects.get(key=key)

        if valid_key_check:
            return valid_key_check.key


# Initialize, and require regular API key authentication to all endpoints except the docs endpoint, make docs endpoint
# use regular django user authentication
api = NinjaAPI(
    auth=GlobalAuth(), docs_decorator=user_passes_test(lambda u: u.is_authenticated)
)

api.add_router("/system/", system_router)
# api.add_router("/changelog/", changelog_router)
