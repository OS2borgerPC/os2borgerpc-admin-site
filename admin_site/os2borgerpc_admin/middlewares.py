from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponseRedirect
from django.utils import translation


class user_locale_middleware(MiddlewareMixin):
    """
    Parse a request and determine the translation to use based
    on the user's chosen language. If no user is logged in,
    use the browser language instead.
    """

    response_redirect_class = HttpResponseRedirect

    def process_request(self, request):
        if request.user.is_authenticated:
            language = request.user.user_profile.language
        else:
            language = translation.get_language_from_request(request)
        translation.activate(language)
        request.LANGUAGE_CODE = translation.get_language()
